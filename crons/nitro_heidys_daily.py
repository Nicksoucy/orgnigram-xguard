#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heidys daily sync cron — runs every day at 23h15 on Nitro.

Pulls today's calls from JustCall, transcribes recordings with faster-whisper (GPU),
saves transcripts to disk, and pushes summary data to Supabase.

Phase 1 hardening (2026-03-25):
- Atomic file writes (write .tmp then rename)
- Per-file error tracking (success/failed/skipped counts)
- Supabase push failures are FATAL (exit 1)
- Batch size limit (max 500 calls per run)
- Disk space check before starting
- File integrity validation on read
- UTC everywhere
- File logging
- Run ID for traceability
"""

import json
import logging
import os
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
JUSTCALL_AGENT_ID = "407715"

# GHL fallback — in case Heidys uses GHL instead of JustCall
GHL_TOKEN = "pit-7de455ab-c46e-47a4-af9e-0b07a6c3a1ee"
GHL_LOCATION = "dfkLurZY2ADWAUZl4zYc"
GHL_HEIDYS_USER_ID = "FqpS2HfIklBPAiAoANBB"
GHL_BASE = "https://services.leadconnectorhq.com"
GHL_HEADERS = {
    "Authorization": f"Bearer {GHL_TOKEN}",
    "Version": "2021-07-28",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Origin": "https://app.gohighlevel.com",
    "Referer": "https://app.gohighlevel.com/",
}

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
WAV_DIR = os.path.join(TRANSCRIPT_DIR, "wav")
LOG_FILE = os.path.join(TRANSCRIPT_DIR, "daily.log")
MIN_DURATION_SEC = 30
MAX_BATCH_SIZE = 500  # prevent runaway backfills
MIN_DISK_FREE_MB = 500  # require 500MB free before starting

# Whisper settings
WHISPER_MODEL = "medium"
WHISPER_LANGUAGE = "fr"
WHISPER_BEAM_SIZE = 3

# ---------------------------------------------------------------------------
# Run ID — unique per execution for traceability
# ---------------------------------------------------------------------------

RUN_ID = str(uuid.uuid4())[:8]

# ---------------------------------------------------------------------------
# Logging — both console and file
# ---------------------------------------------------------------------------

os.makedirs(TRANSCRIPT_DIR, exist_ok=True)

log = logging.getLogger("nitro_heidys_daily")
log.setLevel(logging.INFO)

_fmt = logging.Formatter(
    f"%(asctime)s [{RUN_ID}] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console = logging.StreamHandler()
_console.setFormatter(_fmt)
log.addHandler(_console)

_file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
_file_handler.setFormatter(_fmt)
log.addHandler(_file_handler)

# ---------------------------------------------------------------------------
# Supabase helpers — failures are FATAL
# ---------------------------------------------------------------------------


def supabase_upsert(table: str, data: dict | list, on_conflict: str) -> requests.Response:
    """Upsert data into a Supabase table. Raises on failure."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
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
    """Insert a row into Supabase. Raises on failure."""
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
        if len(calls) < 100:
            break
        page += 1
        # Rate limit protection
        time.sleep(0.5)

    # Safety: if agent_id is inactive, JustCall may return ALL calls. Cap at 500.
    if len(all_calls) > 500:
        log.warning("JustCall returned %d calls (likely all agents). Agent 407715 may be inactive. Returning empty.", len(all_calls))
        return []
    log.info("JustCall returned %d raw calls for %s", len(all_calls), date_str)
    return all_calls


def _ts_to_date(ts):
    """Convert GHL timestamp (ms int or ISO string) to YYYY-MM-DD."""
    if isinstance(ts, (int, float)):
        return datetime.utcfromtimestamp(ts / 1000).strftime("%Y-%m-%d")
    return str(ts)[:10] if ts else ""


