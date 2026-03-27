#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
seed_coaching_data.py — One-shot backfill script

Reads ALL existing transcripts for Domingos and Heidys, scores them on
8 coaching dimensions, groups by week, and pushes coaching_data +
coaching_reports rows to Supabase.

Usage:  python seed_coaching_data.py
"""

import json
import re
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

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

AGENTS = {
    "domingos": {
        "person_id": "t11",
        "transcript_dir": Path("C:/Users/nicol/Xguard sales/domingos_transcripts"),
    },
    "heidys": {
        "person_id": "v1",
        "transcript_dir": Path("C:/Users/nicol/Xguard sales/heidys_analysis/📁 Data/transcripts"),
    },
}

DIMENSIONS = [
    "intro", "qualification", "objections", "closing",
    "empathy", "energy", "duration", "engagement",
]

# ---------------------------------------------------------------------------
# Domingos classification keywords
# ---------------------------------------------------------------------------

DRONE_KW = re.compile(
    r"\b(drone|drones|télépilote|pilote|vol|aéronef|transport canada"
    r"|certificat de pilote|formation drone|rpas)\b",
    re.IGNORECASE,
)
ELITE_KW = re.compile(
    r"\b(gardien|gardiennage|sécurité|agent de sécurité|bsp|permis"
    r"|formation gardiennage|élite|elite|securisme|secourisme)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Objection patterns
# ---------------------------------------------------------------------------

OBJECTION_PATTERNS = [
    (r"\bc'est trop cher\b", "C'est trop cher"),
    (r"\bpas intéressé\b", "Pas intéressé"),
    (r"\bpas le temps\b", "Pas le temps"),
    (r"\bje vais réfléchir\b", "Je vais réfléchir"),
    (r"\bj'ai déjà\b", "J'ai déjà un fournisseur"),
    (r"\bpas besoin\b", "Pas besoin"),
    (r"\brappeler plus tard\b", "Rappeler plus tard"),
    (r"\bpas le budget\b", "Pas le budget"),
    (r"\bje ne suis pas\b", "Je ne suis pas décideur"),
    (r"\benvoyez[- ]moi\b", "Envoyez-moi de l'info"),
    (r"\bpas le bon moment\b", "Pas le bon moment"),
    (r"\bon verra\b", "On verra"),
]

# ---------------------------------------------------------------------------
# Supabase helper
# ---------------------------------------------------------------------------

def supabase_upsert(table: str, payload):
    """POST (upsert) one row or a list of rows."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code not in (200, 201, 204):
        print(f"  [WARN] Supabase {table} upsert {resp.status_code}: {resp.text[:300]}")
    return resp


def supabase_get(table: str, params: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    return requests.get(url, params=params, headers=headers)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d",
]


def parse_call_time(raw: str) -> datetime | None:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return None


