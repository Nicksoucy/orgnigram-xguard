#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heidys daily sync cron — runs every day at 23h15 on Nitro.

Pulls today's calls from JustCall, transcribes recordings with faster-whisper (GPU),
saves transcripts to disk, and pushes summary data to Supabase.
"""

import json
import logging
import os
import sys
import tempfile
import time
from datetime import datetime, timezone

import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JUSTCALL_API_URL = "https://api.justcall.io/v1/calls/query"
JUSTCALL_API_KEY = "daf60d953694336f07c84c74205eb311dd85c996"
JUSTCALL_API_SECRET = "20612f8fcb80ef33845cbdc226bc8174853c82dd"
JUSTCALL_AGENT_ID = "407715"

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

PERSON_ID = "v1"
AGENT_NAME = "heidys"
TRANSCRIPT_DIR = r"C:\Users\user\xguard_transcripts\heidys"
MIN_DURATION_SEC = 30

# Whisper settings
WHISPER_MODEL = "medium"
WHISPER_LANGUAGE = "fr"
WHISPER_BEAM_SIZE = 3

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("nitro_heidys_daily")

# ---------------------------------------------------------------------------
# Supabase helper
# ---------------------------------------------------------------------------


def supabase_upsert(table: str, data: dict | list, on_conflict: str) -> requests.Response:
    """Upsert data into a Supabase table via PostgREST."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    resp = requests.post(url, json=data, headers=headers, timeout=30)
    if resp.status_code >= 400:
        log.warning("Supabase upsert %s failed (%s): %s", table, resp.status_code, resp.text)
    return resp


