#!/usr/bin/env python3
"""
SAC Daily Sync v2 — Production cron, runs every day at 19:00 on Nitro.

Fetches calls from BOTH JustCall accounts (academie@ + formateur@),
attributes each call to the correct person (first-name detection + notes),
downloads recordings, transcribes with faster-whisper (GPU),
classifies calls, pushes daily stats to Supabase.

Replaces nitro_sac_daily.py — adds:
- Dual-account fetching (academie + formateur)
- First-name attribution from transcript
- 10 SAC-adapted dimensions (scoring done in weekly cron)
- Lock file to prevent double-run
- Retry with exponential backoff
- Per-day log files
"""

import json
import logging
import os
import re
import shutil
import sys
import tempfile
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# Add crons dir to path for sac_scoring import
sys.path.insert(0, str(Path(__file__).parent))
from sac_scoring import (
    score_call, global_score, classify_call as classify_call_scored,
    detect_agent_from_transcript, detect_objections_normalized, SAC_DIMENSIONS,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JUSTCALL_API_URL = "https://api.justcall.io/v1/calls/query"
JUSTCALL_API_KEY = "daf60d953694336f07c84c74205eb311dd85c996"
JUSTCALL_API_SECRET = "20612f8fcb80ef33845cbdc226bc8174853c82dd"

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

JUSTCALL_ACCOUNTS = {
    "academie": {"agent_id": "301418", "label": "academie@xguard.ca"},
    "formateur": {"agent_id": "302145", "label": "formateur@xguard.ca"},
}

PERSON_IDS = {"hamza": "L3", "lilia": "s2", "sekou": "s3"}
TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts")
LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOCK_FILE = Path(r"C:\Users\user\sac_daily.lock")

MIN_DURATION_SEC = 30
MAX_BATCH_SIZE = 500
MIN_DISK_FREE_MB = 500
MAX_CONSECUTIVE_FAILURES = 10
LOCK_STALE_HOURS = 4

WHISPER_MODEL = "medium"
WHISPER_LANGUAGE = "fr"
WHISPER_BEAM_SIZE = 3

RUN_ID = str(uuid.uuid4())[:8]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR.mkdir(parents=True, exist_ok=True)
today_str = datetime.now().strftime("%Y-%m-%d")
log_file = LOG_DIR / f"daily_{today_str}.log"

log = logging.getLogger("sac_daily_v2")
log.setLevel(logging.INFO)
_fmt = logging.Formatter(f"%(asctime)s [{RUN_ID}] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_console = logging.StreamHandler()
_console.setFormatter(_fmt)
log.addHandler(_console)
_file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
_file_handler.setFormatter(_fmt)
log.addHandler(_file_handler)

# ---------------------------------------------------------------------------
# Lock file
# ---------------------------------------------------------------------------

def acquire_lock():
    if LOCK_FILE.exists():
        try:
            lock_time = datetime.fromtimestamp(LOCK_FILE.stat().st_mtime)
            age_hours = (datetime.now() - lock_time).total_seconds() / 3600
            if age_hours > LOCK_STALE_HOURS:
                log.warning("Stale lock file (%.1f hours old) — removing", age_hours)
                LOCK_FILE.unlink()
            else:
                log.error("Lock file exists (%.1f hours old) — another instance running. Exiting.", age_hours)
                sys.exit(1)
        except Exception:
            LOCK_FILE.unlink(missing_ok=True)
    LOCK_FILE.write_text(f"{RUN_ID} {datetime.now().isoformat()}", encoding="utf-8")
    log.info("Lock acquired: %s", LOCK_FILE)

def release_lock():
    LOCK_FILE.unlink(missing_ok=True)
    log.info("Lock released")

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

SAC_PLAINTE_KW = re.compile(
    r"\b(plainte|mécontent|insatisfait|rembours|annuler|annulation|déçu|inacceptable|pire|problème grave)\b", re.IGNORECASE)
SAC_INSCRIPTION_KW = re.compile(
    r"\b(inscrire|inscription|formation|cours|session|programme|date|place|disponible|gardiennage|sécurité|bsp|secourisme)\b", re.IGNORECASE)
SAC_SUPPORT_KW = re.compile(
    r"\b(problème|aide|fonctionne pas|ne marche pas|erreur|bug|technique|accès|mot de passe|connexion|identifiant|compte)\b", re.IGNORECASE)
SAC_INFO_KW = re.compile(
    r"\b(information|renseignement|question|comment|combien|prix|tarif|horaire|adresse|coût|frais)\b", re.IGNORECASE)

def classify_call(text: str) -> str:
    if SAC_PLAINTE_KW.search(text): return "plainte"
    if SAC_INSCRIPTION_KW.search(text): return "inscription"
    if SAC_SUPPORT_KW.search(text): return "support"
    if SAC_INFO_KW.search(text): return "info"
    return "autre"

# ---------------------------------------------------------------------------
# First-name detection
# ---------------------------------------------------------------------------

AGENT_NAME_PATTERNS = {
    "lilia": re.compile(r"\b(lilia|lilya|lilea)\b", re.IGNORECASE),
    "hamza": re.compile(r"\b(hamza|hamzah)\b", re.IGNORECASE),
    "sekou": re.compile(r"\b(sekou|sékou|secou|sécou|sécoudé|secoudé|sékou de|secou de|sekou de)\b", re.IGNORECASE),
}

def detect_agent_from_transcript(text: str):
    words = text.split()
    intro = " ".join(words[:150]).lower()
    for agent, pattern in AGENT_NAME_PATTERNS.items():
        if pattern.search(intro):
            return agent
    return None

# ---------------------------------------------------------------------------
# Pre-transcription attribution (from notes + account + day)
# ---------------------------------------------------------------------------

def assign_person_pre(call: dict, account: str) -> str:
    notes = (call.get("notes", "") or "").lower().strip()
    if "lilia" in notes: return "lilia"
    if "hamza" in notes: return "hamza"
    if "sekou" in notes or notes.strip() == "sk": return "sekou"
    if account == "formateur": return "lilia"
    date_str = (call.get("time", "") or "").split(" ")[0]
    if date_str:
        try:
            dow = datetime.strptime(date_str, "%Y-%m-%d").weekday()
            if dow >= 5: return "sekou"
        except ValueError:
            pass
    return "hamza"

# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def supabase_upsert(table: str, data, on_conflict: str = ""):
    oc = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{oc}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            log.error("Supabase %s failed (%d): %s", table, resp.status_code, resp.text[:200])
        return resp
    except Exception as e:
        log.error("Supabase %s error: %s", table, e)
        return None

def supabase_upsert_patch(call_id: str, data: dict):
    """PATCH existing sac_calls row by call_id."""
    url = f"{SUPABASE_URL}/rest/v1/sac_calls?call_id=eq.{call_id}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    try:
        resp = requests.patch(url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            log.warning("Supabase PATCH sac_calls (%d): %s", resp.status_code, resp.text[:100])
    except Exception as e:
        log.warning("Supabase PATCH error: %s", e)

def supabase_insert(table: str, data: dict):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    try:
        return requests.post(url, json=data, headers=headers, timeout=30)
    except Exception as e:
        log.error("Supabase insert %s error: %s", table, e)
        return None

# ---------------------------------------------------------------------------
# JustCall API with retry
# ---------------------------------------------------------------------------

def fetch_justcall_page(agent_id: str, date_str: str, page: int) -> dict:
    headers = {"Accept": "application/json", "Authorization": f"{JUSTCALL_API_KEY}:{JUSTCALL_API_SECRET}"}
    body = {"from_date": date_str, "to_date": date_str, "agent_id": agent_id, "per_page": 100, "page": page}
    for attempt in range(3):
        try:
            log.info("    -> page %d attempt %d starting...", page, attempt + 1)
            resp = requests.post(JUSTCALL_API_URL, json=body, headers=headers, timeout=(10, 30))
            log.info("    -> page %d attempt %d got %d", page, attempt + 1, resp.status_code)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            log.warning("JustCall page %d attempt %d TIMEOUT — retrying in %ds", page, attempt + 1, 2 ** (attempt + 1))
            time.sleep(2 ** (attempt + 1))
        except Exception as e:
            wait = 2 ** (attempt + 1)
            log.warning("JustCall page %d attempt %d failed: %s — retrying in %ds", page, attempt + 1, e, wait)
            time.sleep(wait)
    raise RuntimeError(f"JustCall API failed after 3 retries (agent_id={agent_id}, page={page})")

def fetch_all_calls(agent_id: str, date_str: str) -> list:
    """Fetch all calls for a specific date. Stops when calls fall outside the target date."""
    all_calls = []
    page = 1
    while page <= 30:  # safety cap
        data = fetch_justcall_page(agent_id, date_str, page)
        calls = data.get("data", [])
        if not calls:
            break

        # Filter to only calls from the target date (API returns beyond)
        on_date = [c for c in calls if (c.get("time", "") or "").startswith(date_str)]
        all_calls.extend(on_date)

        # If we got calls from other dates, we've gone past our target — stop
        if len(on_date) < len(calls):
            log.info("  Page %d: %d on-date, %d other — stopping pagination", page, len(on_date), len(calls) - len(on_date))
            break
        if len(calls) < 100:
            break
        page += 1
        time.sleep(0.5)

    log.info("  Total calls for %s: %d", date_str, len(all_calls))
    return all_calls

def filter_calls(calls: list) -> list:
    return [c for c in calls
            if int(c.get("duration", 0) or 0) >= MIN_DURATION_SEC
            and (c.get("recording") or "").strip()]

# ---------------------------------------------------------------------------
# Disk check
# ---------------------------------------------------------------------------

def check_disk_space(path_str: str = "C:\\"):
    usage = shutil.disk_usage(path_str)
    free_mb = usage.free // (1024 * 1024)
    if free_mb < MIN_DISK_FREE_MB:
        raise RuntimeError(f"Low disk space: {free_mb}MB free (need {MIN_DISK_FREE_MB}MB)")
    log.info("Disk space OK: %dMB free", free_mb)

# ---------------------------------------------------------------------------
# Whisper
# ---------------------------------------------------------------------------

def load_whisper_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log.error("faster-whisper not installed")
        sys.exit(1)
    try:
        model = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="int8_float16")
        log.info("Whisper model loaded on CUDA")
    except Exception:
        log.warning("CUDA unavailable, falling back to CPU")
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    return model

# ---------------------------------------------------------------------------
# Download + Transcribe
# ---------------------------------------------------------------------------

def download_recording(url: str, out_path: Path) -> bool:
    for attempt in range(2):
        try:
            resp = requests.get(url, timeout=120, stream=True)
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except Exception as e:
            if attempt == 0:
                time.sleep(2)
            else:
                log.warning("Download failed after 2 attempts: %s", e)
    return False

def transcribe_file(model, audio_path: Path) -> tuple:
    segments, info = model.transcribe(
        str(audio_path), language=WHISPER_LANGUAGE,
        beam_size=WHISPER_BEAM_SIZE, vad_filter=True)
    text = " ".join(seg.text.strip() for seg in segments)
    lang = info.language if hasattr(info, "language") else "fr"
    return text, lang

# ---------------------------------------------------------------------------
# Process one person's calls
# ---------------------------------------------------------------------------

def process_person(person: str, calls: list, model) -> dict:
    person_id = PERSON_IDS[person]
    transcript_dir = TRANSCRIPT_BASE / person
    transcript_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "calls_total": len(calls), "calls_transcribed": 0, "calls_new": 0,
        "calls_skipped": 0, "calls_failed": 0, "errors": [],
        "durations": [], "categories": {},
    }

    if not calls:
        log.info("No qualifying calls for %s", person)
        return stats

    # Update nitro_status
    supabase_upsert("nitro_status", {
        "person_id": person_id, "task_type": "daily_sync",
        "status": "running", "done": 0, "total": len(calls),
        "pct": 0, "gpu_active": True, "last_file": "",
        "started_at": datetime.now(timezone.utc).isoformat(),
    }, on_conflict="person_id,task_type")

    consecutive_failures = 0
    reassigned = 0

    for i, call in enumerate(calls, 1):
        call_id = str(call.get("id", f"unknown_{i}"))
        json_path = transcript_dir / f"{call_id}.json"
        audio_path = transcript_dir / f"{call_id}.wav"

        # Skip existing transcript
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                cat = existing.get("category", "autre")
                stats["categories"][cat] = stats["categories"].get(cat, 0) + 1
                stats["durations"].append(existing.get("duration_s", 0))
                stats["calls_skipped"] += 1
                stats["calls_transcribed"] += 1
                consecutive_failures = 0
                continue
            except Exception:
                pass

        # Download
        rec_url = call.get("recording", "")
        if not audio_path.exists():
            if not download_recording(rec_url, audio_path):
                stats["calls_failed"] += 1
                stats["errors"].append(f"{call_id}: download failed")
                consecutive_failures += 1
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    log.error("10 consecutive failures — aborting %s", person)
                    break
                continue

        # Transcribe
        try:
            text, lang = transcribe_file(model, audio_path)
            category = classify_call(text)
            duration = int(call.get("duration", 0) or 0)

            # Post-transcription re-attribution
            detected = detect_agent_from_transcript(text)
            assigned_to = person
            if detected and detected != person:
                # Move to correct folder
                new_dir = TRANSCRIPT_BASE / detected
                new_dir.mkdir(parents=True, exist_ok=True)
                new_json_path = new_dir / f"{call_id}.json"
                assigned_to = detected
                reassigned += 1
                log.info("  Reassigned %s: %s -> %s (detected in transcript)", call_id, person, detected)
            else:
                new_json_path = json_path

            transcript_data = {
                "id": call_id,
                "contact_name": call.get("contact_name", ""),
                "contact_number": call.get("contact_number", ""),
                "call_time": call.get("time", ""),
                "duration_s": duration,
                "direction": "inbound" if call.get("direction") == "1" else "outbound",
                "recording_url": rec_url,
                "transcript": text,
                "word_count": len(text.split()),
                "language": lang,
                "category": category,
                "source": "justcall",
                "agent": assigned_to,
                "account": call.get("_account", ""),
                "notes": call.get("notes", ""),
                "transcribed_at": datetime.now(timezone.utc).isoformat(),
            }

            # Atomic write
            tmp_path = new_json_path.with_suffix(".json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)
            os.replace(str(tmp_path), str(new_json_path))

            stats["calls_new"] += 1
            stats["calls_transcribed"] += 1
            stats["durations"].append(duration)
            stats["categories"][category] = stats["categories"].get(category, 0) + 1
            consecutive_failures = 0

            log.info("  [%d/%d] Transcribed: %s (%d words, %s, -> %s)",
                     i, len(calls), call_id, len(text.split()), category, assigned_to)

            # Score and push to sac_calls
            try:
                assigned_pid = PERSON_IDS.get(assigned_to, person_id)
                scores = score_call(text, duration)
                gs = global_score(scores)
                contact_num = (call.get("contact_number", "") or "").strip()
                contact_name = (call.get("contact_name", "") or "").strip()

                supabase_upsert("sac_calls", {
                    "call_id": call_id,
                    "person_id": assigned_pid,
                    "call_time": call.get("time", ""),
                    "duration_s": duration,
                    "direction": "inbound" if call.get("direction") == "1" else "outbound",
                    "contact_name": contact_name,
                    "contact_number": contact_num,
                    "classification": category,
                    "language": lang,
                    "transcript": text,
                    "word_count": len(text.split()),
                    "scores": scores,
                    "global_score": gs,
                    "account": call.get("_account", ""),
                    "notes": call.get("notes", ""),
                    "detected_agent": detected,
                }, on_conflict="call_id")

                # Update sac_contacts
                if contact_num and len(contact_num) >= 7:
                    supabase_upsert("sac_contacts", {
                        "contact_number": contact_num,
                        "contact_name": contact_name or None,
                        "first_call_date": call.get("time", "")[:10],
                        "last_call_date": call.get("time", "")[:10],
                        "total_calls": 1,
                        "total_duration_s": duration,
                        "primary_agent": assigned_pid,
                        "primary_category": category,
                        "languages": [lang] if lang else [],
                    }, on_conflict="contact_number")
            except Exception as push_err:
                log.warning("  sac_calls/contacts push failed: %s", push_err)

            # Cleanup audio
            try:
                audio_path.unlink()
            except Exception:
                pass

        except Exception as exc:
            consecutive_failures += 1
            stats["calls_failed"] += 1
            if len(stats["errors"]) < 10:
                stats["errors"].append(f"{call_id}: {str(exc)[:100]}")
            log.error("  [%d/%d] Failed %s: %s", i, len(calls), call_id, exc)

            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                log.error("10 consecutive failures — aborting %s", person)
                break

        # Progress update every 10 calls
        if i % 10 == 0:
            pct = round(i / len(calls) * 100, 1)
            supabase_upsert("nitro_status", {
                "person_id": person_id, "task_type": "daily_sync",
                "status": "running", "done": i, "total": len(calls),
                "pct": pct, "gpu_active": True, "last_file": call_id,
            }, on_conflict="person_id,task_type")

    # Final nitro_status
    supabase_upsert("nitro_status", {
        "person_id": person_id, "task_type": "daily_sync",
        "status": "done", "done": stats["calls_transcribed"], "total": len(calls),
        "pct": 100, "gpu_active": False, "last_file": "",
    }, on_conflict="person_id,task_type")

    if reassigned > 0:
        log.info("  %s: %d calls reassigned by first-name detection", person, reassigned)

    return stats

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()
    date_str = datetime.now().strftime("%Y-%m-%d")

    log.info("=" * 60)
    log.info("SAC Daily Sync v2 — %s", date_str)
    log.info("Run ID: %s", RUN_ID)
    log.info("=" * 60)

    # Lock
    acquire_lock()

    try:
        # Disk check
        check_disk_space("C:\\")

        # Fetch from BOTH accounts
        all_calls_by_person = {"hamza": [], "lilia": [], "sekou": []}

        for acct_name, acct_config in JUSTCALL_ACCOUNTS.items():
            agent_id = acct_config["agent_id"]
            log.info("Fetching %s (agent_id=%s)...", acct_name, agent_id)
            log.info("  Starting API call at %s", datetime.now().strftime("%H:%M:%S"))
            try:
                raw_calls = fetch_all_calls(agent_id, date_str)
                log.info("  %s: %d raw calls", acct_name, len(raw_calls))
                filtered = filter_calls(raw_calls)
                log.info("  %s: %d after filter (>=%ds + recording)", acct_name, len(filtered), MIN_DURATION_SEC)

                for call in filtered:
                    call["_account"] = acct_name
                    person = assign_person_pre(call, acct_name)
                    all_calls_by_person[person].append(call)

            except Exception as e:
                log.error("Failed to fetch %s: %s", acct_name, e)

        for person, calls in all_calls_by_person.items():
            log.info("  %s: %d calls to process", person, len(calls))

        # Load whisper
        total_calls = sum(len(c) for c in all_calls_by_person.values())
        model = None
        if total_calls > 0:
            log.info("Loading Whisper model...")
            model = load_whisper_model()

        # Process each person
        all_stats = {}
        for person in ["hamza", "lilia", "sekou"]:
            calls = all_calls_by_person[person]
            if not calls and model is None:
                all_stats[person] = {"calls_total": 0, "calls_transcribed": 0, "calls_new": 0,
                                     "calls_skipped": 0, "calls_failed": 0, "errors": [],
                                     "durations": [], "categories": {}}
                continue

            log.info("")
            log.info("--- Processing %s (%d calls) ---", person.upper(), len(calls))

            # Disk check before each person
            check_disk_space("C:\\")

            stats = process_person(person, calls, model)
            all_stats[person] = stats

            # Push coaching_data
            avg_dur = round(sum(stats["durations"]) / len(stats["durations"])) if stats["durations"] else 0
            supabase_upsert("coaching_data", {
                "person_id": PERSON_IDS[person],
                "sync_date": date_str,
                "calls_total": stats["calls_total"],
                "calls_transcribed": stats["calls_transcribed"],
                "calls_new": stats["calls_new"],
                "avg_duration_sec": avg_dur,
                "call_breakdown": stats["categories"],
                "source": "justcall",
            }, on_conflict="person_id,sync_date")

            log.info("  %s: total=%d, transcribed=%d, new=%d, skipped=%d, failed=%d",
                     person, stats["calls_total"], stats["calls_transcribed"],
                     stats["calls_new"], stats["calls_skipped"], stats["calls_failed"])

        # Cron log
        elapsed = round(time.time() - start_time)
        total_new = sum(s["calls_new"] for s in all_stats.values())
        total_failed = sum(s["calls_failed"] for s in all_stats.values())
        all_errors = []
        for s in all_stats.values():
            all_errors.extend(s.get("errors", []))

        status = "success"
        if total_failed > 0 and total_new > 0:
            status = "partial"
        elif total_failed > 0 and total_new == 0 and total_calls > 0:
            status = "error"

        for person in ["hamza", "lilia", "sekou"]:
            supabase_insert("cron_logs", {
                "person_id": PERSON_IDS[person],
                "cron_type": "daily_sync",
                "status": status,
                "calls_processed": all_stats[person]["calls_total"],
                "transcripts_new": all_stats[person]["calls_new"],
                "error_msg": "; ".join(all_stats[person].get("errors", [])[:3]) or None,
                "duration_sec": elapsed,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })

        log.info("")
        log.info("=" * 60)
        log.info("DONE in %d seconds — status: %s", elapsed, status)
        log.info("  Total new transcripts: %d", total_new)
        log.info("  Total failed: %d", total_failed)
        log.info("=" * 60)

        # Score today's calls with Haiku IA
        if total_new > 0:
            try:
                log.info("")
                log.info("--- Haiku IA scoring for today's calls ---")
                from claude_scoring import score_call_haiku
                import json as _json

                total_scored_all = 0
                total_attempted = 0
                total_failed = 0
                for person in ["hamza", "lilia", "sekou"]:
                    person_calls = all_calls_by_person.get(person, [])
                    if not person_calls:
                        continue

                    scored_count = 0
                    for call in person_calls:
                        total_attempted += 1
                        call_id = str(call.get("id", ""))
                        pid = PERSON_IDS.get(person, "L3")
                        transcript_dir = TRANSCRIPT_BASE / person
                        json_path = transcript_dir / f"{call_id}.json"

                        if not json_path.exists():
                            continue

                        # Load transcript
                        try:
                            with open(json_path, "r", encoding="utf-8") as f:
                                t = _json.load(f)
                        except Exception:
                            continue

                        # Skip if already scored
                        if t.get("ai_scores"):
                            continue

                        # Score with Haiku
                        result = score_call_haiku(t)
                        if result and result.get("ai_scores"):
                            # Save to file
                            t["ai_scores"] = result["ai_scores"]
                            t["ai_global_score"] = result["ai_global_score"]
                            t["coaching_note"] = result.get("coaching_note", "")
                            with open(json_path, "w", encoding="utf-8") as f:
                                _json.dump(t, f, ensure_ascii=False, indent=2)

                            # PATCH Supabase
                            supabase_upsert_patch(call_id, {
                                "ai_scores": result["ai_scores"],
                                "ai_global_score": result["ai_global_score"],
                                "coaching_note": result.get("coaching_note", ""),
                            })
                            scored_count += 1
                            log.info("  Haiku [%s] %s: %.1f/10", person, call_id, result["ai_global_score"])
                        else:
                            total_failed += 1
                            if total_failed <= 3:
                                log.warning("  Haiku [%s] %s: scoring returned empty (result=%s)", person, call_id, type(result).__name__ if result else "None")

                    if scored_count > 0:
                        log.info("  %s: %d calls scored by Haiku", person, scored_count)
                    total_scored_all += scored_count

                log.info("Haiku scoring summary: %d/%d scored, %d failed", total_scored_all, total_attempted, total_failed)

            except Exception as haiku_err:
                log.error("Haiku scoring failed: %s", haiku_err, exc_info=True)

        # Send daily email report via SMTP
        if total_new > 0:
            try:
                # SAFETY: Only send daily email if we're past 17h local time.
                # If the script runs earlier (e.g. watchdog catch-up in the
                # morning), we'd send a report with only partial data. This
                # prevents incomplete reports from being emailed to Hamza.
                now_local = datetime.now()
                if now_local.hour < 17:
                    log.warning("")
                    log.warning("--- Email SKIPPED: current hour is %d:%02d (< 17:00)",
                                now_local.hour, now_local.minute)
                    log.warning("    Daily reports should only be sent at end of day.")
                    log.warning("    Transcription + scoring done, but email not sent.")
                    log.warning("    The 19:00 cron will re-score any new calls and send the real email.")
                else:
                    log.info("")
                    log.info("--- Sending daily email report ---")
                    import subprocess as _sp
                    _result = _sp.run(
                        [sys.executable, str(Path(__file__).parent / "daily_email_report.py"), date_str],
                        capture_output=True, text=True, timeout=300,
                        cwd=str(Path(__file__).parent)
                    )
                    if _result.returncode == 0:
                        log.info("Daily email sent!")
                    else:
                        log.warning("Daily email failed: %s", _result.stderr[:200])
            except Exception as email_err:
                log.warning("Daily email failed (non-critical): %s", email_err)

    except Exception as e:
        log.exception("FATAL ERROR: %s", e)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
