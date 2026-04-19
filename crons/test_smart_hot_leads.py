"""Unit tests for smart_hot_leads.py — prompt building, throttle edge cases."""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent))


class TestBuildContextPrompt(unittest.TestCase):
    def setUp(self):
        # Import fresh to reset state
        from smart_hot_leads import build_context_prompt
        self.build = build_context_prompt

    @patch("smart_hot_leads.get_prospect_full_context")
    def test_minimal_lead_no_prospect_history(self, mock_ctx):
        """When prospect not in intelligence base, should still work."""
        mock_ctx.return_value = None
        lead = {
            "number": "5141234567",
            "name": "Jean Dupont",
            "missed_count": 1,
            "call_times": ["14:30"],
            "sms_count": 0,
            "sms_messages": [],
            "email_subject": "",
            "email_from": "",
            "channels": ["appel"],
            "priority": "MEDIUM",
        }
        prompt = self.build(lead)
        # New prompt uses first_name for greeting, not full name
        self.assertIn("Jean", prompt)
        self.assertIn("1 fois AUJOURD'HUI", prompt)
        self.assertIn("(438) 802-0475", prompt)
        # Verify service-not-sales tone
        self.assertIn("SUIVI SERVICE", prompt)
        self.assertIn("PAS un message de ventes", prompt)

    @patch("smart_hot_leads.get_prospect_full_context")
    def test_lead_with_full_history(self, mock_ctx):
        """Should include prior calls, SMS, our outreach in prompt."""
        mock_ctx.return_value = {
            "prospect": {
                "id": 123,
                "total_calls": 3,
                "answered_calls": 1,
                "missed_calls": 2,
                "total_sms_received": 2,
                "total_emails_received": 1,
                "program_interested": "drone",
                "programs_mentioned": ["drone", "gardiennage"],
                "times_we_contacted": 1,
                "last_our_sms_at": "2026-04-10T14:00:00",
                "last_our_sms_body": "Previous SMS body",
            },
            "timeline": [
                {
                    "event_type": "sms_inbound",
                    "event_date": "2026-04-15T10:00:00",
                    "content_excerpt": "Combien coute la formation?",
                },
            ],
            "summary_parts": [],
        }
        lead = {
            "number": "5141234567",
            "name": "Jean",
            "missed_count": 1,
            "call_times": ["14:30"],
            "sms_count": 1,
            "sms_messages": ["Disponibilites en mai?"],
            "email_subject": "",
            "email_from": "",
            "channels": ["appel", "SMS"],
            "priority": "URGENT",
        }
        prompt = self.build(lead)
        # Should contain history context
        self.assertIn("drone", prompt.lower())
        self.assertIn("on lui a DEJA envoye", prompt)
        self.assertIn("NE PAS repeter", prompt)

    @patch("smart_hot_leads.get_prospect_full_context")
    def test_no_name_uses_generic_greeting(self, mock_ctx):
        mock_ctx.return_value = None
        lead = {
            "number": "5141234567",
            "name": "",
            "missed_count": 1,
            "call_times": ["14:30"],
            "sms_count": 0,
            "sms_messages": [],
            "email_subject": "",
            "email_from": "",
            "channels": ["appel"],
            "priority": "MEDIUM",
        }
        prompt = self.build(lead)
        # Should still build the prompt; no crash
        self.assertIn("(438) 802-0475", prompt)


class TestThrottleCheck(unittest.TestCase):
    """Test throttle logic — tz-aware vs naive datetimes."""

    @patch("smart_hot_leads.sb_get")
    @patch("prospects_helpers.get_prospect")
    def test_no_prior_sms(self, mock_get, mock_sb):
        mock_get.return_value = None
        mock_sb.return_value = []
        from smart_hot_leads import recently_sms_sent
        self.assertFalse(recently_sms_sent("5141234567"))

    @patch("prospects_helpers.get_prospect")
    def test_tz_aware_recent(self, mock_get):
        """When last_our_sms_at is tz-aware ISO and recent, should return True."""
        recent = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        mock_get.return_value = {"last_our_sms_at": recent}
        from smart_hot_leads import recently_sms_sent
        self.assertTrue(recently_sms_sent("5141234567"))

    @patch("smart_hot_leads.sb_get")
    @patch("prospects_helpers.get_prospect")
    def test_tz_aware_old(self, mock_get, mock_sb):
        """When last SMS is > THROTTLE_DAYS ago, should return False."""
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        mock_get.return_value = {"last_our_sms_at": old}
        mock_sb.return_value = []  # Fallback finds nothing
        from smart_hot_leads import recently_sms_sent
        self.assertFalse(recently_sms_sent("5141234567"))

    @patch("prospects_helpers.get_prospect")
    def test_tz_aware_with_z_suffix(self, mock_get):
        """Z suffix should parse correctly (common ISO format)."""
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
        mock_get.return_value = {"last_our_sms_at": recent}
        from smart_hot_leads import recently_sms_sent
        self.assertTrue(recently_sms_sent("5141234567"))


class TestSendSmsIntegration(unittest.TestCase):
    """Test send_sms payload formatting."""

    @patch("smart_hot_leads.requests.post")
    def test_payload_has_plus_1(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = "ok"
        mock_post.return_value = mock_response
        from smart_hot_leads import send_sms
        send_sms("5141234567", "Bonjour Jean, test.")
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertEqual(payload["to"], "15141234567")
        self.assertEqual(payload["from"], "14388020475")

    @patch("smart_hot_leads.requests.post")
    def test_already_has_1_prefix(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = "ok"
        mock_post.return_value = mock_response
        from smart_hot_leads import send_sms
        send_sms("15141234567", "Bonjour Jean, test.")
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["to"], "15141234567")


if __name__ == "__main__":
    unittest.main(verbosity=2)