def supabase_insert(table: str, data: dict) -> requests.Response:
    """Insert a single row into a Supabase table (no upsert)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    resp = requests.post(url, json=data, headers=headers, timeout=30)
    if resp.status_code >= 400:
        log.warning("Supabase insert %s failed (%s): %s", table, resp.status_code, resp.text)
    return resp


# ---------------------------------------------------------------------------
# JustCall helpers
# ---------------------------------------------------------------------------


def fetch_justcall_calls(date_str: str) -> list[dict]:
    """Fetch all calls for *date_str* (YYYY-MM-DD) from JustCall, paginated."""
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
            "agent_id": JUSTCALL_AGENT_ID,
            "per_page": 100,
            "page": page,
        }
        log.info("JustCall API — fetching page %d for %s", page, date_str)
        resp = requests.post(JUSTCALL_API_URL, json=body, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        calls = data.get("data", [])
        if not calls:
            break

        all_calls.extend(calls)
        # If we got fewer than per_page, we've reached the last page
        if len(calls) < 100:
            break
        page += 1

    log.info("JustCall returned %d raw calls for %s", len(all_calls), date_str)
    return all_calls


def filter_calls(calls: list[dict]) -> list[dict]:
    """Keep calls with duration >= 30 s and a recording URL."""
    filtered = []
    for c in calls:
        duration = int(c.get("duration", 0) or 0)
        recording_url = (c.get("recording_url") or "").strip()
        if duration >= MIN_DURATION_SEC and recording_url:
            filtered.append(c)
    log.info("Filtered to %d calls (duration >= %ds, has recording)", len(filtered), MIN_DURATION_SEC)
    return filtered


# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------


def _load_whisper_model():
    """Load faster-whisper model with GPU, fall back to CPU."""
    from faster_whisper import WhisperModel  # noqa: local import

    try:
        model = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="int8_float16")
        log.info("Whisper model loaded on CUDA (int8_float16)")
        return model, True
    except Exception as exc:
        log.warning("CUDA unavailable (%s), falling back to CPU", exc)
        model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        return model, False


def transcribe_recording(model, recording_url: str) -> tuple[str, int]:
    """Download a recording to a temp file, transcribe it, return (text, word_count)."""
    resp = requests.get(recording_url, timeout=120)
    resp.raise_for_status()

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".mp3")
    try:
        os.write(tmp_fd, resp.content)
        os.close(tmp_fd)

        segments, _info = model.transcribe(
            tmp_path,
            language=WHISPER_LANGUAGE,
            beam_size=WHISPER_BEAM_SIZE,
            vad_filter=True,
        )
        text_parts = [seg.text for seg in segments]
        full_text = " ".join(text_parts).strip()
        word_count = len(full_text.split()) if full_text else 0
        return full_text, word_count
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------------------------------------------------------------------------
# Transcript I/O
# ---------------------------------------------------------------------------


def already_transcribed(call_id: str) -> bool:
    """Check if a transcript JSON already exists on disk."""
    path = os.path.join(TRANSCRIPT_DIR, f"{call_id}.json")
    return os.path.isfile(path)


def save_transcript(call: dict, transcript: str, word_count: int) -> str:
    """Write transcript JSON to disk and return the file path."""
    call_id = str(call.get("id", call.get("call_id", "")))
    out = {
        "id": call_id,
        "contact_name": call.get("contact_name", ""),
        "contact_number": call.get("contact_number", ""),
        "call_time": call.get("call_time", call.get("datetime", "")),
        "duration_s": int(call.get("duration", 0) or 0),
        "recording_url": call.get("recording_url", ""),
        "transcript": transcript,
        "word_count": word_count,
        "language": WHISPER_LANGUAGE,
        "source": "justcall",
        "agent": AGENT_NAME,
        "transcribed_at": datetime.now(timezone.utc).isoformat(),
    }
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    path = os.path.join(TRANSCRIPT_DIR, f"{call_id}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------------------
# Supabase status updates
# ---------------------------------------------------------------------------


def update_nitro_status(
    status: str,
    done: int,
    total: int,
    gpu_active: bool,
    last_file: str = "",
):
    pct = round(done / total * 100, 1) if total else 0.0
    supabase_upsert(
        "nitro_status",
        {
            "person_id": PERSON_ID,
            "task_type": "daily_sync",
            "status": status,
            "done": done,
            "total": total,
            "pct": pct,
            "gpu_active": gpu_active,
            "last_file": last_file,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="person_id,task_type",
    )


def push_coaching_data(today_str: str, calls_total: int, calls_transcribed: int, calls_new: int, avg_duration: float):
    supabase_upsert(
        "coaching_data",
        {
            "person_id": PERSON_ID,
            "sync_date": today_str,
            "calls_total": calls_total,
            "calls_transcribed": calls_transcribed,
            "calls_new": calls_new,
            "avg_duration_sec": round(avg_duration, 1),
            "source": "justcall",
        },
        on_conflict="person_id,sync_date",
    )


def push_cron_log(
    status: str,
    calls_processed: int,
    transcripts_new: int,
    started_at: str,
    duration_sec: float,
    error_msg: str = "",
    dates_synced: list[str] | None = None,
):
    finished_at = datetime.now(timezone.utc).isoformat()
    # Encode synced dates as "dates:..." in error_msg when no actual error
    msg = error_msg or None
    if not error_msg and dates_synced and len(dates_synced) > 1:
        msg = "dates:" + ", ".join(dates_synced)
    supabase_insert(
        "cron_logs",
        {
            "person_id": PERSON_ID,
            "cron_type": "daily_sync",
            "status": status,
            "calls_processed": calls_processed,
            "transcripts_new": transcripts_new,
            "duration_sec": round(duration_sec),
            "error_msg": msg,
            "started_at": started_at,
            "finished_at": finished_at,
        },
    )


# ---------------------------------------------------------------------------
# Catch-up: determine dates to sync
# ---------------------------------------------------------------------------


def get_last_successful_sync_date() -> str | None:
    """Query cron_logs for the last successful daily_sync date for this person."""
    url = (
        f"{SUPABASE_URL}/rest/v1/cron_logs"
        f"?person_id=eq.{PERSON_ID}&cron_type=eq.daily_sync&status=eq.success"
        f"&order=started_at.desc&limit=1"
    )
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        rows = resp.json()
        if rows and rows[0].get("started_at"):
            # Extract date from the started_at timestamp
            return rows[0]["started_at"][:10]
    except Exception as exc:
        log.warning("Could not fetch last sync date: %s", exc)
    return None


def compute_dates_to_sync(today_str: str) -> list[str]:
    """Return list of dates to sync, catching up any missed days."""
    last_sync = get_last_successful_sync_date()
    if last_sync:
        from datetime import timedelta as td
        last_dt = datetime.strptime(last_sync, "%Y-%m-%d")
        today_dt = datetime.strptime(today_str, "%Y-%m-%d")
        start_dt = last_dt + td(days=1)
        dates = []
        d = start_dt
        while d <= today_dt:
            dates.append(d.strftime("%Y-%m-%d"))
            d += td(days=1)
        # Cap at 14 days to avoid runaway backfills
        dates = dates[-14:]
    else:
        dates = [today_str]

    return dates


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    t0 = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    today_str = datetime.now().strftime("%Y-%m-%d")
    log.info("===== Heidys daily sync started — %s =====", today_str)

    error_msg = ""
    calls_processed = 0
    transcripts_new = 0
    gpu_active = False

    try:
        # 0. Determine dates to sync (catch-up if missed days)
        dates_to_sync = compute_dates_to_sync(today_str)
        if len(dates_to_sync) > 1:
            log.info("CATCH-UP: %d days to sync — %s", len(dates_to_sync), ", ".join(dates_to_sync))

        # 1. Fetch calls for all dates
        raw_calls = []
        for sync_date in dates_to_sync:
            day_calls = fetch_justcall_calls(sync_date)
            log.info("  %s: %d raw calls", sync_date, len(day_calls))
            raw_calls.extend(day_calls)

        calls = filter_calls(raw_calls)
        calls_total = len(calls)

        if not calls:
            log.info("No qualifying calls today. Nothing to do.")
            push_coaching_data(today_str, len(raw_calls), 0, 0, 0.0)
            push_cron_log("success", 0, 0, started_at, time.time() - t0, dates_synced=dates_to_sync)
            update_nitro_status("idle", 0, 0, False)
            return

        # 2. Load whisper model
        model, gpu_active = _load_whisper_model()
        update_nitro_status("running", 0, calls_total, gpu_active)

        durations = []
        # 3. Process each call
        for idx, call in enumerate(calls, start=1):
            call_id = str(call.get("id", call.get("call_id", "")))
            duration = int(call.get("duration", 0) or 0)
            durations.append(duration)

            # Resumability: skip if already transcribed
            if already_transcribed(call_id):
                log.info("[%d/%d] call %s already transcribed — skipping", idx, calls_total, call_id)
                calls_processed += 1
                update_nitro_status("running", idx, calls_total, gpu_active, last_file=f"{call_id}.json")
                continue

            try:
                log.info("[%d/%d] Transcribing call %s (%ds)…", idx, calls_total, call_id, duration)
                recording_url = call.get("recording_url", "")
                transcript, word_count = transcribe_recording(model, recording_url)
                path = save_transcript(call, transcript, word_count)
                transcripts_new += 1
                calls_processed += 1
                log.info("  -> saved %s (%d words)", path, word_count)
            except Exception as exc:
                log.error("  !! Error on call %s: %s", call_id, exc, exc_info=True)
                calls_processed += 1
                continue

            update_nitro_status("running", idx, calls_total, gpu_active, last_file=f"{call_id}.json")

        # 4. Push summary to Supabase
        avg_dur = sum(durations) / len(durations) if durations else 0.0
        push_coaching_data(today_str, len(raw_calls), calls_processed, transcripts_new, avg_dur)
        update_nitro_status("idle", calls_total, calls_total, False)

        elapsed = time.time() - t0
        log.info("===== Sync complete: %d processed, %d new transcripts (%.1fs) =====", calls_processed, transcripts_new, elapsed)
        push_cron_log("success", calls_processed, transcripts_new, started_at, elapsed, dates_synced=dates_to_sync)

    except Exception as exc:
        error_msg = str(exc)[:500]
        log.error("Fatal error: %s", exc, exc_info=True)
        elapsed = time.time() - t0
        push_cron_log("error", calls_processed, transcripts_new, started_at, elapsed, error_msg=error_msg)
        update_nitro_status("error", calls_processed, 0, False)
        sys.exit(1)


if __name__ == "__main__":
    main()