def fetch_ghl_calls_heidys(date_str: str) -> list[dict]:
    """Fetch Heidys's calls from GHL for a single date.
    GHL lastMessageDate is a Unix timestamp in ms (int).
    Paginates conversations assigned to Heidys, checks each for call messages."""
    ghl_calls = []
    target_date = date_str
    seen_ids = set()

    # Paginate conversations (GHL doesn't support offset, so we use limit + stop condition)
    params = {
        "locationId": GHL_LOCATION,
        "assignedTo": GHL_HEIDYS_USER_ID,
        "limit": 50,
        "sort": "desc",
        "sortBy": "last_message_date",
    }

    try:
        resp = requests.get(f"{GHL_BASE}/conversations/search",
                            params=params, headers=GHL_HEADERS, timeout=30)
        if resp.status_code != 200:
            log.warning("GHL conversations/search failed (%d): %s", resp.status_code, resp.text[:200])
            return ghl_calls
        convs = resp.json().get("conversations", [])
    except Exception as exc:
        log.warning("GHL conversation search failed: %s", exc)
        return ghl_calls

    log.info("  GHL: %d conversations returned for Heidys", len(convs))

    for conv in convs:
        conv_id = conv.get("id", "")
        last_msg_ts = conv.get("lastMessageDate")
        conv_date = _ts_to_date(last_msg_ts)

        # Stop if conversations are older than target date
        if conv_date and conv_date < target_date:
            break

        # Skip if not target date (could be future)
        # But check messages anyway — conv might have older calls on target date
        # Only skip if more than 1 day ahead
        if conv_date and conv_date > target_date:
            # Still check — the conversation may have calls from target_date
            pass

        # Fetch messages for this conversation
        try:
            r2 = requests.get(f"{GHL_BASE}/conversations/{conv_id}/messages",
                              params={"locationId": GHL_LOCATION, "limit": 30},
                              headers=GHL_HEADERS, timeout=15)
            if r2.status_code != 200:
                continue
            raw = r2.json().get("messages", {})
            if isinstance(raw, dict):
                raw = raw.get("messages", [])

            for msg in raw:
                if not isinstance(msg, dict):
                    continue
                if msg.get("messageType") != "TYPE_CALL":
                    continue

                date_added = msg.get("dateAdded", "")
                if date_added[:10] != target_date:
                    continue

                msg_id = msg.get("id", "")
                if msg_id in seen_ids:
                    continue
                seen_ids.add(msg_id)

                meta_call = msg.get("meta", {}).get("call", {}) if isinstance(msg.get("meta"), dict) else {}
                duration = meta_call.get("duration") or 0

                contact_name = conv.get("contactName", "")
                contact_number = conv.get("phone", "") or msg.get("to", "")

                ghl_calls.append({
                    "id": msg_id,
                    "duration": duration,
                    "recording_url": f"__GHL__{msg_id}" if duration >= MIN_DURATION_SEC else "",
                    "call_time": date_added,
                    "contact_number": contact_number,
                    "contact_name": contact_name,
                    "direction": "1" if msg.get("direction") == "inbound" else "0",
                    "source": "ghl",
                })
        except Exception as e:
            log.warning("  GHL conv %s messages failed: %s", conv_id[:8], e)

        time.sleep(0.12)

    log.info("GHL: %d Heidys calls for %s (%d with recording)", len(ghl_calls), date_str,
             len([c for c in ghl_calls if c.get("recording_url")]))
    return ghl_calls


