"""Unit tests for prospects_helpers.py — summary formatting edge cases.
Does NOT hit live Supabase — mocks sb_get.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from prospects_helpers import _build_summary_parts


class TestSummaryParts(unittest.TestCase):
    def test_minimal_prospect(self):
        p = {"full_name": "Jean Dupont"}
        parts = _build_summary_parts(p, [])
        self.assertIn("Jean Dupont", "\n".join(parts))
        self.assertIn("PAS ENCORE PAYE", "\n".join(parts))

    def test_paid_prospect(self):
        p = {"full_name": "Marie", "has_gard_paid_tag": True, "paid_date": "2026-04-15"}
        parts = _build_summary_parts(p, [])
        joined = "\n".join(parts)
        self.assertIn("DEJA PAYE", joined)
        self.assertIn("2026-04-15", joined)

    def test_no_name(self):
        """Prospect with no name should not crash."""
        p = {}
        parts = _build_summary_parts(p, [])
        self.assertIn("nom inconnu", "\n".join(parts))

    def test_programs(self):
        p = {"programs_mentioned": ["drone", "gardiennage"], "program_interested": "drone"}
        parts = _build_summary_parts(p, [])
        joined = "\n".join(parts)
        self.assertIn("drone", joined)

    def test_activity_counts(self):
        p = {
            "total_calls": 5,
            "answered_calls": 2,
            "missed_calls": 3,
            "total_sms_received": 4,
            "total_sms_sent": 2,
            "total_emails_received": 1,
        }
        parts = _build_summary_parts(p, [])
        joined = "\n".join(parts)
        self.assertIn("5 appels", joined)
        self.assertIn("2 repondus", joined)
        self.assertIn("3 manques", joined)

    def test_our_outreach_shown(self):
        p = {
            "times_we_contacted": 2,
            "last_our_sms_at": "2026-04-15T14:00:00+00:00",
        }
        parts = _build_summary_parts(p, [])
        joined = "\n".join(parts)
        self.assertIn("2 SMS", joined)

    def test_timeline_events_included(self):
        p = {"full_name": "Jean"}
        timeline = [
            {
                "event_type": "sms_inbound",
                "event_date": "2026-04-15T10:00:00",
                "content_excerpt": "Combien coute la formation?",
            },
            {
                "event_type": "call_inbound",
                "event_date": "2026-04-14T14:00:00",
                "content_excerpt": "Appel manque",
            },
        ]
        parts = _build_summary_parts(p, timeline)
        joined = "\n".join(parts)
        self.assertIn("Combien coute", joined)
        self.assertIn("Appel manque", joined)

    def test_empty_timeline_ok(self):
        """No timeline events should not crash."""
        p = {"full_name": "Jean"}
        parts = _build_summary_parts(p, [])
        self.assertIsInstance(parts, list)
        self.assertGreater(len(parts), 0)


class TestGetProspect(unittest.TestCase):
    @patch("prospects_helpers.sb_get")
    def test_find_by_phone(self, mock_get):
        mock_get.return_value = [{"id": 1, "phone_normalized": "5141234567"}]
        from prospects_helpers import get_prospect
        p = get_prospect(phone="514-123-4567")
        self.assertIsNotNone(p)
        self.assertEqual(p["id"], 1)

    @patch("prospects_helpers.sb_get")
    def test_find_by_email(self, mock_get):
        mock_get.return_value = [{"id": 2, "email_normalized": "a@b.com"}]
        from prospects_helpers import get_prospect
        p = get_prospect(email="A@B.COM")
        self.assertIsNotNone(p)
        self.assertEqual(p["id"], 2)

    @patch("prospects_helpers.sb_get")
    def test_not_found_returns_none(self, mock_get):
        mock_get.return_value = []
        from prospects_helpers import get_prospect
        self.assertIsNone(get_prospect(phone="5149999999"))

    def test_no_identifiers_returns_none(self):
        from prospects_helpers import get_prospect
        self.assertIsNone(get_prospect())
        self.assertIsNone(get_prospect(phone="", email="", ghl_id=""))

    def test_invalid_phone_returns_none(self):
        from prospects_helpers import get_prospect
        self.assertIsNone(get_prospect(phone="123"))  # too short


if __name__ == "__main__":
    unittest.main(verbosity=2)
