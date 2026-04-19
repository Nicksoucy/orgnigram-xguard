#!/usr/bin/env python3
"""
SAC Weekly Report v2 — Production cron, runs Monday at 07:00 on Nitro.

Analyzes all transcripts from last 7 days, scores 10 SAC dimensions,
compares vs previous week, extracts coaching examples,
generates 3 DOCX reports, pushes to Supabase.

No GPU needed — reads existing JSON transcripts only.
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# Add crons dir to path for sac_scoring import
sys.path.insert(0, str(Path(__file__).parent))
from sac_scoring import (
    score_call, global_score as calc_global, classify_call as classify_scored,
    detect_agent_from_transcript, detect_objections_normalized,
    SAC_DIMENSIONS, DIM_LABELS, COACHING_RESPONSES, OBJECTION_CATEGORIES,
    DIMENSION_RECOMMENDATIONS, generate_recommendations,
)

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

PERSON_IDS = {"hamza": "L3", "lilia": "s2", "sekou": "s3"}
TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts")
REPORT_DIR = Path(r"C:\Users\user\sac_reports")
ARCHIVE_DIR = Path(r"C:\Users\user\sac_archive")
LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOCK_FILE = Path(r"C:\Users\user\sac_weekly.lock")
DOCX_SCRIPT = Path(r"C:\Users\user\sac_analysis\generate_reports_docx.js")
DOCX_DATA_DIR = Path(r"C:\Users\user\sac_analysis")

SAC_DIMENSIONS = [
    "accueil", "ecoute", "resolution", "patience", "professionnalisme",
    "vente_subtile", "qualification", "gestion_objections", "energie", "engagement",
]

RUN_ID = str(uuid.uuid4())[:8]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR.mkdir(parents=True, exist_ok=True)
today_str = datetime.now().strftime("%Y-%m-%d")
log = logging.getLogger("sac_weekly_v2")
log.setLevel(logging.INFO)
_fmt = logging.Formatter(f"%(asctime)s [{RUN_ID}] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_console = logging.StreamHandler(); _console.setFormatter(_fmt); log.addHandler(_console)
_fh = logging.FileHandler(str(LOG_DIR / f"weekly_{today_str}.log"), encoding="utf-8")
_fh.setFormatter(_fmt); log.addHandler(_fh)

# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------

def acquire_lock():
    if LOCK_FILE.exists():
        lock_time = datetime.fromtimestamp(LOCK_FILE.stat().st_mtime)
        age = (datetime.now() - lock_time).total_seconds() / 3600
        if age > 2:
            LOCK_FILE.unlink()
        else:
            log.error("Lock exists (%.1fh old) — exiting", age); sys.exit(1)
    LOCK_FILE.write_text(f"{RUN_ID} {datetime.now().isoformat()}", encoding="utf-8")

def release_lock():
    LOCK_FILE.unlink(missing_ok=True)

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def supabase_upsert(table, data, on_conflict=""):
    oc = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{oc}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            log.error("Supabase %s failed (%d): %s", table, resp.status_code, resp.text[:200])
        else:
            log.info("Supabase %s push OK", table)
        return resp
    except Exception as e:
        log.error("Supabase %s error: %s", table, e)

def supabase_insert(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "return=minimal"}
    try:
        return requests.post(url, json=data, headers=headers, timeout=30)
    except Exception as e:
        log.error("Supabase insert %s error: %s", table, e)

def supabase_get(table, params):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        return requests.get(url, params=params, headers=headers, timeout=30)
    except Exception as e:
        log.error("Supabase get %s error: %s", table, e)

# ---------------------------------------------------------------------------
# First-name detection
# ---------------------------------------------------------------------------

AGENT_NAMES = {
    "lilia": re.compile(r"\b(lilia|lilya|lilea)\b", re.IGNORECASE),
    "hamza": re.compile(r"\b(hamza|hamzah)\b", re.IGNORECASE),
    "sekou": re.compile(r"\b(sekou|sékou|secou)\b", re.IGNORECASE),
}

def detect_agent(text):
    intro = " ".join(text.split()[:150]).lower()
    for agent, pat in AGENT_NAMES.items():
        if pat.search(intro):
            return agent
    return None

# ---------------------------------------------------------------------------
# Load & reassign transcripts
# ---------------------------------------------------------------------------

def get_week_range():
    """Last 7 days: previous Monday to Sunday."""
    today = datetime.now()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return last_monday.replace(hour=0, minute=0, second=0, microsecond=0), last_sunday

def load_and_reassign_transcripts(week_start, week_end):
    buckets = {"hamza": [], "lilia": [], "sekou": []}
    total = 0; reassigned = 0

    for person in ["hamza", "lilia", "sekou"]:
        tdir = TRANSCRIPT_BASE / person
        if not tdir.exists(): continue
        for fp in tdir.glob("*.json"):
            if fp.name.endswith(".tmp"): continue
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    t = json.load(f)
            except Exception:
                continue

            # Parse call_time
            ct_str = t.get("call_time", "")
            ct = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S%z"):
                try:
                    ct = datetime.strptime(ct_str, fmt)
                    if ct.tzinfo: ct = ct.replace(tzinfo=None)
                    break
                except ValueError:
                    continue
            if ct is None: continue
            if not (week_start <= ct <= week_end): continue

            total += 1
            detected = detect_agent(t.get("transcript", ""))
            notes = (t.get("notes", "") or "").lower()
            original = person

            if detected:
                assigned = detected
            elif "lilia" in notes: assigned = "lilia"
            elif "hamza" in notes: assigned = "hamza"
            elif "sekou" in notes or notes.strip() == "sk": assigned = "sekou"
            else: assigned = original

            if assigned != original: reassigned += 1
            t["_assigned_to"] = assigned
            t["_source_file"] = str(fp)
            buckets[assigned].append(t)

    log.info("Loaded %d transcripts in range, reassigned %d", total, reassigned)
    return buckets

# ---------------------------------------------------------------------------
# Scoring engine (10 SAC dimensions) — imported from rescore_sac.py
# ---------------------------------------------------------------------------

def _count(text, patterns):
    c = 0
    for p in patterns: c += len(re.findall(p, text, re.IGNORECASE))
    return c

def _norm(raw, high=10):
    return round(min(10.0, max(0, (raw / high) * 10)), 1)

def score_accueil(text):
    words = text.split()
    intro = " ".join(words[:150]) if len(words) > 150 else text
    s = 0.0
    if re.search(r"\b(bonjour|bonsoir|allo)\b", intro, re.IGNORECASE): s += 2.0
    if re.search(r"\b(xguard|x[\s-]?guard|académie|academiexguard)\b", intro, re.IGNORECASE): s += 2.5
    if re.search(r"\b(je m'appelle|mon nom est|c'est|ici)\b", intro, re.IGNORECASE): s += 2.0
    if re.search(r"\b(comment puis-je vous aider|en quoi puis-je|que puis-je faire)\b", intro, re.IGNORECASE): s += 2.0
    if re.search(r"\bcomment (allez|ça va|vas)\b", intro, re.IGNORECASE): s += 1.5
    return round(min(10.0, s), 1)

def score_ecoute(text):
    pats = [r"\bje comprends\b", r"\bje vous comprends\b", r"\bje vois\b", r"\bd'accord\b",
            r"\btout à fait\b", r"\bexactement\b", r"\bbien sûr\b", r"\babsolument\b",
            r"\bsi je comprends bien\b", r"\bdonc vous\b", r"\bce que vous dites\b",
            r"\bvous me dites que\b", r"\bsi je résume\b"]
    return _norm(_count(text, pats), high=8)

def score_resolution(text):
    sol = [r"\bvoici ce (qu'on|que je)\b", r"\bje vais vous\b", r"\bje vous envoie\b",
           r"\bje vous transfère\b", r"\bla réponse\b", r"\bvous pouvez\b",
           r"\bje vous explique\b", r"\bje vais vérifier\b", r"\bc'est (fait|noté|envoyé|confirmé)\b",
           r"\bj'ai (noté|pris en note|vérifié|confirmé)\b"]
    conf = [r"\best-ce que.*clair\b", r"\bavez-vous d'autres questions\b",
            r"\best-ce que ça.*aide\b", r"\by a-t-il.*autre\b"]
    return _norm(_count(text, sol) * 1.2 + _count(text, conf) * 2.0, high=10)

def score_patience(dur):
    m = dur / 60
    if m < 0.5: return 1.0
    if m < 1: return 3.0
    if m < 2: return 5.0
    if m < 4: return 7.0
    if m < 8: return 9.0
    if m <= 15: return 10.0
    if m <= 25: return 9.5
    return 9.0

def score_professionnalisme(text):
    pro = [r"\bmerci\b", r"\bs'il vous plaît\b", r"\bje vous en prie\b", r"\bavec plaisir\b",
           r"\bbonne journée\b", r"\bbonne soirée\b", r"\bn'hésitez pas\b", r"\bà votre disposition\b"]
    neg = [r"\b(euh|tsé|genre|là là|faque)\b", r"\b(ça marche pas|j'sais pas|aucune idée)\b"]
    return _norm(max(0, _count(text, pro) * 1.5 - _count(text, neg)), high=8)

def score_vente_subtile(text):
    soft = [r"\bsi (ça|cela) vous intéresse\b", r"\bje (peux|pourrais) vous inscrire\b",
            r"\bvoulez-vous (que je|qu'on)\b", r"\bla prochaine (session|formation|date)\b",
            r"\bil (reste|y a) (encore|des) place\b", r"\bsi vous voulez réserver\b"]
    val = [r"\bl'avantage\b", r"\bce qui est bien\b", r"\bça (permet|va vous)\b",
           r"\b(certification|certifié|accrédité|reconnu)\b", r"\b(emploi|employeur|carrière)\b"]
    nxt = [r"\bje vous envoie (le lien|les infos|un courriel)\b", r"\bje vous rappelle\b",
           r"\bon se (reparle|rappelle)\b", r"\bquand (seriez|êtes)-vous disponible\b"]
    return _norm(_count(text, soft) * 2 + _count(text, val) * 1.5 + _count(text, nxt) * 2, high=10)

def score_qualification(text):
    qpats = [r"\bqu['']est-ce (que|qui)\b.*\?", r"\bpourquoi\b.*\?", r"\bcomment\b.*\?",
             r"\bquand\b.*\?", r"\bcombien\b.*\?", r"\bquel(le)?s?\b.*\?",
             r"\best-ce que\b.*\?", r"\bavez[- ]vous\b.*\?"]
    tops = [r"\b(besoin|objectif|motivation)\b", r"\b(expérience|parcours)\b",
            r"\b(disponibilité|horaire|quand|date)\b", r"\b(situation|emploi|travail)\b"]
    return round(min(10.0, min(6, _count(text, qpats)) + min(4, _count(text, tops) * 0.8)), 1)

def score_gestion_objections(text):
    obj = [r"c'est trop cher", r"pas le budget", r"je vais réfléchir", r"pas le temps",
           r"pas intéressé", r"pas le bon moment", r"mécontent", r"insatisfait", r"plainte"]
    hand = [r"\bje comprends\b", r"\bjustement\b", r"\ben fait\b", r"\bc'est normal\b",
            r"\bbonne question\b", r"\btout à fait\b", r"\bje vais (vérifier|m'occuper)\b",
            r"\bon va (trouver|régler)\b", r"\bsolution\b", r"\balternative\b"]
    o = _count(text, obj); h = _count(text, hand)
    if o == 0: return 7.0
    r = h / max(o, 1)
    if r >= 2: return 10.0
    if r >= 1: return 8.0
    if r >= 0.5: return 6.0
    if r > 0: return 4.0
    return 2.0

def score_energie(text):
    pos = [r"\bexcellent\b", r"\bparfait\b", r"\bsuper\b", r"\bgénial\b",
           r"\bfantastique\b", r"\bbravo\b", r"\bbienvenue\b", r"\bfélicitations\b"]
    enc = [r"\bvous (allez|êtes) (voir|sur|capable)\b", r"\bc'est (une|la) bonne\b", r"\bbon choix\b"]
    ex = min(text.count("!"), 15)
    return _norm(_count(text, pos) * 1.5 + _count(text, enc) * 2 + ex * 0.3, high=10)

def score_engagement(text):
    sents = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 5]
    q = text.count("?"); wc = len(text.split())
    qd = (q / max(wc, 1)) * 100
    return round(min(10.0, min(5, len(sents) * 0.1) + min(5, qd * 1.5)), 1)

def score_transcript(text, dur):
    return {d: f(text) if d != "patience" else score_patience(dur)
            for d, f in [("accueil", score_accueil), ("ecoute", score_ecoute),
                         ("resolution", score_resolution), ("patience", lambda t: None),
                         ("professionnalisme", score_professionnalisme), ("vente_subtile", score_vente_subtile),
                         ("qualification", score_qualification), ("gestion_objections", score_gestion_objections),
                         ("energie", score_energie), ("engagement", score_engagement)]}

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

SAC_PLAINTE = re.compile(r"\b(plainte|mécontent|insatisfait|rembours|annuler|annulation|déçu|inacceptable)\b", re.I)
SAC_INSCRIPTION = re.compile(r"\b(inscrire|inscription|formation|cours|session|programme|date|place|disponible|gardiennage|sécurité)\b", re.I)
SAC_SUPPORT = re.compile(r"\b(problème|aide|fonctionne pas|ne marche pas|erreur|bug|technique|accès|mot de passe|connexion)\b", re.I)
SAC_INFO = re.compile(r"\b(information|renseignement|question|comment|combien|prix|tarif|horaire|adresse)\b", re.I)

def classify(text):
    if SAC_PLAINTE.search(text): return "plainte"
    if SAC_INSCRIPTION.search(text): return "inscription"
    if SAC_SUPPORT.search(text): return "support"
    if SAC_INFO.search(text): return "info"
    return "autre"

# ---------------------------------------------------------------------------
# Coaching examples
# ---------------------------------------------------------------------------

def extract_examples(scored_data):
    examples = {}
    for dim in SAC_DIMENSIONS:
        by_dim = sorted(scored_data, key=lambda x: x["_scores"].get(dim, 0))
        worst = by_dim[:3]
        best = by_dim[-3:][::-1]
        de = {"best": [], "worst": []}
        for item in best:
            text = item.get("transcript", "")
            words = text.split()
            if dim == "accueil":
                excerpt = " ".join(words[:80])
            elif dim in ("resolution", "vente_subtile"):
                excerpt = " ".join(words[-100:]) if len(words) > 100 else text
            else:
                excerpt = " ".join(words[:100])
            de["best"].append({"score": item["_scores"][dim], "contact": item.get("contact_name", ""),
                               "duration": item.get("duration_s", 0), "date": item.get("call_time", ""),
                               "excerpt": excerpt + ("..." if len(words) > 100 else ""), "call_id": item.get("id", "")})
        for item in worst:
            text = item.get("transcript", "")
            words = text.split()
            excerpt = " ".join(words[:80]) if dim == "accueil" else " ".join(words[:100])
            de["worst"].append({"score": item["_scores"][dim], "contact": item.get("contact_name", ""),
                                "duration": item.get("duration_s", 0), "date": item.get("call_time", ""),
                                "excerpt": excerpt + ("..." if len(words) > 100 else ""), "call_id": item.get("id", "")})
        examples[dim] = de
    return examples

# ---------------------------------------------------------------------------
# Objections
# ---------------------------------------------------------------------------

def detect_objections(transcripts):
    pats = [
        (r"c'est trop cher|pas le budget|pas les moyens", "Prix/Budget"),
        (r"je vais réfléchir|pas encore décidé", "Reflexion"),
        (r"pas le temps|pas disponible", "Temps/Disponibilite"),
        (r"pas intéressé|ça ne m'intéresse", "Pas interesse"),
        (r"rappeler plus tard|un autre moment", "Reporter"),
        (r"déjà.*formation|déjà.*carte", "Deja fait"),
        (r"mécontent|insatisfait|plainte", "Plainte/Mecontentement"),
    ]
    counts = {}
    for t in transcripts:
        text = t.get("transcript", "")
        for pattern, label in pats:
            if re.search(pattern, text, re.I):
                counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items(), key=lambda x: -x[1])[:7]

# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

DIM_LABELS = {
    "accueil": "Accueil", "ecoute": "Ecoute active", "resolution": "Resolution",
    "patience": "Patience", "professionnalisme": "Professionnalisme",
    "vente_subtile": "Vente subtile", "qualification": "Qualification",
    "gestion_objections": "Gestion des objections", "energie": "Energie positive",
    "engagement": "Engagement",
}

def generate_recommendations(avg_scores):
    recs = []
    if avg_scores.get("accueil", 10) < 6:
        recs.append("Standardiser l'accueil: 'Bonjour, [prenom] de l'Academie XGuard, comment puis-je vous aider?'")
    if avg_scores.get("ecoute", 10) < 5:
        recs.append("Pratiquer la reformulation: 'Si je comprends bien, vous cherchez...' avant de repondre")
    if avg_scores.get("resolution", 10) < 5:
        recs.append("Toujours confirmer la resolution: 'Est-ce que ca repond a votre question?' avant de raccrocher")
    if avg_scores.get("vente_subtile", 10) < 4:
        recs.append("Quand un prospect demande des infos, mentionner les prochaines dates disponibles et proposer l'inscription")
    if avg_scores.get("professionnalisme", 10) < 5:
        recs.append("Terminer chaque appel par 'Merci d'avoir appele, bonne journee!' et 'N'hesitez pas a nous rappeler'")
    if avg_scores.get("qualification", 10) < 5:
        recs.append("Avant de repondre, poser 2-3 questions: situation actuelle, besoin specifique, disponibilite")
    if avg_scores.get("energie", 10) < 4:
        recs.append("Utiliser des mots positifs naturels: 'Excellent choix!', 'C'est parfait!', 'Bienvenue!'")
    if avg_scores.get("engagement", 10) < 5:
        recs.append("Poser des questions ouvertes: 'Qu'est-ce qui vous a interesse dans cette formation?'")
    return recs

# ---------------------------------------------------------------------------
# Previous week comparison
# ---------------------------------------------------------------------------

def fetch_comparison(person_id, current_scores, current_global, week_start):
    prev_start = (week_start - timedelta(days=7)).strftime("%Y-%m-%d")
    comparison = {d: 0.0 for d in SAC_DIMENSIONS}
    comparison["global"] = 0.0
    try:
        resp = supabase_get("coaching_reports", {
            "person_id": f"eq.{person_id}", "week_start": f"eq.{prev_start}",
            "select": "scores"})
        if resp and resp.status_code == 200:
            rows = resp.json()
            if rows:
                prev = rows[0].get("scores", {})
                for d in SAC_DIMENSIONS:
                    comparison[d] = round(current_scores.get(d, 0) - prev.get(d, 0), 1)
                prev_global = sum(prev.get(d, 0) for d in SAC_DIMENSIONS) / len(SAC_DIMENSIONS)
                comparison["global"] = round(current_global - prev_global, 1)
                log.info("  Comparison loaded (prev week: %s)", prev_start)
            else:
                log.info("  No previous week report found — deltas = 0")
    except Exception as e:
        log.warning("  Failed to fetch comparison: %s", e)
    return comparison

# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(person, transcripts, week_start, week_end):
    person_id = PERSON_IDS[person]

    if not transcripts:
        log.info("  %s: no transcripts — generating placeholder", person)
        return {
            "person_id": person_id, "person_name": person.capitalize(),
            "week_start": week_start.strftime("%Y-%m-%d"),
            "report_type": "sac", "calls_analyzed": 0,
            "scores": {d: 0.0 for d in SAC_DIMENSIONS}, "global_score": 0.0,
            "strengths": [], "improvements": [], "recommendations": [],
            "top_objections": [], "call_breakdown": {}, "duration_stats": {},
            "coaching_examples": {}, "comparison": {},
            "raw_summary": "Aucune transcription disponible cette semaine.",
        }

    # Score all
    scored = []
    breakdown = defaultdict(int)
    durations = []
    for t in transcripts:
        text = t.get("transcript", "") or ""
        dur = t.get("duration_s", 0) or 0
        sc = score_call(text, dur)
        t["_scores"] = sc
        scored.append(t)
        breakdown[classify_scored(text)] += 1
        durations.append(dur)

    # Averages
    avg = {}
    for d in SAC_DIMENSIONS:
        vals = [s["_scores"][d] for s in scored if s["_scores"].get(d) is not None]
        avg[d] = round(sum(vals) / len(vals), 1) if vals else 0.0
    gl = round(sum(avg.values()) / len(SAC_DIMENSIONS), 1)

    # Duration stats
    avg_dur = round(sum(durations) / len(durations)) if durations else 0
    sorted_dur = sorted(durations)
    median_dur = sorted_dur[len(sorted_dur) // 2] if sorted_dur else 0

    # Duration buckets
    buckets = {"<2min": 0, "2-5min": 0, "5-15min": 0, "15+min": 0}
    for d in durations:
        m = d / 60
        if m < 2: buckets["<2min"] += 1
        elif m < 5: buckets["2-5min"] += 1
        elif m < 15: buckets["5-15min"] += 1
        else: buckets["15+min"] += 1

    # Strengths / improvements
    sd = sorted(avg.items(), key=lambda x: -x[1])
    strengths = [f"{DIM_LABELS.get(d, d)}: {s}/10" for d, s in sd[:3] if s >= 4.0]
    improvements = [f"{DIM_LABELS.get(d, d)}: {s}/10" for d, s in sd[-3:] if s < 7.0]

    # Comparison
    comparison = fetch_comparison(person_id, avg, gl, week_start)

    # Coaching examples
    examples = extract_examples(scored)

    report = {
        "person_id": person_id, "person_name": person.capitalize(),
        "week_start": week_start.strftime("%Y-%m-%d"),
        "report_type": "sac",
        "calls_analyzed": len(transcripts),
        "scores": avg, "global_score": gl,
        "strengths": strengths, "improvements": improvements,
        "recommendations": generate_recommendations(avg),
        "top_objections": [{"objection": o, "count": c} for o, c in detect_objections(transcripts)],
        "call_breakdown": dict(breakdown),
        "duration_stats": {
            "avg_sec": avg_dur, "avg_min": round(avg_dur / 60, 1),
            "median_sec": median_dur, "median_min": round(median_dur / 60, 1),
            "max_sec": max(durations) if durations else 0,
            "max_min": round(max(durations) / 60, 1) if durations else 0,
            "min_sec": min(durations) if durations else 0,
            "buckets": buckets,
        },
        "call_stats": {},
        "coaching_examples": examples,
        "comparison": comparison,
        "raw_summary": (
            f"{len(transcripts)} appels analyses. Score global SAC: {gl}/10. "
            f"Duree moyenne: {round(avg_dur/60, 1)} min. "
            f"Forces: {', '.join(strengths[:2])}. "
            f"A ameliorer: {', '.join(improvements[:2])}."
        ),
    }
    return report

# ---------------------------------------------------------------------------
# DOCX generation
# ---------------------------------------------------------------------------

def generate_docx_reports(week_start_str):
    """Call Node.js script to generate DOCX, or skip if Node not available."""
    # Check if Node.js is available
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            log.warning("Node.js not available — skipping DOCX generation")
            return False
    except Exception:
        log.warning("Node.js not found — skipping DOCX generation")
        return False

    if not DOCX_SCRIPT.exists():
        log.warning("DOCX script not found at %s — skipping", DOCX_SCRIPT)
        return False

    try:
        # Install docx module if needed
        docx_check = subprocess.run(["node", "-e", "require('docx')"],
                                     capture_output=True, text=True, timeout=10,
                                     cwd=str(DOCX_DATA_DIR))
        if docx_check.returncode != 0:
            log.info("Installing docx npm package...")
            subprocess.run(["npm", "install", "docx"], capture_output=True, timeout=60,
                          cwd=str(DOCX_DATA_DIR))

        result = subprocess.run(["node", str(DOCX_SCRIPT)],
                               capture_output=True, text=True, timeout=120,
                               cwd=str(DOCX_DATA_DIR))
        if result.returncode == 0:
            log.info("DOCX reports generated successfully")
            log.info(result.stdout)

            # Copy to report archive
            for person in ["hamza", "lilia", "sekou"]:
                name = person.capitalize()
                src = DOCX_DATA_DIR / f"Rapport_Coaching_{name}_SAC.docx"
                if src.exists():
                    dest_dir = REPORT_DIR / person
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / f"rapport_semaine_{week_start_str}.docx"
                    shutil.copy2(str(src), str(dest))
                    log.info("  Archived: %s", dest)
            return True
        else:
            log.error("DOCX generation failed: %s", result.stderr[:300])
            return False
    except Exception as e:
        log.error("DOCX generation error: %s", e)
        return False

# ---------------------------------------------------------------------------
# Archive old transcripts
# ---------------------------------------------------------------------------

def archive_old_transcripts(days=30):
    cutoff = datetime.now() - timedelta(days=days)
    archived = 0
    for person in ["hamza", "lilia", "sekou"]:
        tdir = TRANSCRIPT_BASE / person
        adir = ARCHIVE_DIR / person
        if not tdir.exists(): continue
        for fp in tdir.glob("*.json"):
            if fp.name.endswith(".tmp"): continue
            try:
                mtime = datetime.fromtimestamp(fp.stat().st_mtime)
                if mtime < cutoff:
                    adir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(fp), str(adir / fp.name))
                    archived += 1
            except Exception:
                pass
    if archived > 0:
        log.info("Archived %d transcripts older than %d days", archived, days)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()
    log.info("=" * 60)
    log.info("SAC Weekly Report v2 — %s", today_str)
    log.info("Run ID: %s", RUN_ID)
    log.info("=" * 60)

    acquire_lock()

    try:
        week_start, week_end = get_week_range()
        week_start_str = week_start.strftime("%Y-%m-%d")
        log.info("Analysis period: %s to %s", week_start.strftime("%Y-%m-%d"), week_end.strftime("%Y-%m-%d"))

        # Load transcripts
        buckets = load_and_reassign_transcripts(week_start, week_end)

        for person in ["hamza", "lilia", "sekou"]:
            log.info("")
            log.info("=" * 50)
            log.info("  %s — %d transcripts", person.upper(), len(buckets[person]))
            log.info("=" * 50)

            report = generate_report(person, buckets[person], week_start, week_end)

            # Save report JSON (for DOCX generation)
            json_path = DOCX_DATA_DIR / person / "report_v2.json"
            json_path.parent.mkdir(parents=True, exist_ok=True)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            log.info("  Report JSON saved: %s", json_path)

            # Print summary
            log.info("  Global: %.1f/10 | Calls: %d | Avg dur: %.1f min",
                     report["global_score"], report["calls_analyzed"],
                     report["duration_stats"].get("avg_min", 0))
            for d in SAC_DIMENSIONS:
                delta = report["comparison"].get(d, 0)
                arrow = "+" if delta > 0 else ""
                log.info("    %s: %.1f (%s%.1f)", d, report["scores"][d], arrow, delta)

            # Push to Supabase
            sb_data = {
                "person_id": report["person_id"],
                "week_start": report["week_start"],
                "week_end": week_end.strftime("%Y-%m-%d"),
                "report_type": "sac",
                "calls_analyzed": report["calls_analyzed"],
                "scores": report["scores"],
                "strengths": report["strengths"],
                "improvements": report["improvements"],
                "recommendations": report["recommendations"],
                "top_objections": report["top_objections"],
                "call_breakdown": report["call_breakdown"],
                "comparison": report["comparison"],
                "raw_summary": report["raw_summary"],
            }
            supabase_upsert("coaching_reports", sb_data, on_conflict="person_id,week_start")

            # Cron log
            supabase_insert("cron_logs", {
                "person_id": report["person_id"],
                "cron_type": "weekly_report",
                "status": "success" if report["calls_analyzed"] > 0 else "empty",
                "calls_processed": report["calls_analyzed"],
                "transcripts_new": 0,
                "duration_sec": round(time.time() - start_time),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })

            # --- NEW v3: Weekly metrics rollup ---
            if report["calls_analyzed"] > 0:
                supabase_upsert("sac_coaching_metrics", {
                    "person_id": report["person_id"],
                    "period_type": "week",
                    "period_start": week_start_str,
                    "period_end": week_end.strftime("%Y-%m-%d"),
                    "calls_analyzed": report["calls_analyzed"],
                    "avg_duration_s": report.get("duration_stats", {}).get("avg_sec", 0),
                    "scores": report["scores"],
                    "global_score": report["global_score"],
                    "score_trend": report.get("comparison", {}).get("global", 0),
                    "call_breakdown": report.get("call_breakdown", {}),
                    "top_objections": report.get("top_objections", []),
                }, on_conflict="person_id,period_type,period_start")
                log.info("  sac_coaching_metrics (week) pushed")

            # --- NEW v3: Coaching actions tracking ---
            recs = generate_recommendations(report["scores"])
            for rec in recs:
                dim = rec["dimension"]
                # Check if same dim action exists from previous week
                try:
                    prev_ws = (week_start - timedelta(days=7)).strftime("%Y-%m-%d")
                    resp = supabase_get("sac_coaching_actions", {
                        "person_id": f"eq.{report['person_id']}",
                        "dimension": f"eq.{dim}",
                        "week_start": f"eq.{prev_ws}",
                        "status": "eq.open",
                        "select": "id,pre_score",
                    })
                    if resp and resp.status_code == 200:
                        rows = resp.json()
                        if rows:
                            # Update previous action with post_score
                            old = rows[0]
                            impact = round(report["scores"].get(dim, 0) - (old.get("pre_score", 0) or 0), 1)
                            supabase_upsert("sac_coaching_actions", {
                                "id": old["id"],
                                "post_score": report["scores"].get(dim, 0),
                                "impact": impact,
                                "status": "completed" if impact > 0.5 else "open",
                            }, on_conflict="id")
                except Exception:
                    pass

                # Insert new action for this week
                supabase_upsert("sac_coaching_actions", {
                    "person_id": report["person_id"],
                    "week_start": week_start_str,
                    "dimension": dim,
                    "recommendation": rec["recommendation"],
                    "status": "open",
                    "pre_score": rec["current_score"],
                }, on_conflict="")
            log.info("  sac_coaching_actions: %d recommendations tracked", len(recs))

            # --- NEW v3: Normalized objection tracking ---
            for t in buckets[person]:
                text = t.get("transcript", "") or ""
                objections = detect_objections_normalized(text)
                for category, raw in objections:
                    supabase_upsert("sac_objections", {
                        "person_id": report["person_id"],
                        "week_start": week_start_str,
                        "category": category,
                        "raw_text": raw[:200] if raw else "",
                        "count": 1,
                        "example_call_id": str(t.get("id", "")),
                        "coaching_response": COACHING_RESPONSES.get(category, ""),
                    }, on_conflict="person_id,week_start,category")
            log.info("  sac_objections pushed")

            # --- NEW v3: Monthly rollup (if last week of month) ---
            next_monday = week_start + timedelta(days=7)
            if next_monday.month != week_start.month:
                # This week crosses a month boundary — compute monthly rollup
                month_start = week_start.replace(day=1)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                try:
                    resp = supabase_get("sac_coaching_metrics", {
                        "person_id": f"eq.{report['person_id']}",
                        "period_type": "eq.week",
                        "period_start": f"gte.{month_start.strftime('%Y-%m-%d')}",
                        "period_end": f"lte.{month_end.strftime('%Y-%m-%d')}",
                        "select": "scores,calls_analyzed,avg_duration_s",
                    })
                    if resp and resp.status_code == 200:
                        weeks = resp.json()
                        if weeks:
                            total_calls = sum(w.get("calls_analyzed", 0) for w in weeks)
                            month_scores = {}
                            for d in SAC_DIMENSIONS:
                                vals = [w["scores"].get(d, 0) for w in weeks if w.get("scores")]
                                month_scores[d] = round(sum(vals) / len(vals), 1) if vals else 0.0
                            mg = round(sum(month_scores.values()) / len(SAC_DIMENSIONS), 1)
                            supabase_upsert("sac_coaching_metrics", {
                                "person_id": report["person_id"],
                                "period_type": "month",
                                "period_start": month_start.strftime("%Y-%m-%d"),
                                "period_end": month_end.strftime("%Y-%m-%d"),
                                "calls_analyzed": total_calls,
                                "scores": month_scores,
                                "global_score": mg,
                                "score_trend": 0,
                            }, on_conflict="person_id,period_type,period_start")
                            log.info("  Monthly rollup pushed for %s", month_start.strftime("%Y-%m"))
                except Exception as e:
                    log.warning("  Monthly rollup failed: %s", e)

        # Generate DOCX reports
        log.info("")
        log.info("Generating DOCX reports...")
        generate_docx_reports(week_start_str)

        # Archive old transcripts
        archive_old_transcripts(days=30)

        elapsed = round(time.time() - start_time)
        log.info("")
        log.info("=" * 60)
        log.info("ALL DONE in %d seconds", elapsed)
        log.info("=" * 60)

    except Exception as e:
        log.exception("FATAL ERROR: %s", e)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
