"""Unit tests for ghl_helpers.py — tag matching, phone normalization, note format.

Does NOT hit live GHL API — tests pure functions only.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent))

from ghl_helpers import ghl_has_tag


class TestGhlHasTag(unittest.TestCase):
    def test_exact_match(self):
        contact = {"tags": ["gard paid", "inscription"]}
        self.assertTrue(ghl_has_tag(contact, "gard paid"))

    def test_case_insensitive(self):
        contact = {"tags": ["Gard Paid"]}
        self.assertTrue(ghl_has_tag(contact, "gard paid"))
        self.assertTrue(ghl_has_tag(contact, "GARD PAID"))

    def test_whitespace_stripped(self):
        contact = {"tags": ["  gard paid  "]}
        self.assertTrue(ghl_has_tag(contact, "gard paid"))

    def test_no_match(self):
        contact = {"tags": ["xguard paid", "inscription"]}
        self.assertFalse(ghl_has_tag(contact, "gard paid"))

    def test_empty_tags(self):
        self.assertFalse(ghl_has_tag({"tags": []}, "gard paid"))
        self.assertFalse(ghl_has_tag({}, "gard paid"))

    def test_none_contact(self):
        self.assertFalse(ghl_has_tag(None, "gard paid"))

    def test_none_tag(self):
        self.assertFalse(ghl_has_tag({"tags": ["gard paid"]}, None))
        self.assertFalse(ghl_has_tag({"tags": ["gard paid"]}, ""))

    def test_none_in_tags_list(self):
        """Gracefully handle None or empty strings in the tags list."""
        contact = {"tags": [None, "", "gard paid"]}
        self.assertTrue(ghl_has_tag(contact, "gard paid"))

    def test_partial_match_not_counted(self):
        """'paid' should not match 'gard paid'."""
        contact = {"tags": ["gard paid"]}
        self.assertFalse(ghl_has_tag(contact, "paid"))


class TestGhlLogActionFormat(unittest.TestCase):
    """Test the note body format is consistent and parseable."""

    @patch("ghl_helpers._request")
    def test_note_format(self, mock_request):
        mock_request.return_value.status_code = 201
        from ghl_helpers import ghl_log_action
        ghl_log_action("contact_123", action="SMS envoye", details="Bonjour test")

        # Inspect what was POSTed
        args, kwargs = mock_request.call_args
        self.assertEqual(args[0], "POST")
        self.assertEqual(args[1], "/contacts/contact_123/notes")

        body = kwargs["json"]["body"]
        self.assertIn("[IA-automation", body)
        self.assertIn("SMS envoye", body)
        self.assertIn("Bonjour test", body)

    @patch("ghl_helpers._request")
    def test_note_no_contact_id_returns_false(self, mock_request):
        from ghl_helpers import ghl_log_action
        result = ghl_log_action("", action="SMS envoye")
        self.assertFalse(result)
        mock_request.assert_not_called()


class TestGhlAddNote(unittest.TestCase):
    @patch("ghl_helpers._request")
    def test_success_201(self, mock_request):
        mock_request.return_value.status_code = 201
        from ghl_helpers import ghl_add_note
        self.assertTrue(ghl_add_note("cid", "body"))

    @patch("ghl_helpers._request")
    def test_failure_404(self, mock_request):
        mock_request.return_value.status_code = 404
        mock_request.return_value.text = "Not Found"
        from ghl_helpers import ghl_add_note
        self.assertFalse(ghl_add_note("cid", "body"))

    def test_empty_body(self):
        from ghl_helpers import ghl_add_note
        self.assertFalse(ghl_add_note("cid", ""))
        self.assertFalse(ghl_add_note("cid", None))


class TestGhlAddTag(unittest.TestCase):
    @patch("ghl_helpers._request")
    def test_success(self, mock_request):
        mock_request.return_value.status_code = 201
        from ghl_helpers import ghl_add_tag
        self.assertTrue(ghl_add_tag("cid", "gard paid"))

    @patch("ghl_helpers._request")
    def test_failure(self, mock_request):
        mock_request.return_value.status_code = 400
        mock_request.return_value.text = "bad request"
        from ghl_helpers import ghl_add_tag
        self.assertFalse(ghl_add_tag("cid", "gard paid"))

    def test_empty_args(self):
        from ghl_helpers import ghl_add_tag
        self.assertFalse(ghl_add_tag("", "tag"))
        self.assertFalse(ghl_add_tag("cid", ""))


class TestGhlRemoveTag(unittest.TestCase):
    @patch("ghl_helpers._request")
    def test_success_204(self, mock_request):
        mock_request.return_value.status_code = 204
        from ghl_helpers import ghl_remove_tag
        self.assertTrue(ghl_remove_tag("cid", "xguard paid"))

    @patch("ghl_helpers._request")
    def test_failure(self, mock_request):
        mock_request.return_value.status_code = 500
        mock_request.return_value.text = "server error"
        from ghl_helpers import ghl_remove_tag
        self.assertFalse(ghl_remove_tag("cid", "tag"))


class TestGhlCreateContact(unittest.TestCase):
    @patch("ghl_helpers._request")
    def test_success(self, mock_request):
        mock_request.return_value.status_code = 201
        mock_request.return_value.json.return_value = {
            "contact": {"id": "new_id", "email": "a@b.com"}
        }
        from ghl_helpers import ghl_create_contact
        result = ghl_create_contact("a@b.com", first_name="Alice")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "new_id")

    @patch("ghl_helpers._request")
    def test_duplicate_fallback(self, mock_request):
        """When GHL says 'Duplicated contacts', should fall back to search."""
        def side_effect(method, path, **kwargs):
            from unittest.mock import MagicMock
            r = MagicMock()
            if method == "POST" and "/contacts/" == path:
                r.status_code = 400
                r.text = "Duplicated contacts found"
            elif method == "GET" and "/contacts/" == path:
                r.status_code = 200
                r.json.return_value = {
                    "contacts": [{"id": "existing", "email": "a@b.com"}]
                }
            return r
        mock_request.side_effect = side_effect
        from ghl_helpers import ghl_create_contact
        result = ghl_create_contact("a@b.com")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "existing")

    def test_empty_email(self):
        from ghl_helpers import ghl_create_contact
        self.assertIsNone(ghl_create_contact(""))
        self.assertIsNone(ghl_create_contact(None))


class TestPhoneSearch(unittest.TestCase):
    """Test phone normalization for GHL search (different from prospects normalization)."""

    @patch("ghl_helpers._request")
    def test_10_digits_formatted(self, mock_request):
        mock_request.return_value.status_code = 404
        from ghl_helpers import ghl_find_contact_by_phone
        ghl_find_contact_by_phone("5141234567")
        # Verify the number was formatted with +1
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"]["number"], "+15141234567")

    @patch("ghl_helpers._request")
    def test_already_has_plus(self, mock_request):
        mock_request.return_value.status_code = 404
        from ghl_helpers import ghl_find_contact_by_phone
        ghl_find_contact_by_phone("+15141234567")
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"]["number"], "+15141234567")

    @patch("ghl_helpers._request")
    def test_with_dashes(self, mock_request):
        mock_request.return_value.status_code = 404
        from ghl_helpers import ghl_find_contact_by_phone
        ghl_find_contact_by_phone("514-123-4567")
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["params"]["number"], "+15141234567")

    def test_empty(self):
        from ghl_helpers import ghl_find_contact_by_phone
        self.assertIsNone(ghl_find_contact_by_phone(""))
        self.assertIsNone(ghl_find_contact_by_phone(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