def monday_of(dt: datetime) -> datetime:
    """Return the Monday 00:00 of the week containing *dt*."""
    return (dt - timedelta(days=dt.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )


def sunday_of(monday: datetime) -> datetime:
    return monday + timedelta(days=6)


# ---------------------------------------------------------------------------
# Classification (Domingos only)
# ---------------------------------------------------------------------------

def classify_call(text: str) -> str:
    has_drone = bool(DRONE_KW.search(text))
    has_elite = bool(ELITE_KW.search(text))
    if has_drone and not has_elite:
        return "drone"
    if has_elite and not has_drone:
        return "elite"
    return "autre"


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def _count(text: str, patterns: list[str]) -> int:
    total = 0
    for p in patterns:
        total += len(re.findall(p, text, re.IGNORECASE))
    return total


def _norm(raw: int, high: int) -> float:
    if raw <= 0:
        return 0.0
    return round(min(10.0, raw / high * 10), 1)


def score_intro(text: str) -> float:
    pats = [
        r"\bbonjour\b", r"\bbonsoir\b", r"\bc'est \w+ de\b",
        r"\bje m'appelle\b", r"\bmon nom\b", r"\bxguard\b",
        r"\bx[\s-]?guard\b", r"\bbienvenue\b",
        r"\bcomment allez[- ]vous\b",
    ]
    return _norm(_count(text, pats), 5)


def score_qualification(text: str) -> float:
    pats = [
        r"\bbesoin\b", r"\bcherchez\b", r"\bvoulez\b",
        r"\bintéressé\b", r"\bbudget\b", r"\bquand\b",
        r"\bcombien\b", r"\bpourquoi\b", r"\bqu['']est-ce que\b",
        r"\bquel\b", r"\bquelle\b", r"\bsituation\b",
    ]
    return _norm(_count(text, pats), 12)


def score_objections(text: str) -> float:
    pats = [
        r"\bcomprends\b", r"\beffectivement\b", r"\bpar contre\b",
        r"\bjustement\b", r"\ben fait\b", r"\bbonne question\b",
        r"\btout à fait\b", r"\bc'est normal\b",
        r"\bje vous entends\b", r"\bcependant\b", r"\btoutefois\b",
    ]
    return _norm(_count(text, pats), 6)


def score_closing(text: str) -> float:
    pats = [
        r"\bon procède\b", r"\binscription\b", r"\bconfirmer\b",
        r"\bréserver\b", r"\bon réserve\b", r"\bplace\b",
        r"\bprochaine étape\b", r"\bpaiement\b", r"\bs'inscrire\b",
        r"\bcommencer\b", r"\bon y va\b",
    ]
    return _norm(_count(text, pats), 5)


def score_empathy(text: str) -> float:
    pats = [
        r"\bcomprends\b", r"\bpas de souci\b", r"\bje vous comprends\b",
        r"\bbien sûr\b", r"\babsolument\b", r"\btout à fait\b",
        r"\bexactement\b", r"\bje vois\b", r"\bc'est vrai\b",
    ]
    return _norm(_count(text, pats), 6)


def score_energy(text: str) -> float:
    pats = [
        r"\bexcellent\b", r"\bparfait\b", r"\bsuper\b",
        r"\bfantastique\b", r"\bgénial\b", r"\bincroyable\b",
        r"\bbravo\b", r"\bmagnifique\b", r"\bformidable\b",
    ]
    excl = text.count("!")
    return _norm(excl + _count(text, pats) * 2, 12)


def score_duration(duration_s: float) -> float:
    if duration_s < 30:
        return 2.0
    if duration_s < 60:
        return 4.0
    if duration_s < 120:
        return 6.0
    if duration_s < 300:
        return 8.0
    return 10.0


def score_engagement(text: str) -> float:
    q = text.count("?")
    if q >= 20:
        return 10.0
    return round(min(10.0, q / 20 * 10), 1)


def score_call(transcript_text: str, duration_s: float) -> dict:
    return {
        "intro": score_intro(transcript_text),
        "qualification": score_qualification(transcript_text),
        "objections": score_objections(transcript_text),
        "closing": score_closing(transcript_text),
        "empathy": score_empathy(transcript_text),
        "energy": score_energy(transcript_text),
        "duration": score_duration(duration_s),
        "engagement": score_engagement(transcript_text),
    }


# ---------------------------------------------------------------------------
# Objection extraction
# ---------------------------------------------------------------------------

def extract_objections(transcripts: list[dict]) -> list[dict]:
    counts: dict[str, int] = {}
    for t in transcripts:
        text = t.get("transcript", "") or ""
        for pattern, label in OBJECTION_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                counts[label] = counts.get(label, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [{"text": lab, "count": cnt} for lab, cnt in ranked[:10]]


# ---------------------------------------------------------------------------
# Load all transcripts for one agent
# ---------------------------------------------------------------------------

def load_all_transcripts(agent_name: str, directory: Path) -> list[dict]:
    """Load every JSON file, parse call_time, return list of dicts."""
    loaded = []
    errors = 0
    for fpath in sorted(directory.glob("*.json")):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  [SKIP] {fpath.name}: {exc}")
            errors += 1
            continue

        raw_time = data.get("call_time")
        if not raw_time:
            print(f"  [SKIP] {fpath.name}: no call_time")
            errors += 1
            continue

        ct = parse_call_time(str(raw_time))
        if ct is None:
            print(f"  [SKIP] {fpath.name}: unparseable call_time '{raw_time}'")
            errors += 1
            continue

        data["_call_dt"] = ct
        data["_file"] = fpath.name
        loaded.append(data)

    print(f"  Loaded {len(loaded)} transcripts for {agent_name} ({errors} skipped)")
    return loaded


# ---------------------------------------------------------------------------
# Group by week (Monday)
# ---------------------------------------------------------------------------

def group_by_week(transcripts: list[dict]) -> dict[str, list[dict]]:
    """Return {monday_iso: [transcripts]}."""
    weeks: dict[str, list[dict]] = defaultdict(list)
    for t in transcripts:
        mon = monday_of(t["_call_dt"])
        weeks[mon.strftime("%Y-%m-%d")].append(t)
    return dict(sorted(weeks.items()))


# ---------------------------------------------------------------------------
# Process one week for one agent
# ---------------------------------------------------------------------------

def process_week(
    agent_name: str,
    person_id: str,
    monday_str: str,
    transcripts: list[dict],
    prev_scores: dict | None,
):
    """Score, build coaching_data + coaching_reports rows, push both."""

    monday_dt = datetime.strptime(monday_str, "%Y-%m-%d")
    sunday_str = sunday_of(monday_dt).strftime("%Y-%m-%d")

    is_domingos = agent_name == "domingos"

    # -- Duration list --
    durations = [t.get("duration_s", 0) or 0 for t in transcripts]
    avg_dur = round(sum(durations) / max(len(durations), 1), 1)
    total_calls = len(transcripts)

    # -- Call breakdown (Domingos only) --
    call_breakdown = None
    if is_domingos:
        call_breakdown = {"drone": 0, "elite": 0, "autre": 0}
        for t in transcripts:
            cls = classify_call(t.get("transcript", "") or "")
            call_breakdown[cls] += 1

    # ==================== coaching_data ====================
    coaching_data_row = {
        "person_id": person_id,
        "sync_date": monday_str,
        "calls_total": total_calls,
        "calls_transcribed": total_calls,
        "calls_new": 0,
        "avg_duration_sec": int(avg_dur),
        "call_breakdown": call_breakdown,
        "source": "seed",
    }
    resp = supabase_upsert("coaching_data", coaching_data_row)

    # ==================== coaching_reports ====================

    # Score every call
    all_scores = []
    for t in transcripts:
        text = t.get("transcript", "") or ""
        dur = t.get("duration_s", 0) or 0
        all_scores.append(score_call(text, dur))

    # Average per dimension
    avg_scores = {}
    for dim in DIMENSIONS:
        vals = [s[dim] for s in all_scores]
        avg_scores[dim] = round(sum(vals) / len(vals), 1)

    global_score = round(sum(avg_scores.values()) / len(avg_scores), 1)

    # Strengths / improvements
    ranked = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
    strengths = [d[0] for d in ranked[:3]]
    improvements = [d[0] for d in ranked[-3:]]

    # Objections
    top_objections = extract_objections(transcripts)

    # Comparison vs previous week
    comparison_json = {}
    if prev_scores:
        for dim in DIMENSIONS:
            comparison_json[dim] = round(
                avg_scores.get(dim, 0) - prev_scores.get(dim, 0), 1
            )
        comparison_json["global"] = round(
            global_score - prev_scores.get("_global", 0), 1
        )
    else:
        for dim in DIMENSIONS:
            comparison_json[dim] = 0.0
        comparison_json["global"] = 0.0

    coaching_report_row = {
        "person_id": person_id,
        "week_start": monday_str,
        "week_end": sunday_str,
        "report_type": "ventes_drone" if is_domingos else "ventes",
        "scores": avg_scores,
        "calls_analyzed": total_calls,
        "avg_call_duration_sec": int(avg_dur),
        "top_objections": top_objections,
        "strengths": strengths,
        "improvements": improvements,
        "recommendations": [],
        "comparison": comparison_json,
        "call_breakdown": call_breakdown,
        "raw_summary": f"Seed report: {total_calls} calls, global score {global_score}/10. "
                       f"Strengths: {', '.join(strengths)}. Improvements: {', '.join(improvements)}.",
    }
    resp2 = supabase_upsert("coaching_reports", coaching_report_row)

    # Return scores so next week can compare
    current = dict(avg_scores)
    current["_global"] = global_score
    return current


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    t_start = time.time()
    print("=" * 60)
    print("seed_coaching_data.py — backfill coaching_data + coaching_reports")
    print("=" * 60)

    grand_total_weeks = 0
    grand_total_calls = 0

    for agent_name, cfg in AGENTS.items():
        person_id = cfg["person_id"]
        tdir = cfg["transcript_dir"]

        print(f"\n--- {agent_name.upper()} (person_id={person_id}) ---")
        print(f"  Source: {str(tdir).encode('ascii', 'replace').decode()}")

        if not tdir.exists():
            print(f"  [ERROR] Directory not found — skipping.")
            continue

        transcripts = load_all_transcripts(agent_name, tdir)
        if not transcripts:
            print("  No transcripts to process.")
            continue

        weeks = group_by_week(transcripts)
        print(f"  Weeks to process: {len(weeks)}")

        prev_scores = None
        agent_calls = 0

        for monday_str, week_transcripts in weeks.items():
            n = len(week_transcripts)
            agent_calls += n
            print(f"    Week {monday_str}: {n} calls ... ", end="", flush=True)

            try:
                prev_scores = process_week(
                    agent_name, person_id, monday_str, week_transcripts, prev_scores
                )
                print("OK")
            except Exception as exc:
                print(f"ERROR: {exc}")

        grand_total_weeks += len(weeks)
        grand_total_calls += agent_calls
        print(f"  {agent_name} done: {agent_calls} calls across {len(weeks)} weeks.")

    elapsed = round(time.time() - t_start, 1)
    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {grand_total_calls} calls, {grand_total_weeks} weeks, {elapsed}s elapsed")
    print("=" * 60)


if __name__ == "__main__":
    main()
