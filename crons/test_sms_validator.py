"""Unit tests for sms_validator.py — edge cases for SMS safety."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sms_validator import validate_sms


# A baseline valid SMS we'll vary in the tests
GOOD_SMS = (
    "Bonjour Jean, merci pour votre appel! On est disponible pour repondre "
    "a vos questions. Appelez-nous au (438) 802-0475 — Academie XGuard"
)


class TestValid(unittest.TestCase):
    def test_baseline(self):
        ok, reason = validate_sms(GOOD_SMS)
        self.assertTrue(ok, f"Expected valid, got: {reason}")

    def test_phone_with_dashes(self):
        sms = ("Bonjour Marie, merci pour votre interet! Appelez-nous au 438-802-0475 "
               "pour plus d'info. Academie XGuard est la pour vous.")
        ok, reason = validate_sms(sms)
        self.assertTrue(ok, f"Expected valid, got: {reason}")

    def test_phone_no_formatting(self):
        sms = ("Bonjour Pierre, appelez-nous au 4388020475 pour discuter "
               "de votre formation. On est la pour vous aider!")
        ok, reason = validate_sms(sms)
        self.assertTrue(ok, f"Expected valid, got: {reason}")

    def test_french_apostrophes(self):
        """French uses apostrophes (l', d', n') — should not count as unclosed quotes."""
        sms = ("Bonjour, voici l'info de l'Academie XGuard. N'hesitez pas "
               "a nous appeler au (438) 802-0475 pour votre formation!")
        ok, reason = validate_sms(sms)
        self.assertTrue(ok, f"Expected valid, got: {reason}")


class TestLength(unittest.TestCase):
    def test_empty(self):
        ok, r = validate_sms("")
        self.assertFalse(ok)
        self.assertEqual(r, "empty SMS")

    def test_none(self):
        ok, r = validate_sms(None)
        self.assertFalse(ok)

    def test_too_short(self):
        ok, r = validate_sms("Bonjour, (438) 802-0475")  # < 30 chars
        self.assertFalse(ok)
        self.assertIn("too short", r)

    def test_too_long(self):
        long_sms = "Bonjour Jean, " + ("blabla " * 60) + "(438) 802-0475"
        ok, r = validate_sms(long_sms)
        self.assertFalse(ok)
        self.assertIn("too long", r)


class TestStartsWithBonjour(unittest.TestCase):
    def test_hello_rejected(self):
        sms = ("Hello Jean, thanks for your call. Please call us at (438) 802-0475 "
               "for more info about the training program.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertEqual(r, "doesn't start with Bonjour")

    def test_salut_rejected(self):
        sms = ("Salut Jean, merci de votre appel. Appelez-nous au (438) 802-0475 "
               "pour plus d'information sur la formation.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)


class TestPhoneRequired(unittest.TestCase):
    def test_no_phone(self):
        sms = ("Bonjour Jean, merci pour votre appel aujourd'hui. Nous sommes "
               "disponibles pour repondre a toutes vos questions sur la formation.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertIn("missing XGuard phone", r)

    def test_wrong_phone(self):
        sms = ("Bonjour Jean, appelez-nous au (514) 555-1234 pour discuter "
               "de votre formation. Academie XGuard est la pour vous.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)


class TestToxicLanguage(unittest.TestCase):
    def test_french_swear(self):
        sms = ("Bonjour Jean, crisse on a essaye de vous joindre. "
               "Appelez-nous au (438) 802-0475 pour la formation.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertIn("toxic word", r)

    def test_english_swear(self):
        sms = ("Bonjour Jean, what the fuck is going on. "
               "Call us at (438) 802-0475 pour la formation XGuard.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)

    def test_word_boundary_avoids_false_positive(self):
        """'con' in 'constamment' should NOT trigger."""
        sms = ("Bonjour Jean, on essaie constamment de vous joindre. "
               "Appelez-nous au (438) 802-0475 pour discuter de la formation.")
        ok, r = validate_sms(sms)
        self.assertTrue(ok, f"Expected valid, got: {r}")


class TestPromises(unittest.TestCase):
    def test_garantie(self):
        sms = ("Bonjour Jean, votre formation est garantie reussie. "
               "Appelez-nous au (438) 802-0475 pour reserver votre place.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertIn("garant", r)  # matches 'garanti' or 'garantie'

    def test_gratuit(self):
        sms = ("Bonjour Jean, consultation gratuite disponible! "
               "Appelez-nous au (438) 802-0475 pour plus d'information.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertIn("gratuit", r)

    def test_rabais(self):
        sms = ("Bonjour Jean, un rabais exclusif vous attend. "
               "Appelez-nous au (438) 802-0475 pour en profiter.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)


class TestMarkdownArtifacts(unittest.TestCase):
    def test_bold(self):
        sms = ("Bonjour Jean, **merci** pour votre appel. "
               "Appelez-nous au (438) 802-0475 pour la formation.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertIn("markdown", r)

    def test_bullet(self):
        sms = ("Bonjour Jean:\n- formation drone\n- formation gardiennage\n"
               "Appelez-nous au (438) 802-0475 pour choisir.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)


class TestPlaceholders(unittest.TestCase):
    def test_unfilled_prenom(self):
        sms = ("Bonjour [prenom], merci pour votre interet! Appelez-nous "
               "au (438) 802-0475 pour discuter de votre formation XGuard.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertIn("placeholder", r)


class TestLeakedInfo(unittest.TestCase):
    def test_email_in_sms(self):
        sms = ("Bonjour Jean, ecrivez-nous a info@xguard.ca ou appelez "
               "au (438) 802-0475 pour votre formation en securite.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertIn("email", r)

    def test_other_phone_number(self):
        sms = ("Bonjour Jean, ou appelez Marie au 514-555-1234 directement. "
               "Academie XGuard: (438) 802-0475. Merci pour votre interet!")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)


class TestPrices(unittest.TestCase):
    def test_authorized_price(self):
        sms = ("Bonjour Jean, la formation est a $399 incluant tout materiel. "
               "Appelez-nous au (438) 802-0475 pour vous inscrire!")
        ok, r = validate_sms(sms)
        self.assertTrue(ok, f"Expected valid, got: {r}")

    def test_unauthorized_low_price(self):
        """$99 is not in the authorized range [300-799]."""
        sms = ("Bonjour Jean, la formation est a seulement $99! "
               "Appelez-nous au (438) 802-0475 pour reserver votre place.")
        ok, r = validate_sms(sms)
        self.assertFalse(ok)
        self.assertIn("price", r)


if __name__ == "__main__":
    unittest.main(verbosity=2)
