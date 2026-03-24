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


def fetch_todays_conversations():
    """Search GHL conversations for today with cursor pagination."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    start = f"{today}T00:00:00Z"
    end = f"{today}T23:59:59Z"

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
        log.info("Fetched %d conversations (total so far: %d)", len(convos), len(conversations))

        cursor = data.get("nextCursor") or data.get("cursor")
        if not cursor or not convos:
            break

    return conversations


def fetch_call_messages(conversation_id):
    """Fetch messages for a conversation and filter for Domingos's calls >= 30s."""
    calls = []
    try:
        data = ghl_get(
            f"/conversations/{conversation_id}/messages",
            params={"locationId": GHL_LOCATION, "limit": 100},
        )
        for msg in data.get("messages", []):
            if msg.get("messageType") != "TYPE_CALL":
                continue
            if msg.get("userId") != GHL_USER_ID:
                continue
            duration = msg.get("duration", 0)
            if duration < MIN_CALL_DURATION:
                continue
            calls.append(msg)
    except Exception as exc:
        log.error("Error fetching messages for %s: %s", conversation_id, exc)
    return calls


# ---------------------------------------------------------------------------
# Recording download
# ---------------------------------------------------------------------------
def download_recording(recording_url, msg_id):
    """Download a call recording WAV. Returns path or None."""
    WAV_DIR.mkdir(parents=True, exist_ok=True)
    wav_path = WAV_DIR / f"{msg_id}.wav"
    if wav_path.exists():
        log.info("WAV already exists: %s", wav_path.name)
        return wav_path
    try:
        resp = requests.get(recording_url, timeout=120, stream=True)
        resp.raise_for_status()
        with open(wav_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        log.info("Downloaded %s", wav_path.name)
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

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    log.info("Saved transcript %s (%s)", msg_id, classification)
    return doc


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def main():
    t_start = time.time()
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log.info("=== nitro_dom_daily — sync for %s ===", today_str)

    update_nitro_status(status="running", gpu_active=False, last_file="")

    # ------ Step 1: Pull conversations from GHL ------
    try:
        conversations = fetch_todays_conversations()
    except Exception as exc:
        log.error("Failed to fetch conversations: %s", exc)
        update_nitro_status(status="error")
        supabase_upsert("cron_logs", {
            "person_id": PERSON_ID,
            "cron_type": "daily_sync",
            "status": "error",
            "calls_processed": 0,
            "transcripts_new": 0,
            "duration_sec": int(time.time() - t_start),
            "error_msg": str(exc),
        }, on_conflict="person_id,cron_type")
        return

    # ------ Step 2: Collect qualifying call messages ------
    all_calls = []
    for conv in conversations:
        conv_id = conv.get("id")
        if not conv_id:
            continue
        calls = fetch_call_messages(conv_id)
        for call in calls:
            call["_contact_name"] = conv.get("contactName", "")
            call["_contact_phone"] = conv.get("phone", "")
        all_calls.extend(calls)

    log.info("Total qualifying calls: %d", len(all_calls))
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
            # Recording URL
            rec_url = msg.get("recordingUrl", "")
            if not rec_url:
                attachments = msg.get("attachments", [])
                rec_url = attachments[0] if attachments else ""
            if not rec_url:
                log.warning("No recording URL for %s, skipping", msg_id)
                continue

            # Download
            wav_path = download_recording(rec_url, msg_id)
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

            # Inject contact info from conversation
            msg["contactName"] = msg.get("contactName") or msg.get("_contact_name", "")
            msg["contactPhone"] = msg.get("contactPhone") or msg.get("_contact_phone", "")

            # Save transcript
            save_transcript(msg, transcript_text, word_count, language, classification)

            dur = msg.get("duration", 0)
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
    final_status = "error" if errors else "done"

    update_nitro_status(
        status=final_status,
        done=len(all_calls),
        total=len(all_calls),
        pct=100,
        gpu_active=False,
        last_file="",
    )

    supabase_upsert(
        "cron_logs",
        {
            "person_id": PERSON_ID,
            "cron_type": "daily_sync",
            "status": final_status,
            "calls_processed": len(all_calls),
            "transcripts_new": calls_new,
            "duration_sec": elapsed,
            "error_msg": "; ".join(errors) if errors else None,
        },
        on_conflict="person_id,cron_type",
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
