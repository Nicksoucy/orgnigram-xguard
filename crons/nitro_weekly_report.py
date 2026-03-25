#!/usr/bin/env python3
"""
nitro_weekly_report.py
Generates weekly coaching reports for Heidys and Domingos.
Scheduled: Friday at 15:00 on Nitro.

Analyzes transcripts from Mon-Fri, scores on 8 coaching dimensions,
pushes results to Supabase and saves local JSON backup.
"""

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
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
    "heidys": {
        "person_id": "v1",
        "transcript_dir": "C:/Users/user/xguard_transcripts/heidys/",
        "report_type": "ventes",
    },
    "domingos": {
        "person_id": "t11",
        "transcript_dir": "C:/Users/user/xguard_transcripts/domingos/",
        "report_type": "ventes_drone",
    },
}

LOCAL_REPORT_DIR = "C:/Users/user/xguard_reports/"
DIMENSIONS = [
    "intro", "qualification", "objections", "closing",
    "empathy", "energy", "duration", "engagement",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("nitro_weekly_report")

# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def supabase_upsert(table: str, data: dict | list) -> requests.Response:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    return requests.post(url, json=data, headers=headers)


def supabase_insert(table: str, data: dict) -> requests.Response:
    """Insert a single row (no upsert)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    return requests.post(url, json=data, headers=headers)


def supabase_get(table: str, params: dict) -> requests.Response:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    return requests.get(url, params=params, headers=headers)


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def get_week_range() -> tuple[datetime, datetime]:
    """Return (Monday 00:00, Friday 23:59:59) for the current week."""
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    friday = monday + timedelta(days=4, hours=23, minutes=59, seconds=59)
    return monday, friday


def get_previous_week_range() -> tuple[datetime, datetime]:
    monday, friday = get_week_range()
    return monday - timedelta(days=7), friday - timedelta(days=7)


# ---------------------------------------------------------------------------
# Transcript loading
# ---------------------------------------------------------------------------

def load_transcripts(directory: str, week_start: datetime, week_end: datetime) -> list[dict]:
    """Load all JSON transcript files whose call_time falls within the week."""
    transcripts = []
    dir_path = Path(directory)
    if not dir_path.exists():
        log.warning("Transcript directory not found: %s", directory)
        return transcripts

    for fpath in dir_path.glob("*.json"):
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Failed to read %s: %s", fpath, exc)
            continue

        call_time_str = data.get("call_time")
        if not call_time_str:
            continue

        # Support multiple datetime formats
        call_time = None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                call_time = datetime.strptime(call_time_str, fmt)
                break
            except ValueError:
                continue

        if call_time is None:
            log.warning("Unparseable call_time in %s: %s", fpath, call_time_str)
            continue

        if week_start <= call_time <= week_end:
            data["_source_file"] = str(fpath)
            transcripts.append(data)

    log.info("Loaded %d transcripts from %s", len(transcripts), directory)
    return transcripts


# ---------------------------------------------------------------------------
# Classification (Domingos)
# ---------------------------------------------------------------------------

DRONE_KEYWORDS = re.compile(
    r"\b(drone|drones|télépilote|télépilotage|vol|survol|aérien|rpas|uav)\b", re.IGNORECASE
)
ELITE_KEYWORDS = re.compile(
    r"\b(élite|elite|formation élite|programme élite|coaching élite)\b", re.IGNORECASE
)


def classify_call(transcript: dict) -> str:
    """Return 'drone', 'elite', or 'autre'."""
    classification = transcript.get("classification", "").lower().strip()
    if classification in ("drone", "elite", "autre"):
        return classification

    text = transcript.get("transcript", "") or ""
    text += " " + (transcript.get("summary", "") or "")

    if ELITE_KEYWORDS.search(text):
        return "elite"
    if DRONE_KEYWORDS.search(text):
        return "drone"
    return "autre"


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def _count_patterns(text: str, patterns: list[str]) -> int:
    count = 0
    for pat in patterns:
        count += len(re.findall(pat, text, re.IGNORECASE))
    return count


def _normalize(raw: int, low: int = 1, high: int = 10) -> float:
    """Normalize a raw count to 0-10 scale. Caps at 10."""
    if raw <= 0:
        return 0.0
    score = min(10.0, raw / high * 10)
    return round(score, 1)


def score_intro(text: str) -> float:
    patterns = [
        r"\bbonjour\b", r"\bbonsoir\b", r"\bxguard\b", r"\bx[\s-]?guard\b",
        r"\bje m'appelle\b", r"\bmon nom\b", r"\bje suis\b",
        r"\bbienvenue\b", r"\bcomment allez[- ]vous\b",
    ]
    raw = _count_patterns(text, patterns)
    return _normalize(raw, high=5)


def score_qualification(text: str) -> float:
    patterns = [
        r"\?", r"\bbudget\b", r"\bquand\b", r"\bcombien\b",
        r"\bbesoin\b", r"\bobjectif\b", r"\bpourquoi\b",
        r"\bqu['']est-ce que\b", r"\bquel\b", r"\bquelle\b",
        r"\bactuellement\b", r"\bsituation\b", r"\bdélai\b",
        r"\btimeline\b", r"\béchéance\b",
    ]
    raw = _count_patterns(text, patterns)
    return _normalize(raw, high=12)


def score_objections(text: str) -> float:
    patterns = [
        r"\bje comprends\b", r"\bjustement\b", r"\ben fait\b",
        r"\bbonne question\b", r"\btout à fait\b",
        r"\bc'est normal\b", r"\bje vous entends\b",
        r"\beffectivement\b", r"\bcependant\b", r"\btoutefois\b",
    ]
    raw = _count_patterns(text, patterns)
    return _normalize(raw, high=6)


def score_closing(text: str) -> float:
    patterns = [
        r"\binscription\b", r"\bs'inscrire\b", r"\bon réserve\b",
        r"\bplace\b", r"\bprochaine étape\b", r"\bpaiement\b",
        r"\bconfirmer\b", r"\bréserver\b", r"\bcommencer\b",
        r"\bon y va\b", r"\bsigner\b", r"\bengagement\b",
    ]
    raw = _count_patterns(text, patterns)
    return _normalize(raw, high=5)


def score_empathy(text: str) -> float:
    patterns = [
        r"\bje comprends\b", r"\babsolument\b", r"\btout à fait\b",
        r"\bexactement\b", r"\bbien sûr\b", r"\bje vois\b",
        r"\bc'est vrai\b", r"\bje suis d'accord\b",
        r"\bje vous comprends\b",
    ]
    raw = _count_patterns(text, patterns)
    return _normalize(raw, high=6)


def score_energy(text: str) -> float:
    exclamations = text.count("!")
    positive_words = [
        r"\bexcellent\b", r"\bparfait\b", r"\bsuper\b", r"\bgénial\b",
        r"\bfantastique\b", r"\bincroyable\b", r"\bbravo\b",
        r"\bmagnifique\b", r"\bformidable\b",
    ]
    raw = exclamations + _count_patterns(text, positive_words) * 2
    return _normalize(raw, high=12)


def score_duration(duration_sec: float) -> float:
    minutes = duration_sec / 60
    if minutes < 2:
        return 3.0
    elif minutes < 5:
        return 6.0
    elif minutes < 15:
        return 9.0
    elif minutes <= 30:
        return 10.0
    else:
        return 7.0


def score_engagement(transcript: dict) -> float:
    text = transcript.get("transcript", "") or ""
    # Count question marks from both sides as proxy for back-and-forth
    questions = text.count("?")
    # Word count balance: check if there's reasonable back-and-forth
    agent_words = len((transcript.get("agent_text", "") or "").split())
    customer_words = len((transcript.get("customer_text", "") or "").split())

    # If agent/customer text not split, estimate from total
    if agent_words == 0 and customer_words == 0:
        total_words = len(text.split())
        # Assume some balance — use question count as main signal
        balance_score = min(5.0, total_words / 100 * 2)
    else:
        total = agent_words + customer_words
        if total == 0:
            return 0.0
        ratio = min(agent_words, customer_words) / max(agent_words, customer_words) if max(agent_words, customer_words) > 0 else 0
        balance_score = ratio * 5  # 0-5 from balance

    question_score = min(5.0, questions / 6 * 5)  # 0-5 from questions
    return round(min(10.0, balance_score + question_score), 1)


def score_call(transcript: dict) -> dict:
    """Score a single call on all 8 dimensions. Returns {dimension: score}."""
    text = transcript.get("transcript", "") or ""
    duration_sec = transcript.get("duration_sec", 0) or 0

    return {
        "intro": score_intro(text),
        "qualification": score_qualification(text),
        "objections": score_objections(text),
        "closing": score_closing(text),
        "empathy": score_empathy(text),
        "energy": score_energy(text),
        "duration": score_duration(duration_sec),
        "engagement": score_engagement(transcript),
    }


# ---------------------------------------------------------------------------
# Objection extraction
# ---------------------------------------------------------------------------

# Objection patterns per report type — tuned to each sales context
OBJECTION_PATTERNS_VENTES = [
    # Formation gardiennage (Heidys) — relevant objections for training sales
    (r"c'est trop cher|trop dispendieux|trop d'argent", "C'est trop cher"),
    (r"pas le budget|pas les moyens|pas capable de payer", "Pas le budget"),
    (r"c'est combien|le prix|ça coûte combien", "Question sur le prix"),
    (r"je vais réfléchir|je vais y penser|laisser.*réfléchir", "Je vais reflechir"),
    (r"pas le temps|pas disponible|trop occup", "Pas le temps"),
    (r"pas intéressé|ça m'intéresse pas|non merci", "Pas interesse"),
    (r"pas le bon moment|pas maintenant|plus tard", "Pas le bon moment"),
    (r"je ne suis pas.*décideur|en parler à|demander à|mon (mari|conjoint|patron|boss)", "Doit consulter quelqu'un"),
    (r"envoyez[- ]moi|envoie[- ]moi.*info|par courriel|par email", "Envoyez-moi de l'info"),
    (r"c'est quand|prochaine cohorte|prochaine date|quand ça commence", "Quand est la prochaine cohorte"),
    (r"est-ce que c'est reconnu|accrédité|valide|BSP.*reconnu", "Est-ce reconnu/accredite"),
    (r"rappeler plus tard|rappelle[- ]moi", "Rappeler plus tard"),
]

OBJECTION_PATTERNS_DRONE = [
    # Formation drone (Domingos) — relevant for drone pilot training
    (r"c'est trop cher|trop dispendieux|trop d'argent", "C'est trop cher"),
    (r"pas le budget|pas les moyens|pas capable de payer", "Pas le budget"),
    (r"c'est combien|le prix|ça coûte combien", "Question sur le prix"),
    (r"je vais réfléchir|je vais y penser|laisser.*réfléchir", "Je vais reflechir"),
    (r"pas intéressé|ça m'intéresse pas|non merci", "Pas interesse"),
    (r"transport canada|TC|réglementation|légal", "Questions reglementation TC"),
    (r"est-ce que c'est reconnu|accrédité|certifi", "Est-ce reconnu/certifie"),
    (r"déjà.*licen|déjà.*brevet|déjà.*formation", "Deja une formation/licence"),
    (r"envoyez[- ]moi|envoie[- ]moi.*info|par courriel", "Envoyez-moi de l'info"),
    (r"pas le temps|pas disponible|trop occup", "Pas le temps"),
    (r"c'est quand|prochaine.*date|quand ça commence", "Quand est la prochaine session"),
    (r"rappeler plus tard|rappelle[- ]moi", "Rappeler plus tard"),
]


def extract_objections(transcripts: list[dict], report_type: str = "ventes") -> list[dict]:
    """Return top objections as [{text, count}], sorted by count desc."""
    patterns = OBJECTION_PATTERNS_DRONE if report_type == "ventes_drone" else OBJECTION_PATTERNS_VENTES
    counts: dict[str, int] = {}
    for t in transcripts:
        text = t.get("transcript", "") or ""
        for pattern, label in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                counts[label] = counts.get(label, 0) + 1

    sorted_objections = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [{"text": label, "count": cnt} for label, cnt in sorted_objections[:10]]


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

def generate_recommendations(avg_scores: dict) -> list[str]:
    """Generate coaching recommendations based on lowest-scoring dimensions."""
    recommendations_map = {
        "intro": "Travailler l'accroche : mentionner son nom, XGuard et une phrase d'accroche personnalisée dès les premières secondes.",
        "qualification": "Poser davantage de questions de découverte (budget, besoins, délais) avant de présenter l'offre.",
        "objections": "Pratiquer le traitement des objections : reformuler, valider puis recadrer vers la valeur.",
        "closing": "Inclure systématiquement un appel à l'action clair en fin d'appel (inscription, prochaine étape, réservation).",
        "empathy": "Renforcer l'écoute active : utiliser plus de reformulations et de marqueurs d'empathie.",
        "energy": "Augmenter l'enthousiasme vocal : utiliser un ton plus dynamique et des mots positifs.",
        "duration": "Ajuster la durée des appels : viser 5-15 minutes pour un échange complet sans perdre l'attention.",
        "engagement": "Favoriser la participation du prospect : poser des questions ouvertes pour créer un vrai dialogue.",
    }
    sorted_dims = sorted(avg_scores.items(), key=lambda x: x[1])
    recs = []
    for dim, _score in sorted_dims[:3]:
        recs.append(recommendations_map.get(dim, f"Améliorer la dimension '{dim}'."))
    return recs


def compute_weekly_summary(
    transcripts: list[dict],
    agent_name: str,
    person_id: str,
    report_type: str,
    week_start: datetime,
    week_end: datetime,
) -> dict:
    """Compute full weekly summary for an agent."""
    if not transcripts:
        return {}

    # Score each call
    all_scores = []
    for t in transcripts:
        scores = score_call(t)
        t["_scores"] = scores
        all_scores.append(scores)

    # Average scores per dimension
    avg_scores = {}
    for dim in DIMENSIONS:
        values = [s[dim] for s in all_scores]
        avg_scores[dim] = round(sum(values) / len(values), 1)

    global_score = round(sum(avg_scores.values()) / len(avg_scores), 1)

    # Top 3 strengths and improvements
    sorted_dims = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)
    strengths = [d[0] for d in sorted_dims[:3]]
    improvements = [d[0] for d in sorted_dims[-3:]]

    # Objections
    top_objections = extract_objections(transcripts, report_type)

    # Recommendations
    recommendations = generate_recommendations(avg_scores)

    # Call breakdown
    total_calls = len(transcripts)
    durations = [t.get("duration_sec", 0) or 0 for t in transcripts]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    # Direction breakdown
    direction_breakdown = {}
    for t in transcripts:
        d = t.get("direction", "unknown")
        direction_breakdown[d] = direction_breakdown.get(d, 0) + 1

    # Duration buckets
    duration_buckets = {"<2min": 0, "2-5min": 0, "5-15min": 0, "15-30min": 0, ">30min": 0}
    for dur in durations:
        mins = dur / 60
        if mins < 2:
            duration_buckets["<2min"] += 1
        elif mins < 5:
            duration_buckets["2-5min"] += 1
        elif mins < 15:
            duration_buckets["5-15min"] += 1
        elif mins <= 30:
            duration_buckets["15-30min"] += 1
        else:
            duration_buckets[">30min"] += 1

    # Classification breakdown (Domingos)
    call_breakdown = None
    if agent_name == "domingos":
        call_breakdown = {"drone": 0, "elite": 0, "autre": 0}
        for t in transcripts:
            cls = classify_call(t)
            t["_classification"] = cls
            call_breakdown[cls] += 1

    # Delta vs previous week
    comparison = fetch_previous_week_comparison(person_id, avg_scores, global_score, week_start)

    # Raw text summary
    raw_summary = build_raw_summary(
        agent_name, total_calls, global_score, avg_scores,
        strengths, improvements, top_objections, recommendations,
        call_breakdown, week_start, week_end,
    )

    report = {
        "person_id": person_id,
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "report_type": report_type,
        "scores": avg_scores,
        "global_score": global_score,
        "calls_analyzed": total_calls,
        "avg_call_duration_sec": avg_duration,
        "top_objections": top_objections,
        "strengths": strengths,
        "improvements": improvements,
        "recommendations": recommendations,
        "comparison": comparison,
        "call_breakdown": call_breakdown,
        "direction_breakdown": direction_breakdown,
        "duration_buckets": duration_buckets,
        "raw_summary": raw_summary,
    }

    return report


def fetch_previous_week_comparison(
    person_id: str, current_scores: dict, current_global: float, week_start: datetime
) -> dict:
    """Fetch last week's report from Supabase and compute deltas."""
    prev_start = (week_start - timedelta(days=7)).strftime("%Y-%m-%d")
    comparison = {"global_delta": 0.0}
    for dim in DIMENSIONS:
        comparison[f"{dim}_delta"] = 0.0

    try:
        resp = supabase_get("coaching_reports", {
            "person_id": f"eq.{person_id}",
            "week_start": f"eq.{prev_start}",
            "select": "scores,global_score",
        })
        if resp.status_code == 200:
            rows = resp.json()
            if rows:
                prev = rows[0]
                prev_scores = prev.get("scores", {})
                prev_global = prev.get("global_score", 0)
                comparison["global_delta"] = round(current_global - prev_global, 1)
                for dim in DIMENSIONS:
                    prev_val = prev_scores.get(dim, 0)
                    comparison[f"{dim}_delta"] = round(current_scores.get(dim, 0) - prev_val, 1)
        else:
            log.warning("Failed to fetch previous report: %s %s", resp.status_code, resp.text)
    except Exception as exc:
        log.warning("Error fetching previous week comparison: %s", exc)

    return comparison


def build_raw_summary(
    agent_name, total_calls, global_score, avg_scores,
    strengths, improvements, top_objections, recommendations,
    call_breakdown, week_start, week_end,
) -> str:
    lines = [
        f"=== Rapport Hebdomadaire Coaching — {agent_name.title()} ===",
        f"Semaine du {week_start.strftime('%Y-%m-%d')} au {week_end.strftime('%Y-%m-%d')}",
        f"Appels analysés : {total_calls}",
        f"Score global : {global_score}/10",
        "",
        "--- Scores par dimension ---",
    ]
    for dim in DIMENSIONS:
        lines.append(f"  {dim}: {avg_scores[dim]}/10")

    lines.append("")
    lines.append(f"Forces : {', '.join(strengths)}")
    lines.append(f"À améliorer : {', '.join(improvements)}")

    if call_breakdown:
        lines.append("")
        lines.append("--- Répartition (Domingos) ---")
        for k, v in call_breakdown.items():
            lines.append(f"  {k}: {v}")

    if top_objections:
        lines.append("")
        lines.append("--- Objections fréquentes ---")
        for obj in top_objections[:5]:
            lines.append(f"  \"{obj['text']}\" — {obj['count']} fois")

    if recommendations:
        lines.append("")
        lines.append("--- Recommandations ---")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def push_to_supabase(report: dict) -> bool:
    """Upsert report to coaching_reports table."""
    try:
        resp = supabase_upsert("coaching_reports", report)
        if resp.status_code in (200, 201):
            log.info("Supabase upsert OK for %s", report["person_id"])
            return True
        else:
            log.error("Supabase upsert failed: %s %s", resp.status_code, resp.text)
            return False
    except Exception as exc:
        log.error("Supabase upsert error: %s", exc)
        return False


def log_cron(person_id: str, status: str, calls_processed: int, started_at: str, duration_sec: float, error_msg: str = ""):
    """Log execution to cron_logs table."""
    entry = {
        "person_id": person_id,
        "cron_type": "weekly_report",
        "status": status,
        "calls_processed": calls_processed,
        "transcripts_new": 0,
        "duration_sec": round(duration_sec),
        "error_msg": error_msg or None,
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        resp = supabase_insert("cron_logs", entry)
        if resp.status_code not in (200, 201):
            log.warning("cron_logs insert failed: %s %s", resp.status_code, resp.text)
    except Exception as exc:
        log.warning("cron_logs error: %s", exc)


def save_local_report(report: dict, agent_name: str):
    """Save a JSON backup of the report locally."""
    os.makedirs(LOCAL_REPORT_DIR, exist_ok=True)
    filename = f"{agent_name}_weekly_{report['week_start']}_to_{report['week_end']}.json"
    filepath = os.path.join(LOCAL_REPORT_DIR, filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log.info("Local report saved: %s", filepath)
    except OSError as exc:
        log.error("Failed to save local report: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run():
    log.info("=== nitro_weekly_report starting ===")
    week_start, week_end = get_week_range()
    log.info("Week range: %s to %s", week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d"))

    for agent_name, config in AGENTS.items():
        t0 = time.time()
        agent_started_at = datetime.now(timezone.utc).isoformat()
        log.info("Processing agent: %s", agent_name)

        transcripts = load_transcripts(config["transcript_dir"], week_start, week_end)

        if not transcripts:
            log.info("No transcripts for %s this week — skipping.", agent_name)
            log_cron(config["person_id"], "success", 0, agent_started_at, time.time() - t0)
            continue

        report = compute_weekly_summary(
            transcripts,
            agent_name,
            config["person_id"],
            config["report_type"],
            week_start,
            week_end,
        )

        if not report:
            log.warning("Empty report for %s — skipping.", agent_name)
            log_cron(config["person_id"], "error", 0, agent_started_at, time.time() - t0, error_msg="empty report")
            continue

        # Push to Supabase
        success = push_to_supabase(report)
        status = "success" if success else "error"

        # Save local backup
        save_local_report(report, agent_name)

        elapsed = time.time() - t0
        err = "" if success else "supabase push failed"
        log_cron(config["person_id"], status, len(transcripts), agent_started_at, elapsed, error_msg=err)
        log.info("Done with %s: %d calls, %.1fs", agent_name, len(transcripts), elapsed)

    log.info("=== nitro_weekly_report complete ===")


if __name__ == "__main__":
    run()
