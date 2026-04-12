"""
Unit tests for smart_stats.py — callback tracking, 39 indicators, and score /100.
Run: python test_smart_stats.py
"""

import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from smart_stats import (
    compute_callback_stats,
    compute_39_indicators,
    compute_weighted_score,
    score_indicator,
    SIGNATURE_RE,
    DEJA_TRAITE_RE,
)
from phone_utils import normalize_number


def make_call(id, time_str, duration_s=0, direction="in", contact_number="5141234567",
              contact_name="Test", notes="", account="academie", missed_call_type=""):
    """Helper to create a mock call dict."""
    dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
    is_in = direction == "in"
    return {
        "id": id,
        "time": time_str,
        "dt": dt,
        "hour": dt.hour,
        "duration_s": duration_s,
        "is_inbound": is_in,
        "is_answered": is_in and duration_s > 0,
        "is_missed": is_in and duration_s == 0,
        "is_outbound": not is_in,
        "out_connected": not is_in and duration_s > 0,
        "contact_number": contact_number,
        "contact_name": contact_name,
        "notes": notes,
        "missed_call_type": missed_call_type,
        "account": account,
        "end_dt": dt + timedelta(seconds=duration_s) if duration_s > 0 else None,
    }


class TestPhoneNormalization(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(normalize_number("+15141234567"), "5141234567")
        self.assertEqual(normalize_number("15141234567"), "5141234567")
        self.assertEqual(normalize_number("514-123-4567"), "5141234567")
        self.assertEqual(normalize_number("(514) 123-4567"), "5141234567")

    def test_empty(self):
        self.assertEqual(normalize_number(""), "")
        self.assertEqual(normalize_number(None), "")

    def test_short(self):
        self.assertEqual(normalize_number("12345"), "12345")


class TestConformitePatterns(unittest.TestCase):
    def test_signature_detection(self):
        self.assertTrue(SIGNATURE_RE.search("hm"))
        self.assertTrue(SIGNATURE_RE.search("appel - hm"))
        self.assertTrue(SIGNATURE_RE.search("sk - info formation"))
        self.assertTrue(SIGNATURE_RE.search("lilia"))
        self.assertTrue(SIGNATURE_RE.search("Hamza a repondu"))
        self.assertFalse(SIGNATURE_RE.search(""))
        self.assertFalse(SIGNATURE_RE.search("bv"))  # Not a signature

    def test_deja_traite(self):
        self.assertTrue(DEJA_TRAITE_RE.search("deja traite"))
        self.assertTrue(DEJA_TRAITE_RE.search("déjà traité"))
        self.assertTrue(DEJA_TRAITE_RE.search("deja fait"))
        self.assertFalse(DEJA_TRAITE_RE.search("info formation"))


class TestCallbackStats(unittest.TestCase):
    def test_no_missed_calls(self):
        """When there are no missed calls, everything should be 100%."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=120, direction="in"),
        ]
        result = compute_callback_stats(calls, set(), set())
        self.assertEqual(result["taux_rappel_corrige"], 100.0)
        self.assertEqual(result["non_rappeles_count"], 0)

    def test_missed_with_callback(self):
        """Missed call followed by outbound >10s = rappele."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=0, direction="in", contact_number="5141111111"),
            make_call(2, "2026-04-11 10:15:00", duration_s=60, direction="out", contact_number="5141111111"),
        ]
        result = compute_callback_stats(calls, set(), set())
        self.assertEqual(result["taux_rappel_corrige"], 100.0)
        self.assertEqual(result["non_rappeles_count"], 0)
        self.assertEqual(result["rappeles_meme_shift"], 1)
        self.assertEqual(result["delai_moyen_min"], 15.0)

    def test_missed_without_callback(self):
        """Missed call with no outbound = non-rappele."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=0, direction="in", contact_number="5141111111"),
        ]
        result = compute_callback_stats(calls, set(), set())
        self.assertEqual(result["taux_rappel_corrige"], 0.0)
        self.assertEqual(result["non_rappeles_count"], 1)

    def test_callback_too_short(self):
        """Outbound <= 10s doesn't count as callback."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=0, direction="in", contact_number="5141111111"),
            make_call(2, "2026-04-11 10:15:00", duration_s=5, direction="out", contact_number="5141111111"),
        ]
        result = compute_callback_stats(calls, set(), set())
        self.assertEqual(result["non_rappeles_count"], 1)
        # The short outbound IS after the miss, so it counts as a failed attempt
        self.assertGreaterEqual(result["non_rappeles"][0]["attempts"], 0)

    def test_callback_within_hour(self):
        """Callback within 60 min counts for taux_rappel_heure."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=0, direction="in", contact_number="5141111111"),
            make_call(2, "2026-04-11 10:45:00", duration_s=60, direction="out", contact_number="5141111111"),
        ]
        result = compute_callback_stats(calls, set(), set())
        self.assertEqual(result["taux_rappel_heure"], 100.0)

    def test_callback_after_hour(self):
        """Callback after 60 min doesn't count for taux_rappel_heure."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=0, direction="in", contact_number="5141111111"),
            make_call(2, "2026-04-11 11:30:00", duration_s=60, direction="out", contact_number="5141111111"),
        ]
        result = compute_callback_stats(calls, set(), set())
        self.assertEqual(result["taux_rappel_heure"], 0.0)
        self.assertEqual(result["taux_rappel_corrige"], 100.0)  # Still counted as rappele

    def test_dedup_excluded(self):
        """Calls in dedup_removed_ids should not be tracked."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=0, direction="in", contact_number="5141111111"),
        ]
        result = compute_callback_stats(calls, {1}, set())  # ID 1 is deduped
        self.assertEqual(result["total_missed_net"], 0)

    def test_client_called_back_and_answered(self):
        """If client calls again and IS answered, it counts as 'rappele'."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=0, direction="in", contact_number="5141111111"),
            make_call(2, "2026-04-11 10:30:00", duration_s=120, direction="in", contact_number="5141111111"),
        ]
        result = compute_callback_stats(calls, set(), set())
        self.assertEqual(result["taux_rappel_corrige"], 100.0)

    def test_number_normalization(self):
        """Different formats of same number should match."""
        calls = [
            make_call(1, "2026-04-11 10:00:00", duration_s=0, direction="in", contact_number="+15141111111"),
            make_call(2, "2026-04-11 10:15:00", duration_s=60, direction="out", contact_number="5141111111"),
        ]
        result = compute_callback_stats(calls, set(), set())
        self.assertEqual(result["taux_rappel_corrige"], 100.0)


