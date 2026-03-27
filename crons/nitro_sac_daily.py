#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SAC daily sync cron — runs every day at 23h30 on Nitro.

Pulls today's calls from JustCall for 3 SAC agents (Hamza, Lilia, Sekou),
transcribes recordings with faster-whisper (GPU), classifies calls
(support/inscription/plainte/info/autre), saves transcripts to disk,
and pushes summary data to Supabase.

Hamza/Sekou share JustCall agent_id 301418 (academie@) — separated by day:
  - Hamza: Mon-Fri (weekday 0-4)
  - Sekou: Sat-Sun (weekday 5-6)
Lilia uses agent_id 302145 (formateur@), Mon-Fri.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

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

AGENTS = {
    "hamza": {
        "person_id": "L3",
        "justcall_agent_id": "301418",
        "days": [0, 1, 2, 3, 4],       # Mon-Fri
        "transcript_dir": r"C:\Users\user\xguard_transcripts\hamza",
    },
    "lilia": {
        "person_id": "s2",
        "justcall_agent_id": "302145",
        "days": [0, 1, 2, 3, 4],       # Mon-Fri
        "transcript_dir": r"C:\Users\user\xguard_transcripts\lilia",
    },
    "sekou": {
        "person_id": "s3",
        "justcall_agent_id": "301418",  # same as Hamza
        "days": [5, 6],                # Sat-Sun
        "transcript_dir": r"C:\Users\user\xguard_transcripts\sekou",
    },
}

MIN_DURATION_SEC = 30
MAX_BATCH_SIZE = 500
MIN_DISK_FREE_MB = 500

# Whisper settings
WHISPER_MODEL = "medium"
WHISPER_LANGUAGE = "fr"
WHISPER_BEAM_SIZE = 3

# ---------------------------------------------------------------------------
# Run ID
# ---------------------------------------------------------------------------

RUN_ID = str(uuid.uuid4())[:8]

# ---------------------------------------------------------------------------
# Logging — console + file per agent
# ---------------------------------------------------------------------------

log = logging.getLogger("nitro_sac_daily")
log.setLevel(logging.INFO)

