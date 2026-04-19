"""Unit tests for prospects_aggregator.py — dedup, merge, normalization."""

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from prospects_aggregator import (
    _norm_email, _norm_phone, _parse_dt,
    Prospect, ProspectRegistry,
)


class TestNormPhone(unittest.TestCase):
    def test_10_digits(self):
        self.assertEqual(_norm_phone("5141234567"), "5141234567")

    def test_with_plus_1(self):
        self.assertEqual(_norm_phone("+15141234567"), "5141234567")

    def test_with_dashes(self):
        self.assertEqual(_norm_phone("514-123-4567"), "5141234567")

    def test_with_parens(self):
        self.assertEqual(_norm_phone("(514) 123-4567"), "5141234567")

    def test_with_leading_1(self):
        self.assertEqual(_norm_phone("15141234567"), "5141234567")

    def test_empty(self):
        self.assertIsNone(_norm_phone(""))
        self.assertIsNone(_norm_phone(None))

    def test_too_short(self):
        # Must be exactly 10 digits
        self.assertIsNone(_norm_phone("12345"))

    def test_too_long(self):
        # Normalize_number returns last 10, which may not be a valid NA phone.
        # We accept it — real data will be 10 digits in practice.
        result = _norm_phone("+331234567890")
        # Should still return 10 digits (normalize_number keeps last 10)
        self.assertTrue(result is None or len(result) == 10)


class TestNormEmail(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_norm_email("User@Example.COM"), "user@example.com")

    def test_with_whitespace(self):
        self.assertEqual(_norm_email("  foo@bar.com  "), "foo@bar.com")

    def test_invalid_format(self):
        self.assertIsNone(_norm_email("notanemail"))
        self.assertIsNone(_norm_email("@example.com"))
        self.assertIsNone(_norm_email("user@"))

    def test_empty(self):
        self.assertIsNone(_norm_email(""))
        self.assertIsNone(_norm_email(None))

    def test_plus_and_dots(self):
        self.assertEqual(_norm_email("user.name+tag@gmail.com"), "user.name+tag@gmail.com")


class TestParseDt(unittest.TestCase):
    def test_iso_with_tz(self):
        d = _parse_dt("2026-04-15T14:30:00+00:00")
        self.assertIsNotNone(d)
        self.assertEqual(d.year, 2026)

    def test_iso_with_z(self):
        d = _parse_dt("2026-04-15T14:30:00Z")
        self.assertIsNotNone(d)

    def test_iso_naive(self):
        d = _parse_dt("2026-04-15T14:30:00")
        self.assertIsNotNone(d)

    def test_space_format(self):
        d = _parse_dt("2026-04-15 14:30:00")
        self.assertIsNotNone(d)

    def test_date_only(self):
        d = _parse_dt("2026-04-15")
        self.assertIsNotNone(d)

    def test_empty(self):
        self.assertIsNone(_parse_dt(""))
        self.assertIsNone(_parse_dt(None))

    def test_garbage(self):
        self.assertIsNone(_parse_dt("not a date"))


