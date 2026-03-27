#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enrich_heidys_report.py — One-shot enrichment script

Updates existing Heidys (v1) coaching_reports rows in Supabase with rich
analysis data extracted from Coaching_Heidys_Mars2026.docx:
  - 5 actionable recommendations (JSONB array)
  - Rich raw_summary text per week

Also generates a rich raw_summary for Domingos (t11) weeks based on
scores already stored in Supabase.

Usage:  python enrich_heidys_report.py
"""

import json
import sys
import time

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

HEADERS_READ = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
}

HEADERS_WRITE = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=representation",
}

# ---------------------------------------------------------------------------
# Heidys recommendations from Coaching_Heidys_Mars2026.docx
# ---------------------------------------------------------------------------

HEIDYS_RECOMMENDATIONS = [
    (
        "CLOSING CRITIQUE: Seulement 12.8% des appels contiennent une tentative "
        "de closing. M\u00e9moriser 3 phrases: 'Est-ce que vous voulez vous inscrire?', "
        "'On peut proc\u00e9der avec votre inscription maintenant', "
        "'Je peux vous inscrire tout de suite'."
    ),
    (
        "QUALIFICATION: Seulement 30.4% des appels commencent par des questions "
        "de d\u00e9couverte. Toujours poser: 'Qu'est-ce qui vous a amen\u00e9 \u00e0 nous "
        "contacter?' et 'Formation de jour, soir, ou en ligne?'"
    ),
    (
        "NEXT STEP: 59.5% des appels finissent sans action concr\u00e8te. R\u00e8gle: "
        "si pas inscrit \u2192 fixer rappel pr\u00e9cis. Si h\u00e9site \u2192 envoyer lien + "
        "confirmer rappel."
    ),
    (
        "LANGAGE: 689 mots parasites d\u00e9tect\u00e9s (1.7/appel). Remplacer "
        "'je pense que \u00e7a co\u00fbte' par 'La formation co\u00fbte exactement...', "
        "\u00e9liminer 'peut-\u00eatre', 'normalement'."
    ),
    (
        "DUR\u00c9E: Les appels 3-5 min closent 9x plus que 1-2 min. "
        "Maintenir l'engagement plus longtemps avec questions et personnalisation."
    ),
]

HEIDYS_RAW_SUMMARY = (
    "398 appels analys\u00e9s (F\u00e9v 20 - Mars 20). "
    "Taux de conversion f\u00e9vrier: 17.2%, mars: 8.2% (-46%). "
    "Forces: Introduction claire (98%), ma\u00eetrise produit (95.7%), engagement (79.9%). "
    "Probl\u00e8mes critiques: closing tent\u00e9 dans seulement 12.8% des appels, "
    "59.5% des appels sans next step, qualification faible (30.4%). "
    "Dur\u00e9e optimale: 3-5 min (26.5% closing rate vs 0% pour <1 min)."
)

# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def supabase_get(table: str, params: dict) -> list[dict]:
    """GET rows from Supabase. Returns list of dicts."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    resp = requests.get(url, params=params, headers=HEADERS_READ)
    if resp.status_code != 200:
        print(f"  [ERROR] GET {table} {resp.status_code}: {resp.text[:300]}")
        return []
    return resp.json()


