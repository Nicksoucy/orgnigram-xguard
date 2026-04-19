"""Unit tests for google_sheets_reader.py — column detection + paid detection."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from google_sheets_reader import (
    _find_column, _is_paid, _valid_email, _safe_str,
    EMAIL_HEADERS, PAID_HEADERS, PHONE_HEADERS, NAME_HEADERS,
)


class TestFindColumn(unittest.TestCase):
    def test_email_english(self):
        headers = ["Name", "Email", "Phone"]
        self.assertEqual(_find_column(headers, EMAIL_HEADERS), 1)

    def test_email_french(self):
        headers = ["Nom", "Courriel", "Telephone"]
        self.assertEqual(_find_column(headers, EMAIL_HEADERS), 1)

    def test_email_case_insensitive(self):
        headers = ["NAME", "EMAIL ADDRESS", "PHONE"]
        self.assertEqual(_find_column(headers, EMAIL_HEADERS), 1)

    def test_paid_column(self):
        headers = ["Email", "Name", "Phone", "Amount", "Paid"]
        self.assertEqual(_find_column(headers, PAID_HEADERS), 4)

    def test_no_match(self):
        headers = ["col1", "col2", "col3"]
        self.assertIsNone(_find_column(headers, EMAIL_HEADERS))

    def test_empty_headers(self):
        self.assertIsNone(_find_column([], EMAIL_HEADERS))
        self.assertIsNone(_find_column(None, EMAIL_HEADERS))

    def test_returns_first_match(self):
        """If multiple columns match, return the first one."""
        headers = ["email1", "email2", "another email"]
        self.assertEqual(_find_column(headers, EMAIL_HEADERS), 0)

    def test_empty_header_values(self):
        """Skip None/empty headers gracefully."""
        headers = [None, "", "email"]
        self.assertEqual(_find_column(headers, EMAIL_HEADERS), 2)


class TestIsPaid(unittest.TestCase):
    def test_truthy_words_french(self):
        for v in ["oui", "OUI", "paye", "Payé", "x", "X"]:
            self.assertTrue(_is_paid(v), f"Failed for: {v}")

    def test_truthy_words_english(self):
        for v in ["yes", "YES", "paid", "complete", "done", "ok"]:
            self.assertTrue(_is_paid(v), f"Failed for: {v}")

    def test_checkmark_symbols(self):
        self.assertTrue(_is_paid("✓"))
        self.assertTrue(_is_paid("✔"))

    def test_dollar_amount(self):
        self.assertTrue(_is_paid("$399"))
        self.assertTrue(_is_paid("$388.05"))
        self.assertTrue(_is_paid("$ 449.00"))

    def test_date_format(self):
        self.assertTrue(_is_paid("2026-04-15"))
        self.assertTrue(_is_paid("04/15/2026"))
        self.assertTrue(_is_paid("15/4/26"))

    def test_decimal_amount_no_dollar(self):
        self.assertTrue(_is_paid("100.00"))
        self.assertTrue(_is_paid("449,50"))

    def test_empty_not_paid(self):
        self.assertFalse(_is_paid(""))
        self.assertFalse(_is_paid(None))
        self.assertFalse(_is_paid("   "))

    def test_falsy(self):
        self.assertFalse(_is_paid("no"))
        self.assertFalse(_is_paid("n/a"))


class TestValidEmail(unittest.TestCase):
    def test_valid(self):
        self.assertTrue(_valid_email("user@example.com"))
        self.assertTrue(_valid_email("user.name+tag@sub.example.com"))

    def test_invalid(self):
        self.assertFalse(_valid_email("notanemail"))
        self.assertFalse(_valid_email("@example.com"))
        self.assertFalse(_valid_email("user@"))
        self.assertFalse(_valid_email("user@example"))
        self.assertFalse(_valid_email(""))
        self.assertFalse(_valid_email(None))


class TestSafeStr(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_safe_str("hello"), "hello")
        self.assertEqual(_safe_str("  padded  "), "padded")

    def test_none(self):
        self.assertEqual(_safe_str(None), "")

    def test_numeric(self):
        self.assertEqual(_safe_str(42), "42")
        self.assertEqual(_safe_str(3.14), "3.14")


if __name__ == "__main__":
    unittest.main(verbosity=2)