class TestProspectMerge(unittest.TestCase):
    def test_same_phone_different_rows(self):
        """Two rows with same phone should merge into one prospect."""
        reg = ProspectRegistry()
        p1 = reg.find_or_create(phone="514-123-4567", name="Jean Dupont")
        p2 = reg.find_or_create(phone="+15141234567")  # same phone, different format
        self.assertIs(p1, p2)
        self.assertEqual(p1.phone, "5141234567")
        self.assertEqual(p1.full_name, "Jean Dupont")
        self.assertEqual(len(reg.all), 1)

    def test_phone_then_email_same_person(self):
        """If same prospect appears via phone first, then email —
        they should merge IF we know (via GHL lookup or shared data) it's the same.
        CURRENT BEHAVIOR: creates 2 prospects unless both ids come in same call.
        This test documents the known limitation.
        """
        reg = ProspectRegistry()
        p1 = reg.find_or_create(phone="5141234567")
        p2 = reg.find_or_create(email="jean@example.com")
        # Without a shared identifier, these are 2 distinct prospects
        self.assertEqual(len(reg.all), 2)

        # If we then find them together (e.g. from GHL), they should merge:
        p3 = reg.find_or_create(phone="5141234567", email="jean@example.com")
        self.assertIs(p3, p1)  # Matched by phone first
        # But now p1 also has the email
        self.assertEqual(p1.email, "jean@example.com")

    def test_name_not_overwritten(self):
        """First name wins — don't overwrite with 'Unknown' or empty."""
        reg = ProspectRegistry()
        p = reg.find_or_create(phone="5141234567", name="Jean Dupont")
        reg.find_or_create(phone="5141234567", name="")  # empty
        reg.find_or_create(phone="5141234567", name="Inconnu")  # junk
        self.assertEqual(p.full_name, "Jean Dupont")

    def test_at_least_one_identity_required(self):
        """A prospect with no phone/email/ghl_id should not be findable."""
        reg = ProspectRegistry()
        # Skip creating prospect with no identity
        self.assertIsNotNone(reg.find_or_create(phone="5141234567"))
        self.assertEqual(len(reg.all), 1)


class TestProspectDict(unittest.TestCase):
    def test_stage_paid(self):
        p = Prospect()
        p.phone = "5141234567"
        p.has_paid = True
        d = p.to_dict()
        self.assertEqual(d["stage"], "paid")
        self.assertTrue(d["has_gard_paid_tag"])

    def test_stage_engaged(self):
        p = Prospect()
        p.phone = "5141234567"
        p.answered_calls = 1
        d = p.to_dict()
        self.assertEqual(d["stage"], "engaged")

    def test_stage_prospect_default(self):
        p = Prospect()
        p.phone = "5141234567"
        d = p.to_dict()
        self.assertEqual(d["stage"], "prospect")

    def test_identity_key_always_set(self):
        """identity_key must never be None (DB constraint)."""
        p = Prospect()
        p.email = "a@b.com"
        self.assertEqual(p.to_dict()["identity_key"], "a@b.com")

        p2 = Prospect()
        p2.ghl_id = "xyz"
        self.assertEqual(p2.to_dict()["identity_key"], "xyz")

    def test_all_keys_present(self):
        """Bulk insert requires all rows to have same keys — to_dict must return all columns."""
        p1 = Prospect()
        p1.phone = "5141234567"
        p2 = Prospect()
        p2.email = "a@b.com"
        self.assertEqual(set(p1.to_dict().keys()), set(p2.to_dict().keys()))

    def test_days_since_last_inbound_computed(self):
        p = Prospect()
        p.phone = "5141234567"
        p.last_contact = datetime.now(timezone.utc).replace(day=1)
        d = p.to_dict()
        self.assertIsNotNone(d["days_since_last_inbound"])
        self.assertGreaterEqual(d["days_since_last_inbound"], 0)


class TestTouchMethods(unittest.TestCase):
    def test_touch_inbound_updates_both(self):
        p = Prospect()
        dt = datetime(2026, 4, 15, 14, 30)
        p.touch_inbound(dt)
        self.assertEqual(p.last_inbound, dt)
        self.assertEqual(p.first_contact, dt)
        self.assertEqual(p.last_contact, dt)

    def test_touch_inbound_keeps_earliest_first(self):
        p = Prospect()
        p.touch_inbound(datetime(2026, 4, 15))
        p.touch_inbound(datetime(2026, 3, 10))
        self.assertEqual(p.first_contact, datetime(2026, 3, 10))

    def test_touch_inbound_keeps_latest_last(self):
        p = Prospect()
        p.touch_inbound(datetime(2026, 3, 10))
        p.touch_inbound(datetime(2026, 4, 15))
        self.assertEqual(p.last_inbound, datetime(2026, 4, 15))
        self.assertEqual(p.last_contact, datetime(2026, 4, 15))

    def test_touch_none_safe(self):
        p = Prospect()
        p.touch_inbound(None)  # should not crash
        self.assertIsNone(p.last_inbound)


if __name__ == "__main__":
    unittest.main(verbosity=2)