def download_ghl_recording(msg_id: str, save_dir) -> str | None:
    """Download recording from GHL magic endpoint. Returns file path or None."""
    import os
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    wav_path = save_dir / f"ghl_{msg_id}.wav"
    if wav_path.exists() and wav_path.stat().st_size > 1000:
        return str(wav_path)
    try:
        rec_url = f"{GHL_BASE}/conversations/messages/{msg_id}/locations/{GHL_LOCATION}/recording"
        resp = requests.get(rec_url, headers=GHL_HEADERS, timeout=120, stream=True)
        if resp.status_code == 422:
            return None
        resp.raise_for_status()
        tmp = wav_path.with_suffix(".wav.tmp")
        size = 0
        with open(tmp, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                size += len(chunk)
        if size < 1000:
            tmp.unlink(missing_ok=True)
            return None
        tmp.rename(wav_path)
        return str(wav_path)
    except Exception as exc:
        log.error("GHL recording download failed for %s: %s", msg_id, exc)
        return None


# ---------------------------------------------------------------------------
# GHL: Find contact, post note, create task
# ---------------------------------------------------------------------------

def _ghl_find_contact(phone: str) -> str | None:
    """Find GHL contact by phone number. Returns contactId or None."""
    if not phone:
        return None
    # Normalize phone
    clean = phone.strip().replace(" ", "").replace("-", "")
    if not clean.startswith("+"):
        clean = "+1" + clean if len(clean) == 10 else "+" + clean
    try:
        resp = requests.get(
            f"{GHL_BASE}/contacts/search/duplicate",
            params={"locationId": GHL_LOCATION, "number": clean},
            headers=GHL_HEADERS, timeout=15,
        )
        if resp.status_code == 200:
            contact = resp.json().get("contact", {})
            return contact.get("id")
    except Exception as e:
        log.warning("GHL contact lookup failed for %s: %s", phone, e)
    return None


def _ghl_post_note(contact_id: str, body: str):
    """Post a note on a GHL contact."""
    resp = requests.post(
        f"{GHL_BASE}/contacts/{contact_id}/notes",
        json={"body": body},
        headers={**GHL_HEADERS, "Content-Type": "application/json"},
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        log.warning("GHL post note failed (%d): %s", resp.status_code, resp.text[:100])


def _ghl_create_task(contact_id: str, title: str, body: str, due_date: str):
    """Create a task on a GHL contact."""
    resp = requests.post(
        f"{GHL_BASE}/contacts/{contact_id}/tasks",
        json={"title": title, "body": body, "dueDate": f"{due_date}T10:00:00Z", "completed": False},
        headers={**GHL_HEADERS, "Content-Type": "application/json"},
        timeout=15,
    )
    if resp.status_code not in (200, 201):
        log.warning("GHL create task failed (%d): %s", resp.status_code, resp.text[:100])


def filter_calls(calls: list[dict]) -> list[dict]:
    """Keep calls with duration >= 30s and a recording URL (or GHL marker)."""
    filtered = []
    for c in calls:
        duration = int(c.get("duration", 0) or 0)
        recording_url = (c.get("recording_url") or "").strip()
        if duration >= MIN_DURATION_SEC and recording_url:
            filtered.append(c)
    log.info("Filtered to %d calls (duration >= %ds, has recording)", len(filtered), MIN_DURATION_SEC)
    return filtered


# ---------------------------------------------------------------------------
# Disk checks
# ---------------------------------------------------------------------------


def check_disk_space():
    """Ensure enough disk space before starting. Raises if not enough."""
    usage = shutil.disk_usage(TRANSCRIPT_DIR)
    free_mb = usage.free / (1024 * 1024)
    if free_mb < MIN_DISK_FREE_MB:
        raise RuntimeError(
            f"Not enough disk space: {free_mb:.0f}MB free, need {MIN_DISK_FREE_MB}MB. "
            f"Clean up {TRANSCRIPT_DIR} before running."
        )
    log.info("Disk check: %.0fMB free (need %dMB)", free_mb, MIN_DISK_FREE_MB)


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
# Transcript I/O — ATOMIC writes
# ---------------------------------------------------------------------------


def already_transcribed(call_id: str) -> bool:
    """Check if a valid transcript JSON exists on disk."""
    path = os.path.join(TRANSCRIPT_DIR, f"{call_id}.json")
    if not os.path.isfile(path):
        return False
    # Validate file isn't corrupt (can read + has required fields)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if data.get("id") and data.get("transcript") is not None:
            return True
        log.warning("Corrupt transcript %s (missing fields) — will re-transcribe", call_id)
        os.remove(path)
        return False
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("Corrupt transcript %s (%s) — will re-transcribe", call_id, exc)
        os.remove(path)
        return False


def save_transcript(call: dict, transcript: str, word_count: int) -> str:
    """Write transcript JSON ATOMICALLY (write to .tmp then rename)."""
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
        "run_id": RUN_ID,
    }
    os.makedirs(TRANSCRIPT_DIR, exist_ok=True)
    final_path = os.path.join(TRANSCRIPT_DIR, f"{call_id}.json")
    tmp_path = final_path + ".tmp"

    # Write to .tmp first, then atomic rename
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    # On Windows, os.replace is atomic if same drive
    os.replace(tmp_path, final_path)
    return final_path


# ---------------------------------------------------------------------------
# Push individual call metadata to Supabase `calls` table
# ---------------------------------------------------------------------------


def push_call(call: dict, word_count: int):
    """Push a single call's metadata to the calls table (non-fatal)."""
    call_id = str(call.get("id", call.get("call_id", "")))
    call_time = call.get("call_time", call.get("datetime", ""))
    try:
        supabase_upsert(
            "calls",
            {
                "id": call_id,
                "person_id": PERSON_ID,
                "call_time": call_time,
                "duration_s": int(call.get("duration", 0) or 0),
                "contact_name": (call.get("contact_name", "") or "")[:200],
                "contact_number": (call.get("contact_number", "") or "")[:50],
                "word_count": word_count,
                "language": WHISPER_LANGUAGE,
                "recording_url": (call.get("recording_url", "") or "")[:500],
                "source": "justcall",
            },
            on_conflict="id",
        )
    except RuntimeError:
        log.warning("Failed to push call %s to calls table (non-fatal)", call_id)


# ---------------------------------------------------------------------------
# Supabase status updates
# ---------------------------------------------------------------------------


def update_nitro_status(status: str, done: int, total: int, gpu_active: bool, last_file: str = ""):
    pct = round(done / total * 100, 1) if total else 0.0
    try:
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
    except RuntimeError:
        # Non-fatal: status updates are nice-to-have, don't abort the whole run
        log.warning("Failed to update nitro_status (non-fatal, continuing)")


def push_coaching_data(
    sync_date: str, calls_total: int, calls_success: int, calls_failed: int,
    calls_new: int, avg_duration: float
):
    """Push daily summary to Supabase. RAISES on failure."""
    supabase_upsert(
        "coaching_data",
        {
            "person_id": PERSON_ID,
            "sync_date": sync_date,
            "calls_total": calls_total,
            "calls_transcribed": calls_success,
            "calls_new": calls_new,
            "avg_duration_sec": int(round(avg_duration)),
            "source": "justcall",
        },
        on_conflict="person_id,sync_date",
    )


def push_call_activity(
    activity_date: str, total_dials: int, answered: int, not_answered: int,
    short_calls: int, qualified_calls: int, transcribed: int, avg_duration: float
):
    """Push daily activity funnel to Supabase. RAISES on failure."""
    supabase_upsert(
        "call_activity",
        {
            "person_id": PERSON_ID,
            "activity_date": activity_date,
            "total_dials": total_dials,
            "answered": answered,
            "not_answered": not_answered,
            "short_calls": short_calls,
            "qualified_calls": qualified_calls,
            "transcribed": transcribed,
            "avg_duration_sec": int(round(avg_duration)),
        },
        on_conflict="person_id,activity_date",
    )


def push_cron_log(
    status: str,
    calls_processed: int,
    calls_success: int,
    calls_failed: int,
    transcripts_new: int,
    started_at: str,
    duration_sec: float,
    error_msg: str = "",
    dates_synced: list[str] | None = None,
):
    """Push cron execution log. RAISES on failure."""
    finished_at = datetime.now(timezone.utc).isoformat()
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
    """Query cron_logs for the last successful daily_sync date."""
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
            return rows[0]["started_at"][:10]
    except Exception as exc:
        log.warning("Could not fetch last sync date: %s", exc)
    return None


def compute_dates_to_sync(today_str: str) -> list[str]:
    """Return list of dates to sync, catching up missed days (max 14)."""
    last_sync = get_last_successful_sync_date()
    if last_sync:
        last_dt = datetime.strptime(last_sync, "%Y-%m-%d")
        today_dt = datetime.strptime(today_str, "%Y-%m-%d")
        start_dt = last_dt + timedelta(days=1)
        dates = []
        d = start_dt
        while d <= today_dt:
            dates.append(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
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
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")  # UTC date
    log.info("===== Heidys daily sync started — %s (run %s) =====", today_str, RUN_ID)

    error_msg = ""
    calls_success = 0
    calls_failed = 0
    transcripts_new = 0
    gpu_active = False

    try:
        # 0. Pre-flight checks
        check_disk_space()

        # 1. Determine dates to sync (catch-up if missed days)
        dates_to_sync = compute_dates_to_sync(today_str)
        if len(dates_to_sync) > 1:
            log.info("CATCH-UP: %d days to sync — %s", len(dates_to_sync), ", ".join(dates_to_sync))

        # 2. Fetch calls — GHL PRIMARY (Heidys calls from GHL since March 2026)
        #    JustCall agent 407715 is inactive since March 25 2026
        raw_calls = []
        ghl_calls = []
        for sync_date in dates_to_sync:
            # GHL is the primary source now
            try:
                day_ghl = fetch_ghl_calls_heidys(sync_date)
                log.info("  %s: %d GHL calls found", sync_date, len(day_ghl))
                ghl_calls.extend(day_ghl)
            except Exception as exc:
                log.warning("  GHL fetch failed: %s", exc)

            # JustCall as fallback (in case she switches back)
            day_jc = fetch_justcall_calls(sync_date)
            if day_jc:
                log.info("  %s: %d JustCall calls found", sync_date, len(day_jc))
                raw_calls.extend(day_jc)

        # 2b. Compute funnel stats from ALL calls (before filtering)
        funnel_total = len(raw_calls)
        funnel_answered = sum(1 for c in raw_calls if int(c.get("duration", 0) or 0) > 0)
        funnel_not_answered = funnel_total - funnel_answered
        funnel_short = sum(1 for c in raw_calls if 0 < int(c.get("duration", 0) or 0) < MIN_DURATION_SEC)
        funnel_qualified = sum(1 for c in raw_calls if int(c.get("duration", 0) or 0) >= MIN_DURATION_SEC)
        funnel_durations = [int(c.get("duration", 0) or 0) for c in raw_calls if int(c.get("duration", 0) or 0) >= MIN_DURATION_SEC]
        funnel_avg_dur = sum(funnel_durations) / len(funnel_durations) if funnel_durations else 0
        log.info("Funnel: %d dials, %d answered, %d short, %d qualified", funnel_total, funnel_answered, funnel_short, funnel_qualified)

        # Push funnel per date
        for sync_date in dates_to_sync:
            day_raw = [c for c in raw_calls if (c.get("time") or c.get("time_utc") or "")[:10] == sync_date]
            if not day_raw:
                # Even 0-call days get a row so the dashboard shows the gap
                try:
                    push_call_activity(sync_date, 0, 0, 0, 0, 0, 0, 0)
                except RuntimeError:
                    pass
                continue
            d_total = len(day_raw)
            d_answered = sum(1 for c in day_raw if int(c.get("duration", 0) or 0) > 0)
            d_short = sum(1 for c in day_raw if 0 < int(c.get("duration", 0) or 0) < MIN_DURATION_SEC)
            d_qualified = sum(1 for c in day_raw if int(c.get("duration", 0) or 0) >= MIN_DURATION_SEC)
            d_durs = [int(c.get("duration", 0) or 0) for c in day_raw if int(c.get("duration", 0) or 0) >= MIN_DURATION_SEC]
            d_avg = sum(d_durs) / len(d_durs) if d_durs else 0
            try:
                push_call_activity(sync_date, d_total, d_answered, d_total - d_answered, d_short, d_qualified, 0, d_avg)
            except RuntimeError:
                log.warning("Failed to push call_activity for %s (non-fatal)", sync_date)

        # Combine JustCall + GHL calls, filter for transcription
        all_raw = raw_calls + ghl_calls
        calls = filter_calls(all_raw)
        calls_total = len(calls)

        if not calls:
            log.info("No qualifying calls. Nothing to do.")
            push_coaching_data(today_str, len(all_raw), 0, 0, 0, 0.0)
            push_cron_log("success", 0, 0, 0, 0, started_at, time.time() - t0, dates_synced=dates_to_sync)
            update_nitro_status("idle", 0, 0, False)
            return

        # 3. Enforce batch size limit
        if calls_total > MAX_BATCH_SIZE:
            log.warning(
                "Batch too large (%d calls, max %d). Processing first %d only. "
                "Remaining will be caught up next run.",
                calls_total, MAX_BATCH_SIZE, MAX_BATCH_SIZE,
            )
            calls = calls[:MAX_BATCH_SIZE]
            calls_total = len(calls)

        # 4. Load whisper model
        model, gpu_active = _load_whisper_model()
        update_nitro_status("running", 0, calls_total, gpu_active)

        # 5. Process each call
        new_durations = []  # only durations of NEWLY transcribed calls
        consecutive_failures = 0
        MAX_CONSECUTIVE_FAILURES = 10  # if 10 in a row fail, GPU is probably broken

        for idx, call in enumerate(calls, start=1):
            call_id = str(call.get("id", call.get("call_id", "")))
            duration = int(call.get("duration", 0) or 0)

            if already_transcribed(call_id):
                log.info("[%d/%d] call %s already transcribed — skipping", idx, calls_total, call_id)
                calls_success += 1
                update_nitro_status("running", idx, calls_total, gpu_active, last_file=f"{call_id}.json")
                continue

            try:
                log.info("[%d/%d] Transcribing call %s (%ds)…", idx, calls_total, call_id, duration)
                recording_url = call.get("recording_url", "")

                # GHL calls need special download
                if recording_url.startswith("__GHL__"):
                    ghl_msg_id = recording_url.replace("__GHL__", "")
                    wav_path = download_ghl_recording(ghl_msg_id, WAV_DIR)
                    if not wav_path:
                        log.warning("  GHL recording unavailable for %s — skipping", call_id)
                        calls_failed += 1
                        continue
                    recording_url = wav_path

                transcript, word_count = transcribe_recording(model, recording_url)
                save_transcript(call, transcript, word_count)
                push_call(call, word_count)
                transcripts_new += 1
                calls_success += 1
                new_durations.append(duration)
                consecutive_failures = 0
                log.info("  -> OK (%d words)", word_count)
            except Exception as exc:
                log.error("  !! Error on call %s: %s", call_id, exc, exc_info=True)
                calls_failed += 1
                consecutive_failures += 1

                # If too many consecutive failures, GPU is probably broken
                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    raise RuntimeError(
                        f"ABORTING: {MAX_CONSECUTIVE_FAILURES} consecutive failures. "
                        f"GPU may be in a bad state. Last error: {exc}"
                    )
                continue

            update_nitro_status("running", idx, calls_total, gpu_active, last_file=f"{call_id}.json")

        # 5b. Process GHL fallback calls (if Heidys used GHL)
        ghl_new = 0
        if ghl_calls:
            log.info("=== Processing %d GHL fallback calls ===", len(ghl_calls))
            for ghl_call in ghl_calls:
                ghl_msg_id = ghl_call["id"]
                ghl_transcript_path = os.path.join(TRANSCRIPT_DIR, f"ghl_{ghl_msg_id}.json")
                if os.path.exists(ghl_transcript_path):
                    log.info("  GHL call %s already transcribed", ghl_msg_id)
                    continue
                try:
                    wav_path = download_ghl_recording(ghl_msg_id, WAV_DIR)
                    if not wav_path:
                        log.warning("  GHL recording unavailable for %s", ghl_msg_id)
                        continue
                    transcript_text, word_count = transcribe_recording(model, wav_path)
                    # Save as GHL-sourced transcript
                    ghl_doc = {
                        "id": f"ghl_{ghl_msg_id}",
                        "contact_name": ghl_call.get("contact_name", ""),
                        "contact_number": ghl_call.get("contact_number", ""),
                        "call_time": ghl_call.get("call_time", ""),
                        "duration_s": ghl_call.get("duration", 0),
                        "word_count": word_count,
                        "language": "fr",
                        "transcript": transcript_text,
                        "recording_url": "",
                        "source": "ghl",
                    }
                    tmp = ghl_transcript_path.with_suffix(".json.tmp")
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(ghl_doc, f, ensure_ascii=False, indent=2)
                    tmp.rename(ghl_transcript_path)
                    ghl_new += 1
                    calls_success += 1
                    log.info("  GHL OK: %s (%d words)", ghl_msg_id, word_count)
                except Exception as exc:
                    log.error("  GHL error on %s: %s", ghl_msg_id, exc)
            log.info("GHL fallback done: %d new transcripts", ghl_new)
            transcripts_new += ghl_new

        # 6. Push summary to Supabase — FATAL if fails
        avg_dur = sum(new_durations) / len(new_durations) if new_durations else 0.0
        push_coaching_data(today_str, len(raw_calls) + len(ghl_calls), calls_success, calls_failed, transcripts_new, avg_dur)
        update_nitro_status("idle", calls_total, calls_total, False)

        # 6b. Update call_activity with transcribed count per date
        for sync_date in dates_to_sync:
            day_raw = [c for c in raw_calls if (c.get("time") or c.get("time_utc") or "")[:10] == sync_date]
            d_total = len(day_raw)
            d_answered = sum(1 for c in day_raw if int(c.get("duration", 0) or 0) > 0)
            d_short = sum(1 for c in day_raw if 0 < int(c.get("duration", 0) or 0) < MIN_DURATION_SEC)
            d_qualified = sum(1 for c in day_raw if int(c.get("duration", 0) or 0) >= MIN_DURATION_SEC)
            d_durs = [int(c.get("duration", 0) or 0) for c in day_raw if int(c.get("duration", 0) or 0) >= MIN_DURATION_SEC]
            d_avg = sum(d_durs) / len(d_durs) if d_durs else 0
            # Count transcribed for this date (qualified calls that succeeded)
            d_transcribed = sum(1 for c in day_raw if int(c.get("duration", 0) or 0) >= MIN_DURATION_SEC and c.get("_transcribed"))
            try:
                push_call_activity(sync_date, d_total, d_answered, d_total - d_answered, d_short, d_qualified, calls_success if len(dates_to_sync) == 1 else d_qualified, d_avg)
            except RuntimeError:
                log.warning("Failed to update call_activity transcribed count for %s", sync_date)

        # 7. Haiku scoring + GHL notes (non-fatal)
        haiku_scored = 0
        ghl_notes_posted = 0
        ghl_tasks_created = 0
        try:
            from claude_scoring import score_heidys_call
            log.info("=== Step 7: Haiku scoring + GHL notes ===")

            # Collect all newly transcribed calls
            scored_calls = []
            for sync_date in dates_to_sync:
                for fp in Path(TRANSCRIPT_DIR).glob("*.json"):
                    try:
                        with open(fp, "r", encoding="utf-8") as f:
                            doc = json.load(f)
                        ct = doc.get("call_time", "")
                        if sync_date not in ct:
                            continue
                        if doc.get("ai_scores"):
                            continue  # Already scored
                        if (doc.get("word_count") or 0) < 15:
                            continue
                        scored_calls.append((fp, doc))
                    except Exception:
                        continue

            log.info("  %d calls to score with Haiku", len(scored_calls))

            for fp, doc in scored_calls:
                try:
                    result = score_heidys_call(doc)
                    if not result or not result.get("ai_scores"):
                        continue

                    # Save scores back to JSON
                    doc["ai_scores"] = result["ai_scores"]
                    doc["ai_global_score"] = result["ai_global_score"]
                    doc["coaching_note"] = result.get("coaching_note", "")
                    doc["call_summary"] = result.get("call_summary", "")
                    doc["objections_detected"] = result.get("objections_detected", [])
                    doc["next_step"] = result.get("next_step", "")
                    doc["callback_date"] = result.get("callback_date")

                    tmp = str(fp) + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        json.dump(doc, f, ensure_ascii=False, indent=2)
                    os.replace(tmp, str(fp))
                    haiku_scored += 1

                    # Update Supabase calls table with scores
                    call_id = doc.get("id", "")
                    if call_id:
                        try:
                            supabase_upsert("calls", {
                                "call_id": call_id,
                                "person_id": PERSON_ID,
                                "ai_scores": json.dumps(result["ai_scores"]),
                                "ai_global_score": result["ai_global_score"],
                                "coaching_note": result.get("coaching_note", ""),
                            }, on_conflict="call_id")
                        except Exception as e:
                            log.warning("  Supabase score update failed for %s: %s", call_id, e)

                    # Post note to GHL contact
                    phone = doc.get("contact_number", "")
                    if phone and len(phone) >= 10:
                        try:
                            contact_id = _ghl_find_contact(phone)
                            if contact_id:
                                dur_s = doc.get("duration_s", 0)
                                dur_m = int(dur_s) // 60
                                dur_sec = int(dur_s) % 60
                                score = result["ai_global_score"]
                                summary = result.get("call_summary", "Pas de resume")
                                objections = ", ".join(result.get("objections_detected", [])) or "Aucune"
                                next_step = result.get("next_step", "Non defini")
                                callback = result.get("callback_date")

                                note_body = (
                                    f"📞 Appel du {doc.get('call_time','')[:10]} — {dur_m}m{dur_sec:02d}s — Score: {score}/10\n"
                                    f"Resume: {summary}\n"
                                    f"Objections: {objections}\n"
                                    f"Next step: {next_step}\n"
                                    f"🤖 Auto-genere par le systeme coaching"
                                )
                                _ghl_post_note(contact_id, note_body)
                                ghl_notes_posted += 1

                                # Create callback task if date detected
                                if callback and callback != "null":
                                    contact_name = doc.get("contact_name", "")
                                    _ghl_create_task(
                                        contact_id,
                                        f"Rappel — {contact_name or phone}",
                                        f"Suite a l'appel: {summary}",
                                        callback,
                                    )
                                    ghl_tasks_created += 1
                        except Exception as e:
                            log.warning("  GHL note/task failed for %s: %s", phone, e)

                    log.info("  Scored: %s — %.1f/10", fp.name if hasattr(fp, 'name') else fp, result["ai_global_score"])
                except Exception as e:
                    log.warning("  Haiku scoring failed for %s: %s", fp, e)

            log.info("  Haiku: %d scored, GHL: %d notes, %d tasks", haiku_scored, ghl_notes_posted, ghl_tasks_created)
        except ImportError:
            log.warning("claude_scoring.py not found — skipping Haiku scoring")
        except Exception as e:
            log.warning("Haiku scoring step failed (non-fatal): %s", e)

        elapsed = time.time() - t0
        log.info(
            "===== Sync complete: %d success, %d failed, %d new, %d scored, %d GHL notes (%.1fs) =====",
            calls_success, calls_failed, transcripts_new, haiku_scored, ghl_notes_posted, elapsed,
        )

        # Determine overall status
        if calls_failed > 0 and calls_success == 0:
            status = "error"
            error_msg = f"All {calls_failed} calls failed to transcribe"
        elif calls_failed > 0:
            status = "partial"
            error_msg = f"{calls_failed}/{calls_failed + calls_success} calls failed"
        else:
            status = "success"

        push_cron_log(
            status, calls_success + calls_failed, calls_success, calls_failed,
            transcripts_new, started_at, elapsed,
            error_msg=error_msg, dates_synced=dates_to_sync,
        )

        # Exit with error if ALL calls failed
        if status == "error":
            sys.exit(1)

    except Exception as exc:
        error_msg = str(exc)[:500]
        log.error("Fatal error: %s", exc, exc_info=True)
        elapsed = time.time() - t0
        try:
            push_cron_log(
                "error", calls_success + calls_failed, calls_success, calls_failed,
                transcripts_new, started_at, elapsed, error_msg=error_msg,
            )
            update_nitro_status("error", 0, 0, False)
        except Exception:
            log.error("Could not push error log to Supabase (double failure)")
        sys.exit(1)


if __name__ == "__main__":
    # Support --dates 2026-04-07,2026-04-08,2026-04-09 to force specific dates
    if "--dates" in sys.argv:
        idx = sys.argv.index("--dates")
        if idx + 1 < len(sys.argv):
            forced_dates = sys.argv[idx + 1].split(",")
            # Monkey-patch compute_dates_to_sync to return forced dates
            _orig = compute_dates_to_sync
            compute_dates_to_sync = lambda today: forced_dates
            log.info("FORCED DATES: %s", forced_dates)
    main()