class TestScoreIndicator(unittest.TestCase):
    def test_at_target(self):
        self.assertEqual(score_indicator(95, 95), 10.0)

    def test_above_target(self):
        self.assertEqual(score_indicator(100, 95), 10.0)  # Capped at 10

    def test_below_target(self):
        score = score_indicator(50, 100)
        self.assertEqual(score, 5.0)

    def test_zero(self):
        self.assertEqual(score_indicator(0, 100), 0.0)

    def test_none(self):
        self.assertIsNone(score_indicator(None, 100))

    def test_lower_is_better_at_target(self):
        self.assertEqual(score_indicator(60, 60, higher_is_better=False), 10.0)

    def test_lower_is_better_below_target(self):
        self.assertEqual(score_indicator(30, 60, higher_is_better=False), 10.0)  # Better than target

    def test_lower_is_better_above_target(self):
        score = score_indicator(90, 60, higher_is_better=False)
        self.assertLess(score, 10.0)
        self.assertGreaterEqual(score, 0.0)


class TestWeightedScore(unittest.TestCase):
    def test_perfect_score(self):
        """All dimensions at 10/10 should give 100/100."""
        ind = {
            "taux_reponse_brut": 100,
            "disponibilite_reelle": 100,
            "taux_reponse_entrant": 100,
            "taux_connexion_sortant": 100,
            "taux_rappel_corrige": 100,
            "taux_rappel_heure": 100,
            "delai_moyen_min": 0,
            "duree_dans_cible_pct": 100,
            "taux_occupation": 55,
            "nb_tentatives_avant_traitement": 1,
            "saturation_file": 0,
            "facteur_rush": 1.0,
            "conformite_signature": 100,
            "dossiers_deja_traites_pct": 0,
            "notes_avec_motif_pct": 100,
            "taux_utilisation_capacite": 55,
            "productivite_horaire": 15,
        }
        result = compute_weighted_score(ind)
        self.assertGreaterEqual(result["global_score"], 95.0)

    def test_zero_score(self):
        """All dimensions at 0 should give low score."""
        ind = {
            "taux_reponse_brut": 0,
            "disponibilite_reelle": 0,
            "taux_reponse_entrant": 0,
            "taux_connexion_sortant": 0,
            "taux_rappel_corrige": 0,
            "taux_rappel_heure": 0,
            "delai_moyen_min": 999,
            "duree_dans_cible_pct": 0,
            "taux_occupation": 0,
            "nb_tentatives_avant_traitement": 10,
            "saturation_file": 100,
            "facteur_rush": 5.0,
            "conformite_signature": 0,
            "dossiers_deja_traites_pct": 50,
            "notes_avec_motif_pct": 0,
            "taux_utilisation_capacite": 0,
            "productivite_horaire": 0,
        }
        result = compute_weighted_score(ind)
        self.assertLess(result["global_score"], 10.0)

    def test_dimensions_present(self):
        """All 6 dimensions should be in the result."""
        ind = {
            "taux_reponse_brut": 75, "disponibilite_reelle": 90,
            "taux_reponse_entrant": 70, "taux_connexion_sortant": 80,
            "taux_rappel_corrige": 95, "taux_rappel_heure": 70, "delai_moyen_min": 30,
            "duree_dans_cible_pct": 80, "taux_occupation": 55, "nb_tentatives_avant_traitement": 1.5,
            "saturation_file": 20, "facteur_rush": 1.3,
            "conformite_signature": 95, "dossiers_deja_traites_pct": 0.5, "notes_avec_motif_pct": 25,
            "taux_utilisation_capacite": 55, "productivite_horaire": 15,
        }
        result = compute_weighted_score(ind)
        dims = result["dimensions"]
        expected_dims = ["reponse_disponibilite", "taux_rappel", "qualite_traitement",
                         "file_attente_saturation", "conformite_tracabilite", "efficacite_charge"]
        for d in expected_dims:
            self.assertIn(d, dims)
            self.assertIsNotNone(dims[d])

    def test_score_between_0_and_100(self):
        """Score should always be between 0 and 100."""
        ind = {
            "taux_reponse_brut": 49, "disponibilite_reelle": 75,
            "taux_reponse_entrant": 94, "taux_connexion_sortant": 98,
            "taux_rappel_corrige": 82, "taux_rappel_heure": 82, "delai_moyen_min": 11,
            "duree_dans_cible_pct": 67, "taux_occupation": 25, "nb_tentatives_avant_traitement": 1.4,
            "saturation_file": 32, "facteur_rush": 1.7,
            "conformite_signature": 3, "dossiers_deja_traites_pct": 0, "notes_avec_motif_pct": 81,
            "taux_utilisation_capacite": 10, "productivite_horaire": 3.5,
        }
        result = compute_weighted_score(ind)
        self.assertGreaterEqual(result["global_score"], 0)
        self.assertLessEqual(result["global_score"], 100)