def supabase_patch(table: str, row_id: str, payload: dict) -> bool:
    """PATCH a single row by its id."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}"
    resp = requests.patch(url, json=payload, headers=HEADERS_WRITE)
    if resp.status_code not in (200, 204):
        print(f"  [ERROR] PATCH {table} id={row_id} -> {resp.status_code}: {resp.text[:300]}")
        return False
    return True


# ---------------------------------------------------------------------------
# Build rich summary for Domingos from existing scores
# ---------------------------------------------------------------------------

DIMENSIONS = [
    "intro", "qualification", "objections", "closing",
    "empathy", "energy", "duration", "engagement",
]

DIMENSION_LABELS = {
    "intro": "Introduction",
    "qualification": "Qualification",
    "objections": "Gestion objections",
    "closing": "Closing",
    "empathy": "Empathie",
    "energy": "\u00c9nergie",
    "duration": "Dur\u00e9e",
    "engagement": "Engagement",
}


def build_domingos_summary(report: dict) -> str:
    """Build a rich raw_summary for a Domingos report from its stored scores."""
    scores = report.get("scores") or {}
    calls = report.get("calls_analyzed", 0)
    week_start = report.get("week_start", "?")
    week_end = report.get("week_end", "?")
    strengths = report.get("strengths") or []
    improvements = report.get("improvements") or []
    call_breakdown = report.get("call_breakdown") or {}

    # Compute global score from dimension scores
    score_vals = [scores.get(d, 0) for d in DIMENSIONS if d in scores]
    global_score = round(sum(score_vals) / max(len(score_vals), 1), 1)

    # Top / bottom dimensions
    ranked = sorted(
        [(d, scores.get(d, 0)) for d in DIMENSIONS if d in scores],
        key=lambda x: x[1], reverse=True,
    )
    top_dims = ", ".join(
        f"{DIMENSION_LABELS.get(d, d)} ({v}/10)" for d, v in ranked[:3]
    )
    low_dims = ", ".join(
        f"{DIMENSION_LABELS.get(d, d)} ({v}/10)" for d, v in ranked[-3:]
    )

    # Breakdown string
    breakdown_str = ""
    if call_breakdown:
        parts = [f"{k}: {v}" for k, v in call_breakdown.items()]
        breakdown_str = f" R\u00e9partition: {', '.join(parts)}."

    avg_dur = report.get("avg_call_duration_sec", 0)
    dur_min = round(avg_dur / 60, 1) if avg_dur else 0

    summary = (
        f"{calls} appels analys\u00e9s (semaine {week_start} au {week_end}). "
        f"Score global: {global_score}/10. "
        f"Dur\u00e9e moyenne: {dur_min} min. "
        f"Forces: {top_dims}. "
        f"\u00c0 am\u00e9liorer: {low_dims}."
        f"{breakdown_str}"
    )
    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t_start = time.time()
    print("=" * 60)
    print("enrich_heidys_report.py")
    print("  Enriching Heidys (v1) & Domingos (t11) coaching_reports")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Fetch ALL Heidys coaching_reports
    # ------------------------------------------------------------------
    print("\n--- Fetching Heidys (v1) coaching_reports ---")
    heidys_rows = supabase_get("coaching_reports", {
        "person_id": "eq.v1",
        "select": "id,person_id,week_start,week_end,scores,calls_analyzed,"
                  "avg_call_duration_sec,strengths,improvements,"
                  "call_breakdown,raw_summary,recommendations",
        "order": "week_start.asc",
    })
    print(f"  Found {len(heidys_rows)} Heidys report rows.")

    if not heidys_rows:
        print("  [WARN] No Heidys rows found. Nothing to update.")
    else:
        updated = 0
        for row in heidys_rows:
            row_id = row["id"]
            week = row.get("week_start", "?")

            # Build per-week raw_summary with the global score from stored scores
            scores = row.get("scores") or {}
            score_vals = [scores.get(d, 0) for d in DIMENSIONS if d in scores]
            global_score = round(sum(score_vals) / max(len(score_vals), 1), 1)

            # Personalize the raw_summary with this week's global score
            week_summary = HEIDYS_RAW_SUMMARY.replace(
                "Score global: X/10",
                f"Score global: {global_score}/10",
            )

            payload = {
                "recommendations": HEIDYS_RECOMMENDATIONS,
                "raw_summary": week_summary,
            }

            print(f"  PATCH week {week} (id={row_id}) ... ", end="", flush=True)
            ok = supabase_patch("coaching_reports", row_id, payload)
            if ok:
                updated += 1
                print("OK")
            else:
                print("FAILED")

        print(f"  Heidys: {updated}/{len(heidys_rows)} rows updated.")

    # ------------------------------------------------------------------
    # 2. Fetch ALL Domingos coaching_reports and enrich raw_summary
    # ------------------------------------------------------------------
    print("\n--- Fetching Domingos (t11) coaching_reports ---")
    domingos_rows = supabase_get("coaching_reports", {
        "person_id": "eq.t11",
        "select": "id,person_id,week_start,week_end,scores,calls_analyzed,"
                  "avg_call_duration_sec,strengths,improvements,"
                  "call_breakdown,raw_summary",
        "order": "week_start.asc",
    })
    print(f"  Found {len(domingos_rows)} Domingos report rows.")

    if not domingos_rows:
        print("  [WARN] No Domingos rows found. Nothing to update.")
    else:
        updated = 0
        for row in domingos_rows:
            row_id = row["id"]
            week = row.get("week_start", "?")

            rich_summary = build_domingos_summary(row)

            payload = {
                "raw_summary": rich_summary,
            }

            print(f"  PATCH week {week} (id={row_id}) ... ", end="", flush=True)
            ok = supabase_patch("coaching_reports", row_id, payload)
            if ok:
                updated += 1
                print("OK")
            else:
                print("FAILED")

        print(f"  Domingos: {updated}/{len(domingos_rows)} rows updated.")

    # ------------------------------------------------------------------
    # Done
    # ------------------------------------------------------------------
    elapsed = round(time.time() - t_start, 1)
    print(f"\n{'=' * 60}")
    print(f"DONE in {elapsed}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
