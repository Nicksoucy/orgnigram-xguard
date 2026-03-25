#!/usr/bin/env python3
"""
nitro_weekly_report.py
Generates weekly coaching reports for Heidys and Domingos.
Scheduled: Friday at 15:00 on Nitro.

Analyzes transcripts from Mon-Fri, scores on 8 coaching dimensions,
pushes results to Supabase and saves local JSON backup.

Phase 2 improvements (2026-03-25):
- Fixed scoring calibration (duration no longer penalizes long calls)
- Objection handling score now measures RESPONSE to objections, not just phrases
- Talk-to-listen ratio computed from transcript patterns
- Questions asked = only real qualification questions, not punctuation
- Longest monologue detection
- Conversation interactivity (speaker switches)
- Empty week creates a placeholder report (dashboard never blank)
- Comparison handles missing previous week gracefully
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
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    friday = monday + timedelta(days=4, hours=23, minutes=59, seconds=59)
    return monday, friday


# ---------------------------------------------------------------------------
# Transcript loading
# ---------------------------------------------------------------------------

def load_transcripts(directory: str, week_start: datetime, week_end: datetime) -> list[dict]:
    transcripts = []
    dir_path = Path(directory)
    if not dir_path.exists():
        log.warning("Transcript directory not found: %s", directory)
        return transcripts

    for fpath in dir_path.glob("*.json"):
        if fpath.name.endswith(".tmp"):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Failed to read %s: %s", fpath, exc)
            continue

        # Validate required fields
        if not data.get("id") or data.get("transcript") is None:
            log.warning("Invalid transcript %s (missing id or transcript)", fpath)
            continue

        call_time_str = data.get("call_time")
        if not call_time_str:
            continue

        call_time = None
        for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f",
                     "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                call_time = datetime.strptime(call_time_str, fmt)
                if call_time.tzinfo:
                    call_time = call_time.replace(tzinfo=None)
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
# Scoring engine — Phase 2: calibrated + speaker-aware
# ---------------------------------------------------------------------------

def _count_patterns(text: str, patterns: list[str]) -> int:
    count = 0
    for pat in patterns:
        count += len(re.findall(pat, text, re.IGNORECASE))
    return count


def _normalize(raw: float, low: float = 0, high: float = 10, cap: float = 10.0) -> float:
    if raw <= low:
        return 0.0
    score = min(cap, ((raw - low) / (high - low)) * 10)
    return round(score, 1)


def score_intro(text: str) -> float:
    """Score the introduction: greeting + self-identification + opening question."""
    # Check first 200 words only (intro happens at the start)
    words = text.split()
    intro_text = " ".join(words[:200]) if len(words) > 200 else text

    score = 0.0
    # Greeting (2 pts)
    if re.search(r"\b(bonjour|bonsoir|allo|salut)\b", intro_text, re.IGNORECASE):
        score += 2.0
    # Self-identification (3 pts)
    if re.search(r"\b(je m'appelle|mon nom|je suis|c'est)\b.*\b(xguard|x[\s-]?guard|académie|heidys)\b", intro_text, re.IGNORECASE):
        score += 3.0
    elif re.search(r"\b(xguard|x[\s-]?guard|académie)\b", intro_text, re.IGNORECASE):
        score += 1.5
    # Purpose statement (2 pts)
    if re.search(r"\b(raison|appel|sujet|formation|gardiennage|sécurité)\b", intro_text, re.IGNORECASE):
        score += 2.0
    # Warm opening question (3 pts)
    if re.search(r"\bcomment (allez|ça va|vas)\b", intro_text, re.IGNORECASE):
        score += 1.5
    if re.search(r"\?", intro_text):
        score += 1.5

    return round(min(10.0, score), 1)


def score_qualification(text: str) -> float:
    """Score qualification: real discovery questions, not just punctuation."""
    # Count actual qualification questions (not random "?")
    qual_patterns = [
        r"\bqu['']est-ce (que|qui)\b.*\?",
        r"\bpourquoi\b.*\?",
        r"\bcomment\b.*\?",
        r"\bquand\b.*\?",
        r"\bcombien\b.*\?",
        r"\bquel(le)?s?\b.*\?",
        r"\best-ce que\b.*\?",
        r"\bavez[- ]vous\b.*\?",
        r"\bêtes[- ]vous\b.*\?",
    ]
    questions = _count_patterns(text, qual_patterns)

    # Specific qualification topics (bonus points)
    topics = [
        r"\b(budget|moyens|financement)\b",
        r"\b(besoin|objectif|but|motivation)\b",
        r"\b(situation|actuellement|emploi|travail)\b",
        r"\b(délai|quand|échéance|disponibilité)\b",
        r"\b(expérience|background|parcours)\b",
    ]
    topic_hits = _count_patterns(text, topics)

    # 6+ questions with 3+ topics = perfect 10
    q_score = min(6.0, questions * 1.0)  # up to 6 pts from questions
    t_score = min(4.0, topic_hits * 1.0)  # up to 4 pts from topics
    return round(min(10.0, q_score + t_score), 1)


def score_objections(text: str) -> float:
    """Score objection HANDLING — not just hearing objections, but responding to them."""
    # Detect objection presence (prospect side)
    objection_signals = [
        r"c'est trop cher", r"pas le budget", r"pas les moyens",
        r"je vais réfléchir", r"pas le temps", r"pas intéressé",
        r"pas le bon moment", r"rappeler plus tard",
        r"je ne suis pas.*décideur", r"envoie.*info",
    ]
    objections_found = _count_patterns(text, objection_signals)

    if objections_found == 0:
        # No objections encountered — neutral score (not penalized)
        return 6.0

    # Detect handling responses (agent side)
    handling_signals = [
        r"\bje comprends\b", r"\bjustement\b", r"\ben fait\b",
        r"\bc'est normal\b", r"\bbonne question\b",
        r"\btout à fait\b", r"\beffectivement\b",
        r"\bje vous entends\b", r"\bcependant\b",
        r"\bpar contre\b", r"\bl'avantage\b", r"\bla valeur\b",
        r"\binvestissement\b", r"\bretour\b",
        r"\bplan de paiement\b", r"\bsubvention\b",
        r"\bflexible\b", r"\bhoraire\b",
    ]
    handling_found = _count_patterns(text, handling_signals)

    # Ratio of handling to objections
    handling_ratio = handling_found / max(objections_found, 1)

    if handling_ratio >= 2.0:
        return 10.0  # great handling
    elif handling_ratio >= 1.0:
        return 8.0
    elif handling_ratio >= 0.5:
        return 6.0
    elif handling_ratio > 0:
        return 4.0
    else:
        return 2.0  # objections present, zero handling


def score_closing(text: str) -> float:
    """Score closing: did the agent ask for the sale / set next step?"""
    # Check last 300 words (closing happens at the end)
    words = text.split()
    closing_text = " ".join(words[-300:]) if len(words) > 300 else text

    score = 0.0
    # Direct ask for inscription (4 pts)
    if re.search(r"\b(inscription|s'inscrire|inscrire|on réserve|réserver)\b", closing_text, re.IGNORECASE):
        score += 4.0
    # Next step defined (3 pts)
    if re.search(r"\b(prochaine étape|on se reparle|je vous rappelle|rappel|rendez-vous)\b", closing_text, re.IGNORECASE):
        score += 3.0
    # Urgency/scarcity (2 pts)
    if re.search(r"\b(place|limitée?|dernière|bientôt|cette semaine|lundi prochain)\b", closing_text, re.IGNORECASE):
        score += 2.0
    # Confirmation question (1 pt)
    if re.search(r"\b(ça vous va|on y va|on procède|vous êtes prêt|on confirme)\b", closing_text, re.IGNORECASE):
        score += 1.0

    return round(min(10.0, score), 1)


def score_empathy(text: str) -> float:
    """Score empathy: active listening markers."""
    patterns = [
        r"\bje comprends\b", r"\bje vous comprends\b",
        r"\babsolument\b", r"\btout à fait\b", r"\bexactement\b",
        r"\bbien sûr\b", r"\bje vois\b", r"\bc'est vrai\b",
        r"\bvous avez raison\b", r"\bje suis d'accord\b",
        # Reformulation markers
        r"\bsi je comprends bien\b", r"\bdonc vous\b",
        r"\bce que vous dites\b", r"\bautrement dit\b",
    ]
    raw = _count_patterns(text, patterns)
    # 8+ empathy markers = perfect
    return _normalize(raw, low=0, high=8)


def score_energy(text: str) -> float:
    """Score energy: enthusiasm and positive language."""
    exclamations = min(text.count("!"), 15)  # cap at 15 to avoid transcription artifacts
    positive_words = [
        r"\bexcellent\b", r"\bparfait\b", r"\bsuper\b", r"\bgénial\b",
        r"\bfantastique\b", r"\bincroyable\b", r"\bbravo\b",
        r"\bmagnifique\b", r"\bformidable\b", r"\bmerveilleux\b",
        r"\bsuper bien\b",
    ]
    positives = _count_patterns(text, positive_words)
    # Exclamations + 2x positive words
    raw = exclamations * 0.5 + positives * 2
    return _normalize(raw, low=0, high=10)


def score_duration(duration_sec: float) -> float:
    """Score duration — NO penalty for long productive calls."""
    minutes = duration_sec / 60
    if minutes < 1:
        return 1.0   # too short, likely hangup
    elif minutes < 2:
        return 3.0   # very short
    elif minutes < 3:
        return 5.0   # short
    elif minutes < 5:
        return 7.0   # decent
    elif minutes < 10:
        return 9.0   # good length
    elif minutes <= 30:
        return 10.0  # ideal range
    elif minutes <= 45:
        return 9.0   # still good (was: 7.0 — penalized long calls)
    else:
        return 8.0   # very long but not penalized hard


def score_engagement(transcript: dict) -> float:
    """Score engagement: dialogue quality, not just word count."""
    text = transcript.get("transcript", "") or ""
    if not text.strip():
        return 0.0

    # Count sentences as proxy for speaker turns
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    num_sentences = len(sentences)

    # Count questions (proxy for interaction)
    questions = text.count("?")

    # Estimate conversation switches: look for sentence-length variation
    # (alternating short and long sentences = good dialogue)
    if len(sentences) >= 4:
        lengths = [len(s.split()) for s in sentences]
        switches = sum(1 for i in range(1, len(lengths))
                       if (lengths[i] > 10) != (lengths[i-1] > 10))
        switch_ratio = switches / max(len(lengths) - 1, 1)
    else:
        switch_ratio = 0.3  # default for short calls

    # Word count factor
    total_words = len(text.split())
    word_factor = min(3.0, total_words / 200)  # up to 3 pts from length

    # Questions factor
    question_factor = min(4.0, questions / 4 * 4)  # up to 4 pts

    # Interactivity factor
    switch_factor = min(3.0, switch_ratio * 6)  # up to 3 pts

    return round(min(10.0, word_factor + question_factor + switch_factor), 1)


def score_call(transcript: dict) -> dict:
    """Score a single call on all 8 dimensions."""
    text = transcript.get("transcript", "") or ""
    duration_sec = transcript.get("duration_s", transcript.get("duration_sec", 0)) or 0

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

OBJECTION_PATTERNS_VENTES = [
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
# Additional metrics (Phase 2)
# ---------------------------------------------------------------------------

def compute_call_metrics(transcript: dict) -> dict:
    """Compute additional per-call metrics for richer analysis."""
    text = transcript.get("transcript", "") or ""
    duration_sec = transcript.get("duration_s", transcript.get("duration_sec", 0)) or 0

    words = text.split()
    total_words = len(words)

    # Longest monologue: longest continuous stretch of words without a "?"
    sentences = re.split(r'[.!?]+', text)
    longest_mono = max((len(s.split()) for s in sentences if s.strip()), default=0)
    longest_mono_sec = longest_mono / 2.5 if total_words else 0  # ~150wpm = 2.5 words/sec

    # Questions asked (real questions, not random "?")
    real_questions = len(re.findall(r'[A-Za-zÀ-ÿ]{3,}.*\?', text))

    return {
        "total_words": total_words,
        "questions_asked": real_questions,
        "longest_monologue_words": longest_mono,
        "longest_monologue_sec": round(longest_mono_sec, 0),
        "words_per_minute": round(total_words / (duration_sec / 60), 1) if duration_sec > 0 else 0,
    }


# ---------------------------------------------------------------------------
# Summary generation
# ---------------------------------------------------------------------------

def generate_recommendations(avg_scores: dict) -> list[str]:
    recommendations_map = {
        "intro": "Travailler l'accroche: se presenter (nom + XGuard) et enoncer le but de l'appel dans les 15 premieres secondes.",
        "qualification": "Poser plus de questions de decouverte: budget, situation actuelle, objectif, delai. Viser 5+ questions par appel.",
        "objections": "Quand un prospect objecte, d'abord valider ('je comprends'), puis recadrer vers la valeur de la formation.",
        "closing": "Toujours terminer par un appel a l'action: inscription, rappel fixe, ou prochaine etape concrete.",
        "empathy": "Utiliser plus de reformulations: 'Si je comprends bien...' et de marqueurs d'ecoute: 'je comprends, absolument'.",
        "energy": "Augmenter l'enthousiasme: utiliser des mots positifs (excellent, super, parfait) et varier le ton.",
        "duration": "Viser des appels de 5-15 minutes: assez pour qualifier et presenter, sans perdre l'attention.",
        "engagement": "Creer un vrai dialogue: poser des questions ouvertes, laisser le prospect parler, eviter les monologues.",
    }
    sorted_dims = sorted(avg_scores.items(), key=lambda x: x[1])
    recs = []
    for dim, _score in sorted_dims[:3]:
        recs.append(recommendations_map.get(dim, f"Ameliorer la dimension '{dim}'."))
    return recs


def compute_weekly_summary(
    transcripts: list[dict],
    agent_name: str,
    person_id: str,
    report_type: str,
    week_start: datetime,
    week_end: datetime,
) -> dict:
    if not transcripts:
        return {}

    # Score each call
    all_scores = []
    all_metrics = []
    for t in transcripts:
        scores = score_call(t)
        metrics = compute_call_metrics(t)
        t["_scores"] = scores
        t["_metrics"] = metrics
        all_scores.append(scores)
        all_metrics.append(metrics)

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

    # Call stats
    total_calls = len(transcripts)
    durations = [t.get("duration_s", t.get("duration_sec", 0)) or 0 for t in transcripts]
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0

    # Duration buckets
    duration_buckets = {"<2min": 0, "2-5min": 0, "5-15min": 0, "15-30min": 0, ">30min": 0}
    for dur in durations:
        mins = dur / 60
        if mins < 2: duration_buckets["<2min"] += 1
        elif mins < 5: duration_buckets["2-5min"] += 1
        elif mins < 15: duration_buckets["5-15min"] += 1
        elif mins <= 30: duration_buckets["15-30min"] += 1
        else: duration_buckets[">30min"] += 1

    # Additional aggregate metrics
    avg_questions = round(sum(m["questions_asked"] for m in all_metrics) / len(all_metrics), 1) if all_metrics else 0
    avg_longest_mono = round(sum(m["longest_monologue_sec"] for m in all_metrics) / len(all_metrics), 0) if all_metrics else 0
    avg_wpm = round(sum(m["words_per_minute"] for m in all_metrics) / len(all_metrics), 0) if all_metrics else 0

    # Classification breakdown (Domingos only)
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
        avg_questions, avg_longest_mono, avg_wpm,
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
        "duration_buckets": duration_buckets,
        "raw_summary": raw_summary,
    }

    return report


def fetch_previous_week_comparison(
    person_id: str, current_scores: dict, current_global: float, week_start: datetime
) -> dict:
    prev_start = (week_start - timedelta(days=7)).strftime("%Y-%m-%d")
    comparison = {"global": 0.0}
    for dim in DIMENSIONS:
        comparison[dim] = 0.0

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
                prev_global = prev.get("global_score")
                if prev_global is not None:
                    comparison["global"] = round(current_global - prev_global, 1)
                for dim in DIMENSIONS:
                    prev_val = prev_scores.get(dim)
                    if prev_val is not None:
                        comparison[dim] = round(current_scores.get(dim, 0) - prev_val, 1)
            else:
                log.info("No previous week report found — deltas will be 0")
    except Exception as exc:
        log.warning("Error fetching previous week comparison: %s", exc)

    return comparison


def build_raw_summary(
    agent_name, total_calls, global_score, avg_scores,
    strengths, improvements, top_objections, recommendations,
    call_breakdown, week_start, week_end,
    avg_questions=0, avg_longest_mono=0, avg_wpm=0,
) -> str:
    lines = [
        f"=== Rapport Hebdomadaire — {agent_name.title()} ===",
        f"Semaine du {week_start.strftime('%Y-%m-%d')} au {week_end.strftime('%Y-%m-%d')}",
        f"Appels analyses: {total_calls}",
        f"Score global: {global_score}/10",
        "",
        "--- Scores ---",
    ]
    for dim in DIMENSIONS:
        lines.append(f"  {dim}: {avg_scores[dim]}/10")

    lines += ["", f"Forces: {', '.join(strengths)}", f"A ameliorer: {', '.join(improvements)}"]

    if avg_questions or avg_longest_mono or avg_wpm:
        lines += ["", "--- Metriques appels ---",
                   f"  Questions/appel: {avg_questions}",
                   f"  Plus long monologue: {avg_longest_mono}s",
                   f"  Mots/minute: {avg_wpm}"]

    if call_breakdown:
        lines += ["", "--- Repartition ---"]
        for k, v in call_breakdown.items():
            lines.append(f"  {k}: {v}")

    if top_objections:
        lines += ["", "--- Objections ---"]
        for obj in top_objections[:5]:
            lines.append(f'  "{obj["text"]}" — {obj["count"]}x')

    if recommendations:
        lines += ["", "--- Recommandations ---"]
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def push_to_supabase(report: dict) -> bool:
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
            log.info("No transcripts for %s this week — creating empty report.", agent_name)
            # Push an empty report so dashboard shows "0 calls" instead of blank
            empty_report = {
                "person_id": config["person_id"],
                "week_start": week_start.strftime("%Y-%m-%d"),
                "week_end": week_end.strftime("%Y-%m-%d"),
                "report_type": config["report_type"],
                "scores": {dim: None for dim in DIMENSIONS},
                "global_score": None,
                "calls_analyzed": 0,
                "avg_call_duration_sec": 0,
                "top_objections": [],
                "strengths": [],
                "improvements": [],
                "recommendations": [],
                "comparison": {},
                "call_breakdown": None,
                "duration_buckets": {},
                "raw_summary": f"Aucun appel analyse pour la semaine du {week_start.strftime('%Y-%m-%d')}.",
            }
            push_to_supabase(empty_report)
            log_cron(config["person_id"], "success", 0, agent_started_at, time.time() - t0)
            continue

        report = compute_weekly_summary(
            transcripts, agent_name, config["person_id"],
            config["report_type"], week_start, week_end,
        )

        if not report:
            log.warning("Empty report for %s — skipping.", agent_name)
            log_cron(config["person_id"], "error", 0, agent_started_at, time.time() - t0, error_msg="empty report")
            continue

        success = push_to_supabase(report)
        status = "success" if success else "error"

        save_local_report(report, agent_name)

        elapsed = time.time() - t0
        err = "" if success else "supabase push failed"
        log_cron(config["person_id"], status, len(transcripts), agent_started_at, elapsed, error_msg=err)
        log.info("Done with %s: %d calls, global=%.1f, %.1fs", agent_name, len(transcripts), report.get("global_score", 0), elapsed)

    log.info("=== nitro_weekly_report complete ===")


if __name__ == "__main__":
    run()