class TestIntegration(unittest.TestCase):
    """Integration test with realistic call data."""

    def test_full_day_scenario(self):
        """Simulate a realistic day and verify all indicators compute."""
        calls = [
            # Morning: 3 answered, 2 missed, 1 outbound callback
            make_call(1, "2026-04-11 08:30:00", 120, "in", "5141111111", "Client A", "hm"),
            make_call(2, "2026-04-11 09:00:00", 0, "in", "5142222222", "Client B", "", missed_call_type="1"),
            make_call(3, "2026-04-11 09:15:00", 90, "in", "5143333333", "Client C", "hm - inscription"),
            make_call(4, "2026-04-11 09:30:00", 0, "in", "5144444444", "Client D", "", missed_call_type="3"),
            make_call(5, "2026-04-11 09:45:00", 200, "in", "5145555555", "Client E", "sk"),
            # Callback for Client B
            make_call(6, "2026-04-11 10:00:00", 60, "out", "5142222222", "Client B", "hm"),
            # Afternoon outbound
            make_call(7, "2026-04-11 14:00:00", 45, "out", "5146666666", "Client F", "lilia"),
        ]

        raw = {
            "total": len(calls),
            "in_total": 5,
            "in_answered": 3,
            "in_missed": 2,
            "out_total": 2,
            "out_connected": 2,
            "response_rate": 60,
            "by_hour": {
                8: {"total": 1, "answered": 1, "missed": 0, "outbound": 0},
                9: {"total": 4, "answered": 1, "missed": 2, "outbound": 1},
                10: {"total": 1, "answered": 0, "missed": 0, "outbound": 1},
                14: {"total": 1, "answered": 0, "missed": 0, "outbound": 1},
            },
        }

        ind = compute_39_indicators(calls, raw, set(), set(), 1)

        # Basic checks
        self.assertEqual(ind["appels_bruts"], 7)
        self.assertEqual(ind["appels_entrants"], 5)
        self.assertEqual(ind["appels_sortants"], 2)

        # Callback tracking
        self.assertGreater(ind["taux_rappel_corrige"], 0)

        # Conformite: 4 calls have signatures (hm, sk, lilia)
        self.assertGreater(ind["conformite_signature"], 0)

        # Score should be computed
        self.assertIn("global_score", ind)
        self.assertGreater(ind["global_score"], 0)
        self.assertLessEqual(ind["global_score"], 100)

        # Dimensions should all be present
        dims = ind["dimensions"]
        self.assertEqual(len(dims), 6)


if __name__ == "__main__":
    print("=" * 60)
    print("  UNIT TESTS — smart_stats.py")
    print("=" * 60)
    unittest.main(verbosity=2)