_fmt = logging.Formatter(
    f"%(asctime)s [{RUN_ID}] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console = logging.StreamHandler()
_console.setFormatter(_fmt)
log.addHandler(_console)

# ---------------------------------------------------------------------------
# Classification keywords (SAC)
# ---------------------------------------------------------------------------

SAC_SUPPORT_KW = re.compile(
    r"\b(problème|aide|fonctionne pas|ne marche pas|erreur|bug|technique"
    r"|accès|mot de passe|connexion|identifiant|compte)\b",
    re.IGNORECASE,
)
SAC_INSCRIPTION_KW = re.compile(
    r"\b(inscrire|inscription|formation|cours|session|programme"
    r"|date|place|disponible|gardiennage|sécurité|bsp|secourisme)\b",
    re.IGNORECASE,
)
SAC_PLAINTE_KW = re.compile(
    r"\b(plainte|mécontent|insatisfait|rembours|annuler|annulation"
    r"|déçu|inacceptable|pire|problème grave)\b",
    re.IGNORECASE,
)
SAC_INFO_KW = re.compile(
    r"\b(information|renseignement|question|comment|combien|prix"
    r"|tarif|horaire|adresse|coût|frais)\b",
    re.IGNORECASE,
)


def classify_call(text: str) -> str:
    """Classify a SAC call into support/inscription/plainte/info/autre."""
    matches = []
    if SAC_PLAINTE_KW.search(text):
        matches.append("plainte")
    if SAC_INSCRIPTION_KW.search(text):
        matches.append("inscription")
    if SAC_SUPPORT_KW.search(text):
        matches.append("support")
    if SAC_INFO_KW.search(text):
        matches.append("info")

    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        return "autre"
    # Multiple matches — prioritize: plainte > inscription > support > info
    for priority in ("plainte", "inscription", "support", "info"):
        if priority in matches:
            return priority
    return "autre"


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------


def supabase_upsert(table: str, data: dict | list, on_conflict: str = "") -> requests.Response:
    oc = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{oc}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    resp = requests.post(url, json=data, headers=headers, timeout=30)
    if resp.status_code >= 400:
        msg = f"Supabase upsert {table} failed ({resp.status_code}): {resp.text}"
        log.error(msg)
        raise RuntimeError(msg)
    return resp


def supabase_insert(table: str, data: dict) -> requests.Response:
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    resp = requests.post(url, json=data, headers=headers, timeout=30)
    if resp.status_code >= 400:
        msg = f"Supabase insert {table} failed ({resp.status_code}): {resp.text}"
        log.error(msg)
        raise RuntimeError(msg)
    return resp


# ---------------------------------------------------------------------------
# JustCall helpers
# ---------------------------------------------------------------------------


def fetch_justcall_calls(date_str: str, agent_id: str) -> list[dict]:
    """Fetch all calls for a specific date and agent_id from JustCall."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"{JUSTCALL_API_KEY}:{JUSTCALL_API_SECRET}",
    }
    all_calls: list[dict] = []
    page = 1

    while True:
        body = {
            "from_date": date_str,
            "to_date": date_str,
            "agent_id": agent_id,
            "per_page": 100,
            "page": page,
        }
        log.info("JustCall API — page %d for %s (agent_id=%s)", page, date_str, agent_id)
        resp = requests.post(JUSTCALL_API_URL, json=body, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        calls = data.get("data", [])
        if not calls:
            break

        all_calls.extend(calls)
        if len(calls) < 100:
            break
        page += 1
        time.sleep(0.5)

    log.info("JustCall returned %d raw calls for %s", len(all_calls), date_str)
    return all_calls


def filter_calls(calls: list[dict]) -> list[dict]:
    """Keep calls with duration >= 30s and a recording URL."""
    filtered = []
    for c in calls:
        duration = int(c.get("duration", 0) or 0)
        recording_url = (c.get("recording_url") or "").strip()
        if duration >= MIN_DURATION_SEC and recording_url:
            filtered.append(c)
    log.info("Filtered to %d calls (duration >= %ds, has recording)", len(filtered), MIN_DURATION_SEC)
    return filtered


# ---------------------------------------------------------------------------
# Disk check
# ---------------------------------------------------------------------------


def check_disk_space(path: str):
    usage = shutil.disk_usage(path)
    free_mb = usage.free // (1024 * 1024)
    if free_mb < MIN_DISK_FREE_MB:
        raise RuntimeError(f"Low disk space: {free_mb}MB free (need {MIN_DISK_FREE_MB}MB)")
    log.info("Disk space OK: %dMB free", free_mb)


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------


def load_whisper_model():
    """Lazy-load faster-whisper model on CUDA with CPU fallback."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        log.error("faster-whisper not installed. pip install faster-whisper")
        sys.exit(1)

    try:
        model = WhisperModel(
            WHISPER_MODEL,
            device="cuda",
            compute_type="int8_float16",
        )
        log.info("Whisper model loaded on CUDA")
    except Exception:
        log.warning("CUDA unavailable, falling back to CPU")
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")

    return model


def transcribe_call(model, recording_url: str) -> tuple[str, str]:
    """Download recording, transcribe, return (transcript, language)."""
    tmp_path = None
    try:
        resp = requests.get(recording_url, timeout=120, stream=True)
        resp.raise_for_status()

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)

        segments, info = model.transcribe(
            tmp_path,
            language=WHISPER_LANGUAGE,
            beam_size=WHISPER_BEAM_SIZE,
            vad_filter=True,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        return text, info.language

    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Process one agent
# ---------------------------------------------------------------------------


def process_agent(agent_name: str, config: dict, model, date_str: str) -> dict:
    """Process all calls for one SAC agent. Returns stats dict."""
    person_id = config["person_id"]
    agent_id = config["justcall_agent_id"]
    transcript_dir = Path(config["transcript_dir"])
    transcript_dir.mkdir(parents=True, exist_ok=True)

    stats = {
        "calls_total": 0,
        "calls_transcribed": 0,
        "calls_new": 0,
        "calls_skipped": 0,
        "calls_failed": 0,
        "errors": [],
    }

    # Log start to cron_logs
    cron_log_id = None
    try:
        cron_start = datetime.now(timezone.utc).isoformat()
        supabase_insert("cron_logs", {
            "person_id": person_id,
            "cron_type": "daily_sync",
            "status": "running",
            "started_at": cron_start,
        })
    except Exception as exc:
        log.warning("Failed to log cron start: %s", exc)

    # Update nitro_status to running
    try:
        supabase_upsert("nitro_status", {
            "person_id": person_id,
            "task_type": "daily_sync",
            "status": "running",
            "done": 0,
            "total": 0,
            "pct": 0,
            "gpu_active": True,
            "last_file": "",
            "started_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="person_id,task_type")
    except Exception as exc:
        log.warning("Failed to update nitro_status: %s", exc)

    # Fetch calls
    try:
        raw_calls = fetch_justcall_calls(date_str, agent_id)
        calls = filter_calls(raw_calls)
    except Exception as exc:
        log.error("JustCall fetch failed for %s: %s", agent_name, exc)
        stats["errors"].append(str(exc))
        _finalize_agent(person_id, stats, date_str)
        return stats

    stats["calls_total"] = len(calls)

    if not calls:
        log.info("No qualifying calls for %s on %s", agent_name, date_str)
        _finalize_agent(person_id, stats, date_str)
        return stats

    if len(calls) > MAX_BATCH_SIZE:
        log.warning("Batch size %d exceeds max %d — truncating", len(calls), MAX_BATCH_SIZE)
        calls = calls[:MAX_BATCH_SIZE]
        stats["calls_total"] = len(calls)

    # Classify and transcribe
    call_breakdown = {"support": 0, "inscription": 0, "plainte": 0, "info": 0, "autre": 0}
    durations = []
    consecutive_failures = 0

    for i, call in enumerate(calls, 1):
        call_id = call.get("id") or call.get("call_id") or f"unknown_{i}"
        call_id = str(call_id)
        out_path = transcript_dir / f"{call_id}.json"

        # Skip existing
        if out_path.exists():
            try:
                with open(out_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                cat = existing.get("category", "autre")
                call_breakdown[cat] = call_breakdown.get(cat, 0) + 1
                durations.append(existing.get("duration_s", 0))
                stats["calls_skipped"] += 1
                stats["calls_transcribed"] += 1
            except Exception:
                pass
            continue

        # Transcribe
        recording_url = (call.get("recording_url") or "").strip()
        if not recording_url:
            stats["calls_skipped"] += 1
            continue

        try:
            t_start = time.time()
            transcript_text, lang = transcribe_call(model, recording_url)
            elapsed = round(time.time() - t_start, 1)

            duration_s = int(call.get("duration", 0) or 0)
            word_count = len(transcript_text.split()) if transcript_text else 0
            category = classify_call(transcript_text)
            call_breakdown[category] += 1
            durations.append(duration_s)

            # Build transcript JSON
            transcript_data = {
                "id": call_id,
                "contact_name": call.get("contact_name", ""),
                "contact_number": call.get("contact_number", ""),
                "call_time": call.get("call_time") or call.get("datetime", ""),
                "duration_s": duration_s,
                "recording_url": recording_url,
                "transcript": transcript_text,
                "word_count": word_count,
                "language": lang,
                "category": category,
                "source": "justcall",
                "agent": agent_name,
                "transcribed_at": datetime.now(timezone.utc).isoformat(),
            }

            # Atomic write
            tmp_path = out_path.with_suffix(".json.tmp")
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, ensure_ascii=False, indent=2)
            os.replace(str(tmp_path), str(out_path))

            stats["calls_new"] += 1
            stats["calls_transcribed"] += 1
            consecutive_failures = 0

            log.info(
                "[%d/%d] %s — %ds call, %d words, %s, %.1fs transcribe",
                i, len(calls), call_id, duration_s, word_count, category, elapsed,
            )

            # Update nitro_status progress
            try:
                supabase_upsert("nitro_status", {
                    "person_id": person_id,
                    "task_type": "daily_sync",
                    "status": "running",
                    "done": stats["calls_transcribed"],
                    "total": stats["calls_total"],
                    "pct": round(100 * stats["calls_transcribed"] / stats["calls_total"], 1),
                    "gpu_active": True,
                    "last_file": call_id,
                }, on_conflict="person_id,task_type")
            except Exception:
                pass

        except Exception as exc:
            stats["calls_failed"] += 1
            consecutive_failures += 1
            stats["errors"].append(f"{call_id}: {str(exc)[:100]}")
            log.error("[%d/%d] FAILED %s: %s", i, len(calls), call_id, exc)

            if consecutive_failures >= 10:
                log.error("10 consecutive failures — aborting %s", agent_name)
                break

    # Finalize
    _finalize_agent(person_id, stats, date_str, call_breakdown, durations)
    return stats


def _finalize_agent(
    person_id: str,
    stats: dict,
    date_str: str,
    call_breakdown: dict | None = None,
    durations: list | None = None,
):
    """Push final coaching_data, nitro_status, cron_logs to Supabase."""
    avg_dur = round(sum(durations) / len(durations)) if durations else 0
    status = "success" if not stats["errors"] else ("partial" if stats["calls_transcribed"] > 0 else "error")
    error_msg = "; ".join(stats["errors"][:5]) if stats["errors"] else None

    # coaching_data
    try:
        supabase_upsert("coaching_data", {
            "person_id": person_id,
            "sync_date": date_str,
            "calls_total": stats["calls_total"],
            "calls_transcribed": stats["calls_transcribed"],
            "calls_new": stats["calls_new"],
            "avg_duration_sec": avg_dur,
            "call_breakdown": call_breakdown,
            "source": "justcall",
        }, on_conflict="person_id,sync_date")
    except Exception as exc:
        log.error("coaching_data push failed: %s", exc)

    # nitro_status → done
    try:
        supabase_upsert("nitro_status", {
            "person_id": person_id,
            "task_type": "daily_sync",
            "status": "done",
            "done": stats["calls_transcribed"],
            "total": stats["calls_total"],
            "pct": 100.0 if stats["calls_total"] > 0 else 0,
            "gpu_active": False,
            "last_file": "",
        }, on_conflict="person_id,task_type")
    except Exception as exc:
        log.error("nitro_status push failed: %s", exc)

    # cron_logs
    try:
        supabase_insert("cron_logs", {
            "person_id": person_id,
            "cron_type": "daily_sync",
            "status": status,
            "calls_processed": stats["calls_total"],
            "transcripts_new": stats["calls_new"],
            "error_msg": error_msg,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        log.error("cron_logs push failed: %s", exc)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    t_start = time.time()
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    weekday = today.weekday()  # 0=Mon, 6=Sun

    log.info("=" * 60)
    log.info("SAC Daily Sync — %s (weekday=%d) [run=%s]", date_str, weekday, RUN_ID)
    log.info("=" * 60)

    # Check disk space
    check_disk_space(r"C:\Users\user")

    # Load whisper model once for all agents
    model = load_whisper_model()

    grand_total = 0
    grand_new = 0

    for agent_name, config in AGENTS.items():
        # Day filter — skip if today is not this agent's day
        if weekday not in config["days"]:
            log.info("Skipping %s — not their day (weekday=%d, days=%s)", agent_name, weekday, config["days"])
            continue

        log.info("")
        log.info("--- %s (person_id=%s, agent_id=%s) ---", agent_name.upper(), config["person_id"], config["justcall_agent_id"])

        try:
            stats = process_agent(agent_name, config, model, date_str)
            grand_total += stats["calls_total"]
            grand_new += stats["calls_new"]
            log.info(
                "%s done: %d total, %d new, %d skipped, %d failed",
                agent_name, stats["calls_total"], stats["calls_new"],
                stats["calls_skipped"], stats["calls_failed"],
            )
        except Exception as exc:
            log.error("FATAL error processing %s: %s", agent_name, exc)

    elapsed = round(time.time() - t_start, 1)
    log.info("")
    log.info("=" * 60)
    log.info("SAC DAILY SYNC COMPLETE — %d calls, %d new, %.1fs", grand_total, grand_new, elapsed)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
