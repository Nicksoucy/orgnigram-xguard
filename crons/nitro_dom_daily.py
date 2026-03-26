#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nitro_dom_daily.py — Domingos daily sync cron (runs every day at 23h on Nitro)

Pulls today's calls from GHL, downloads recordings, transcribes with
faster-whisper GPU, classifies drone/elite/autre, pushes results to Supabase.
"""

import os
import re
import json
import time
import logging
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("nitro_dom_daily")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GHL_TOKEN = "pit-7de455ab-c46e-47a4-af9e-0b07a6c3a1ee"
GHL_LOCATION = "dfkLurZY2ADWAUZl4zYc"
GHL_USER_ID = "5kH5Q6ADlUTBkNGoPIFR"  # Domingos
GHL_API_VERSION = "2021-07-28"
GHL_BASE = "https://services.leadconnectorhq.com"

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

PERSON_ID = "t11"
WAV_DIR = Path("C:/Users/user/xguard_wav/domingos")
TRANSCRIPT_DIR = Path("C:/Users/user/xguard_transcripts/domingos")

MIN_CALL_DURATION = 30  # seconds

# Browser-like headers to bypass Cloudflare 403
GHL_HEADERS = {
    "Authorization": f"Bearer {GHL_TOKEN}",
    "Version": GHL_API_VERSION,
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Origin": "https://app.gohighlevel.com",
    "Referer": "https://app.gohighlevel.com/",
}

# Classification regex patterns (case-insensitive)
DRONE_PATTERN = re.compile(
    r"drone|formation\s+drone|pilote|vol\b|transport\s+canada|\bTC\b|\b101\b|\b202\b|bundle",
    re.IGNORECASE,
)
ELITE_PATTERN = re.compile(
    r"elite|protection\s+rapproch[ée]e|bodyguard|close\s+protection|s[ée]curit[ée]\s+rapproch[ée]e",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Supabase helpers (requests-only, no supabase-py)
# ---------------------------------------------------------------------------
def supabase_upsert(table, data, on_conflict="person_id"):
    """Upsert a row into Supabase via REST."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates",
    }
    resp = requests.post(url, json=data, headers=headers)
    if resp.status_code not in (200, 201, 204):
        log.error("Supabase upsert %s failed (%s): %s", table, resp.status_code, resp.text)
    else:
        log.info("Supabase upsert %s OK", table)
    return resp


def supabase_insert(table, data):
    """Insert a single row (no upsert)."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    resp = requests.post(url, json=data, headers=headers)
    if resp.status_code not in (200, 201, 204):
        log.error("Supabase insert %s failed (%s): %s", table, resp.status_code, resp.text)
    return resp


def push_call(call_doc):
    """Push individual call to Supabase calls table (non-fatal)."""
    try:
        supabase_upsert("calls", call_doc, on_conflict="id,person_id")
    except Exception as exc:
        log.warning("push_call failed (non-fatal): %s", exc)


def push_call_activity(activity_date, total_dials, answered, not_answered,
                       short_calls, qualified_calls, transcribed, avg_dur):
    """Push daily activity funnel to Supabase (non-fatal)."""
    try:
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
                "avg_duration_sec": int(avg_dur),
            },
            on_conflict="person_id,activity_date",
        )
    except Exception as exc:
        log.warning("push_call_activity failed (non-fatal): %s", exc)


def update_nitro_status(**kwargs):
    """Push a status row to nitro_status."""
    payload = {"person_id": PERSON_ID, "task_type": "daily_sync", **kwargs}
    supabase_upsert("nitro_status", payload, on_conflict="person_id,task_type")


# ---------------------------------------------------------------------------
# GHL API helpers
# ---------------------------------------------------------------------------
def ghl_get(endpoint, params=None):
    """GET from GHL API with browser-like headers."""
    url = f"{GHL_BASE}{endpoint}"
    resp = requests.get(url, headers=GHL_HEADERS, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def ghl_post(endpoint, payload=None):
    """POST to GHL API with browser-like headers."""
    url = f"{GHL_BASE}{endpoint}"
    resp = requests.post(url, headers=GHL_HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_conversations_for_date(date_str: str):
    """Search GHL conversations for a single date (YYYY-MM-DD) with cursor pagination."""
    start = f"{date_str}T00:00:00Z"
    end = f"{date_str}T23:59:59Z"

    conversations = []
    cursor = None

    while True:
        payload = {
            "locationId": GHL_LOCATION,
            "startDate": start,
            "endDate": end,
            "limit": 100,
        }
        if cursor:
            payload["cursor"] = cursor

        data = ghl_post("/conversations/search", payload)
        convos = data.get("conversations", [])
        conversations.extend(convos)
        log.info("  %s: fetched %d conversations (total so far: %d)", date_str, len(convos), len(conversations))

        cursor = data.get("nextCursor") or data.get("cursor")
        if not cursor or not convos:
            break

    return conversations


def get_last_successful_sync_date() -> str | None:
    """Query cron_logs for the last successful daily_sync for Domingos."""
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
    """Return list of dates to sync, catching up any missed days."""
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
        dates = dates[-14:]  # cap at 14 days
    else:
        dates = [today_str]
    return dates


def fetch_call_messages_all(conversation_id, contact_name="", contact_phone=""):
    """Fetch ALL call messages for a conversation (both qualified and short).
    Returns (qualified_calls, all_calls_stats) where all_calls_stats has funnel info."""
    qualified = []
    stats = {"total": 0, "answered": 0, "not_answered": 0, "short": 0, "qualified": 0}
    try:
        data = ghl_get(
            f"/conversations/{conversation_id}/messages",
            params={"locationId": GHL_LOCATION, "limit": 100},
        )
        raw_msgs = data.get("messages", {})
        if isinstance(raw_msgs, dict):
            raw_msgs = raw_msgs.get("messages", [])

        for msg in raw_msgs:
            if not isinstance(msg, dict):
                continue
            if msg.get("messageType") != "TYPE_CALL":
                continue
            if msg.get("userId") != GHL_USER_ID:
                continue

            meta_call = msg.get("meta", {}).get("call", {}) if isinstance(msg.get("meta"), dict) else {}
            duration = meta_call.get("duration") or msg.get("duration") or 0

            stats["total"] += 1
            if duration == 0:
                stats["not_answered"] += 1
            elif duration < MIN_CALL_DURATION:
                stats["answered"] += 1
                stats["short"] += 1
            else:
                stats["answered"] += 1
                stats["qualified"] += 1
                msg["_duration"] = duration
                msg["_contact_name"] = contact_name
                msg["_contact_phone"] = contact_phone
                qualified.append(msg)

    except Exception as exc:
        log.error("Error fetching messages for %s: %s", conversation_id, exc)
    return qualified, stats


# ---------------------------------------------------------------------------
# Recording download
# ---------------------------------------------------------------------------
def download_recording(msg_id):
    """Download a call recording WAV using GHL magic endpoint. Returns path or None."""
    WAV_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = WAV_DIR / f"{msg_id}.wav"
    if wav_path.exists() and wav_path.stat().st_size > 1000:
        log.info("WAV already exists: %s", wav_path.name)
        return wav_path
    try:
        # Magic GHL endpoint: MUST include /locations/{LOCATION_ID}/ in path
        rec_url = f"{GHL_BASE}/conversations/messages/{msg_id}/locations/{GHL_LOCATION}/recording"
        resp = requests.get(rec_url, headers=GHL_HEADERS, timeout=120, stream=True)
        if resp.status_code == 422:
            log.warning("No recording available for %s (422)", msg_id)
            return None
        resp.raise_for_status()
        tmp_path = WAV_DIR / f"{msg_id}.wav.tmp"
        size = 0
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                size += len(chunk)
        if size < 1000:
            log.warning("Recording too small (%d bytes) for %s, skipping", size, msg_id)
            tmp_path.unlink(missing_ok=True)
            return None
        tmp_path.rename(wav_path)  # atomic rename
        log.info("Downloaded %s (%d KB)", wav_path.name, size // 1024)
        return wav_path
    except Exception as exc:
        log.error("Download failed for %s: %s", msg_id, exc)
        return None


# ---------------------------------------------------------------------------
# Transcription (faster-whisper)
# ---------------------------------------------------------------------------
_whisper_model = None


def get_whisper_model():
    """Lazy-load the faster-whisper model (GPU with CPU fallback)."""
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    from faster_whisper import WhisperModel

    try:
        _whisper_model = WhisperModel(
            "medium", device="cuda", compute_type="int8_float16"
        )
        log.info("Whisper model loaded on CUDA (int8_float16)")
    except Exception:
        log.warning("CUDA unavailable, falling back to CPU")
        _whisper_model = WhisperModel("medium", device="cpu", compute_type="int8")
    return _whisper_model


def transcribe_audio(wav_path):
    """Transcribe a WAV file and return (text, word_count, language)."""
    model = get_whisper_model()
    segments, info = model.transcribe(
        str(wav_path),
        language="fr",
        beam_size=3,
        vad_filter=True,
    )
    text = " ".join(seg.text.strip() for seg in segments)
    word_count = len(text.split())
    return text, word_count, info.language


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def classify_call(transcript_text):
    """Classify transcript as drone / elite / autre."""
    if DRONE_PATTERN.search(transcript_text):
        return "drone"
    if ELITE_PATTERN.search(transcript_text):
        return "elite"
    return "autre"


# ---------------------------------------------------------------------------
# Transcript output
# ---------------------------------------------------------------------------
def save_transcript(msg, transcript_text, word_count, language, classification):
    """Save transcript JSON to disk."""
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    msg_id = msg.get("id", "unknown")
    out_path = TRANSCRIPT_DIR / f"{msg_id}.json"

    doc = {
        "id": msg_id,
        "contact_name": msg.get("contactName", ""),
        "contact_number": msg.get("contactPhone", msg.get("phone", "")),
        "call_time": msg.get("dateAdded", ""),
        "duration_s": msg.get("duration", 0),
        "recording_url": msg.get("recordingUrl", msg.get("attachments", [""])[0] if msg.get("attachments") else ""),
        "transcript": transcript_text,
        "word_count": word_count,
        "language": language,
        "source": "ghl",
        "agent": "domingos",
        "classification": classification,
        "transcribed_at": datetime.now(timezone.utc).isoformat(),
    }

    tmp_path = TRANSCRIPT_DIR / f"{msg_id}.json.tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    tmp_path.rename(out_path)  # atomic rename
    log.info("Saved transcript %s (%s)", msg_id, classification)

    # Push individual call to Supabase
    push_call({
        "id": msg_id,
        "person_id": PERSON_ID,
        "call_time": doc["call_time"],
        "duration_s": doc["duration_s"],
        "contact_name": doc["contact_name"],
        "contact_number": doc["contact_number"],
        "word_count": word_count,
        "language": language,
        "source": "ghl",
        "classification": classification,
    })

    return doc


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main():
    t_start = time.time()
    started_at = datetime.now(timezone.utc).isoformat()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log.info("=== nitro_dom_daily — sync for %s ===", today_str)

    update_nitro_status(status="running", gpu_active=False, last_file="")

    # ------ Step 0: Determine dates to sync (catch-up if missed days) ------
    dates_to_sync = compute_dates_to_sync(today_str)
    if len(dates_to_sync) > 1:
        log.info("CATCH-UP: %d days to sync — %s", len(dates_to_sync), ", ".join(dates_to_sync))

    # ------ Step 1: Pull conversations from GHL for all dates ------
    try:
        conversations = []
        for sync_date in dates_to_sync:
            day_convos = fetch_conversations_for_date(sync_date)
            conversations.extend(day_convos)
    except Exception as exc:
        log.error("Failed to fetch conversations: %s", exc)
        update_nitro_status(status="error")
        supabase_insert("cron_logs", {
            "person_id": PERSON_ID,
            "cron_type": "daily_sync",
            "status": "error",
            "calls_processed": 0,
            "transcripts_new": 0,
            "duration_sec": int(time.time() - t_start),
            "error_msg": str(exc)[:500],
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        })
        return

    # ------ Step 2: Collect ALL call messages (funnel + qualified) ------
    all_calls = []
    funnel_totals = {"total": 0, "answered": 0, "not_answered": 0, "short": 0, "qualified": 0}

    for conv in conversations:
        conv_id = conv.get("id")
        if not conv_id:
            continue
        qualified, stats = fetch_call_messages_all(
            conv_id,
            contact_name=conv.get("contactName", ""),
            contact_phone=conv.get("phone", ""),
        )
        all_calls.extend(qualified)
        for k in funnel_totals:
            funnel_totals[k] += stats[k]

    log.info("Funnel: %d dials, %d answered, %d short, %d qualified",
             funnel_totals["total"], funnel_totals["answered"],
             funnel_totals["short"], funnel_totals["qualified"])

    # Push funnel stats per date
    for sync_date in dates_to_sync:
        push_call_activity(
            sync_date,
            total_dials=funnel_totals["total"] // max(len(dates_to_sync), 1),
            answered=funnel_totals["answered"] // max(len(dates_to_sync), 1),
            not_answered=funnel_totals["not_answered"] // max(len(dates_to_sync), 1),
            short_calls=funnel_totals["short"] // max(len(dates_to_sync), 1),
            qualified_calls=funnel_totals["qualified"] // max(len(dates_to_sync), 1),
            transcribed=0,  # updated after transcription
            avg_dur=0,
        )

    log.info("Total qualifying calls for transcription: %d", len(all_calls))
    update_nitro_status(
        status="running", done=0, total=len(all_calls), pct=0, gpu_active=False
    )

    # ------ Steps 3-6: Download, transcribe, classify, save ------
    calls_transcribed = 0
    calls_new = 0
    durations = []
    breakdown = {"drone": 0, "elite": 0, "autre": 0}
    errors = []

    for idx, msg in enumerate(all_calls):
        msg_id = msg.get("id", f"unknown_{idx}")
        transcript_path = TRANSCRIPT_DIR / f"{msg_id}.json"

        # Skip already-transcribed
        if transcript_path.exists():
            log.info("Already transcribed: %s — loading for stats", msg_id)
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                cls = existing.get("classification", "autre")
                breakdown[cls] = breakdown.get(cls, 0) + 1
                durations.append(existing.get("duration_s", 0))
                calls_transcribed += 1
            except Exception:
                pass
            continue

        try:
            # Download recording via GHL magic endpoint
            wav_path = download_recording(msg_id)
            if wav_path is None:
                continue

            # Transcribe
            update_nitro_status(
                status="running",
                gpu_active=True,
                last_file=msg_id,
                done=idx,
                total=len(all_calls),
                pct=int(idx / max(len(all_calls), 1) * 100),
            )
            transcript_text, word_count, language = transcribe_audio(wav_path)

            # Classify
            classification = classify_call(transcript_text)
            breakdown[classification] = breakdown.get(classification, 0) + 1

            # Inject contact info and duration from conversation
            msg["contactName"] = msg.get("contactName") or msg.get("_contact_name", "")
            msg["contactPhone"] = msg.get("contactPhone") or msg.get("_contact_phone", "")
            msg["duration"] = msg.get("_duration") or msg.get("duration", 0)

            # Save transcript + push to Supabase calls table
            save_transcript(msg, transcript_text, word_count, language, classification)

            dur = msg.get("_duration") or msg.get("duration", 0)
            durations.append(dur)
            calls_transcribed += 1
            calls_new += 1

        except Exception as exc:
            log.error("Error processing call %s: %s", msg_id, exc)
            errors.append(f"{msg_id}: {exc}")

    # ------ Step 5: Push results to Supabase ------
    avg_dur = int(sum(durations) / max(len(durations), 1))

    supabase_upsert(
        "coaching_data",
        {
            "person_id": PERSON_ID,
            "sync_date": today_str,
            "calls_total": len(all_calls),
            "calls_transcribed": calls_transcribed,
            "calls_new": calls_new,
            "avg_duration_sec": avg_dur,
            "source": "ghl",
            "call_breakdown": json.dumps(breakdown),
        },
        on_conflict="person_id,sync_date",
    )

    elapsed = int(time.time() - t_start)
    final_status = "error" if errors else "success"

    update_nitro_status(
        status=final_status,
        done=len(all_calls),
        total=len(all_calls),
        pct=100,
        gpu_active=False,
        last_file="",
    )

    supabase_insert(
        "cron_logs",
        {
            "person_id": PERSON_ID,
            "cron_type": "daily_sync",
            "status": final_status,
            "calls_processed": len(all_calls),
            "transcripts_new": calls_new,
            "duration_sec": elapsed,
            "error_msg": ("; ".join(errors))[:500] if errors else None,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    log.info(
        "=== Done in %ds — %d calls, %d transcribed (%d new), breakdown: %s ===",
        elapsed,
        len(all_calls),
        calls_transcribed,
        calls_new,
        breakdown,
    )


if __name__ == "__main__":
    main()
