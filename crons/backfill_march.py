#!/usr/bin/env python3
"""
Backfill Mars complet (1-22 mars 2026) — Transcription + Intégration.
Fetches all calls day-by-day, skips already-transcribed, downloads,
transcribes on GPU, scores, pushes to sac_calls + sac_contacts + metrics.

Resumable: skips existing {call_id}.json files on Nitro.
"""

import json
import logging
import os
import re
import shutil
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from sac_scoring import (
    score_call, global_score, classify_call, detect_agent_from_transcript,
    SAC_DIMENSIONS,
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

ACCOUNTS = {
    "academie": "301418",
    "formateur": "302145",
}
PERSON_IDS = {"hamza": "L3", "lilia": "s2", "sekou": "s3"}
TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts")
LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOCK_FILE = Path(r"C:\Users\user\sac_backfill.lock")

START_DATE = "2026-03-01"
END_DATE = "2026-03-22"  # 23-28 already done
MIN_DURATION = 30

WHISPER_MODEL = "medium"
WHISPER_LANGUAGE = "fr"
WHISPER_BEAM_SIZE = 3

RUN_ID = str(uuid.uuid4())[:8]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("backfill_march")
log.setLevel(logging.INFO)
_fmt = logging.Formatter(f"%(asctime)s [{RUN_ID}] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_ch = logging.StreamHandler(); _ch.setFormatter(_fmt); log.addHandler(_ch)
_fh = logging.FileHandler(str(LOG_DIR / "backfill_march.log"), encoding="utf-8")
_fh.setFormatter(_fmt); log.addHandler(_fh)

# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------

def acquire_lock():
    if LOCK_FILE.exists():
        age = (datetime.now() - datetime.fromtimestamp(LOCK_FILE.stat().st_mtime)).total_seconds() / 3600
        if age > 24:
            LOCK_FILE.unlink()
        else:
            log.error("Lock exists (%.1fh old) — exiting", age); sys.exit(1)
    LOCK_FILE.write_text(f"{RUN_ID}", encoding="utf-8")

def release_lock():
    LOCK_FILE.unlink(missing_ok=True)

# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

def sb_upsert(table, data, on_conflict=""):
    oc = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{oc}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            log.warning("Supabase %s (%d): %s", table, resp.status_code, resp.text[:150])
            return False
        return True
    except Exception as e:
        log.warning("Supabase %s error: %s", table, e)
        return False

def sb_upsert_batch(table, rows, on_conflict="", batch_size=30):
    ok = 0
    for i in range(0, len(rows), batch_size):
        if sb_upsert(table, rows[i:i + batch_size], on_conflict):
            ok += len(rows[i:i + batch_size])
        time.sleep(0.3)
    return ok

def sb_get_existing_call_ids():
    """Get all existing call_ids from sac_calls to avoid re-processing."""
    ids = set()
    url = f"{SUPABASE_URL}/rest/v1/sac_calls?select=call_id"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    offset = 0
    while True:
        resp = requests.get(url, headers={**headers, "Range": f"{offset}-{offset + 999}"}, timeout=30)
        if resp.status_code not in (200, 206):
            break
        rows = resp.json()
        if not rows:
            break
        for r in rows:
            ids.add(str(r["call_id"]))
        if len(rows) < 1000:
            break
        offset += 1000
    return ids

# ---------------------------------------------------------------------------
# JustCall
# ---------------------------------------------------------------------------

def fetch_all_march(agent_id, acct_name):
    """Fetch ALL calls from most recent backward until we pass March 1.
    Returns only March 1-22 calls (filtered client-side)."""
    headers = {"Accept": "application/json", "Authorization": f"{JUSTCALL_API_KEY}:{JUSTCALL_API_SECRET}"}
    march_calls = []
    page = 1
    passed_march = False

    while page <= 60 and not passed_march:
        body = {"from_date": START_DATE, "to_date": END_DATE, "agent_id": agent_id, "per_page": 100, "page": page}
        for attempt in range(3):
            try:
                resp = requests.post(JUSTCALL_API_URL, json=body, headers=headers, timeout=(10, 30))
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < 2:
                    time.sleep(2 ** (attempt + 1))
                else:
                    log.warning("  %s page %d failed: %s", acct_name, page, e)
                    return march_calls

        calls = data.get("data", [])
        if not calls:
            break

        for c in calls:
            t = (c.get("time", "") or "")[:10]
            if t >= START_DATE and t <= END_DATE:
                march_calls.append(c)
            elif t < START_DATE:
                passed_march = True

        if page % 5 == 0:
            latest = calls[-1].get("time", "?")[:10] if calls else "?"
            log.info("    %s page %d: %d calls, oldest=%s, march_so_far=%d",
                     acct_name, page, len(calls), latest, len(march_calls))

        if len(calls) < 100:
            break
        page += 1
        time.sleep(0.5)

    log.info("  %s: %d pages scanned, %d March 1-22 calls found", acct_name, page, len(march_calls))
    return march_calls

def filter_calls(calls):
    return [c for c in calls
            if int(c.get("duration", 0) or 0) >= MIN_DURATION
            and (c.get("recording") or "").strip()]

def assign_person(call, account):
    notes = (call.get("notes", "") or "").lower()
    if "lilia" in notes: return "lilia"
    if "hamza" in notes: return "hamza"
    if "sekou" in notes or notes.strip() == "sk": return "sekou"
    if account == "formateur": return "lilia"
    date_str = (call.get("time", "") or "").split(" ")[0]
    if date_str:
        try:
            if datetime.strptime(date_str, "%Y-%m-%d").weekday() >= 5:
                return "sekou"
        except ValueError:
            pass
    return "hamza"

# ---------------------------------------------------------------------------
# Transcription
# ---------------------------------------------------------------------------

def load_whisper():
    from faster_whisper import WhisperModel
    try:
        m = WhisperModel(WHISPER_MODEL, device="cuda", compute_type="int8_float16")
        log.info("Whisper loaded on CUDA")
    except Exception:
        m = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        log.info("Whisper loaded on CPU")
    return m

def download(url, path):
    for attempt in range(2):
        try:
            resp = requests.get(url, timeout=120, stream=True)
            resp.raise_for_status()
            with open(path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            return True
        except Exception:
            if attempt == 0: time.sleep(2)
    return False

def transcribe(model, audio_path):
    segments, info = model.transcribe(str(audio_path), language=WHISPER_LANGUAGE,
                                       beam_size=WHISPER_BEAM_SIZE, vad_filter=True)
    text = " ".join(seg.text.strip() for seg in segments)
    lang = info.language if hasattr(info, "language") else "fr"
    return text, lang

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()
    log.info("=" * 60)
    log.info("BACKFILL MARS: %s to %s", START_DATE, END_DATE)
    log.info("=" * 60)

    acquire_lock()

    try:
        # Step 0: Get existing call_ids to skip
        log.info("Loading existing call_ids from Supabase...")
        existing_ids = sb_get_existing_call_ids()
        log.info("  %d call_ids already in sac_calls", len(existing_ids))

        # Step 1: Fetch all March 1-22 calls from both accounts
        log.info("")
        log.info("Step 1: Fetching ALL March 1-22 calls from JustCall...")
        all_eligible = []

        for acct_name, agent_id in ACCOUNTS.items():
            log.info("  Fetching %s...", acct_name)
            raw = fetch_all_march(agent_id, acct_name)
            filtered = filter_calls(raw)
            log.info("  %s: %d raw -> %d filtered (duration>=30s + recording)", acct_name, len(raw), len(filtered))

            for c in filtered:
                c["_account"] = acct_name
                c["_person"] = assign_person(c, acct_name)

            # Skip already-processed (in Supabase or on disk)
            new_calls = []
            for c in filtered:
                cid = str(c.get("id", ""))
                if cid in existing_ids:
                    continue
                person = c["_person"]
                json_path = TRANSCRIPT_BASE / person / f"{cid}.json"
                if json_path.exists():
                    continue
                new_calls.append(c)

            log.info("  %s: %d new (skipped %d already processed)", acct_name, len(new_calls), len(filtered) - len(new_calls))
            all_eligible.extend(new_calls)
            time.sleep(2)

        log.info("")
        log.info("Total calls to process: %d", len(all_eligible))

        if not all_eligible:
            log.info("Nothing to do!")
            return

        # Step 2: Load Whisper
        log.info("")
        log.info("Step 2: Loading Whisper model...")
        model = load_whisper()

        # Step 3: Download + Transcribe + Score + Push
        log.info("")
        log.info("Step 3: Processing %d calls...", len(all_eligible))

        processed = 0
        failed = 0
        consecutive_failures = 0
        sb_rows = []
        contact_map = {}

        for i, call in enumerate(all_eligible, 1):
            call_id = str(call.get("id", f"unknown_{i}"))
            person = call["_person"]
            person_id = PERSON_IDS.get(person, "L3")
            acct = call["_account"]

            transcript_dir = TRANSCRIPT_BASE / person
            transcript_dir.mkdir(parents=True, exist_ok=True)
            json_path = transcript_dir / f"{call_id}.json"
            audio_path = transcript_dir / f"{call_id}.wav"

            # Double-check skip
            if json_path.exists():
                processed += 1
                consecutive_failures = 0
                continue

            # Download
            rec_url = call.get("recording", "")
            if not download(rec_url, audio_path):
                failed += 1
                consecutive_failures += 1
                if consecutive_failures >= 10:
                    log.error("10 consecutive failures — aborting")
                    break
                continue

            # Transcribe
            try:
                text, lang = transcribe(model, audio_path)
                category = classify_call(text)
                duration = int(call.get("duration", 0) or 0)

                # Re-attribute by name
                detected = detect_agent_from_transcript(text)
                if detected:
                    person = detected
                    person_id = PERSON_IDS.get(person, person_id)

                # Save JSON
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
                    "agent": person,
                    "account": acct,
                    "notes": call.get("notes", ""),
                    "transcribed_at": datetime.now(timezone.utc).isoformat(),
                }

                tmp = json_path.with_suffix(".json.tmp")
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(transcript_data, f, ensure_ascii=False, indent=2)
                os.replace(str(tmp), str(json_path))

                # Score
                scores = score_call(text, duration)
                gs = global_score(scores)
                contact_num = (call.get("contact_number", "") or "").strip()
                contact_name = (call.get("contact_name", "") or "").strip()

                sb_rows.append({
                    "call_id": call_id,
                    "person_id": person_id,
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
                    "account": acct,
                    "notes": call.get("notes", ""),
                    "detected_agent": detected,
                })

                # Contact tracking
                if contact_num and len(contact_num) >= 7:
                    if contact_num not in contact_map:
                        contact_map[contact_num] = {
                            "contact_number": contact_num,
                            "contact_name": contact_name or None,
                            "first_call_date": call.get("time", "")[:10],
                            "last_call_date": call.get("time", "")[:10],
                            "total_calls": 0,
                            "total_duration_s": 0,
                            "primary_agent": person_id,
                            "languages": [lang] if lang else [],
                        }
                    cm = contact_map[contact_num]
                    cm["total_calls"] += 1
                    cm["total_duration_s"] += duration

                processed += 1
                consecutive_failures = 0

                if i % 10 == 0 or i == len(all_eligible):
                    log.info("  [%d/%d] %s: %d words, %s -> %s (processed=%d, failed=%d)",
                             i, len(all_eligible), call_id, len(text.split()), category, person, processed, failed)

                # Cleanup audio
                try:
                    audio_path.unlink()
                except Exception:
                    pass

            except Exception as exc:
                failed += 1
                consecutive_failures += 1
                log.error("  [%d/%d] Failed %s: %s", i, len(all_eligible), call_id, exc)
                if consecutive_failures >= 10:
                    log.error("10 consecutive failures — aborting")
                    break

            # Batch push every 50 calls
            if len(sb_rows) >= 50:
                log.info("  Pushing batch of %d to sac_calls...", len(sb_rows))
                sb_upsert_batch("sac_calls", sb_rows, on_conflict="call_id")
                sb_rows = []

        # Final push
        if sb_rows:
            log.info("  Pushing final batch of %d to sac_calls...", len(sb_rows))
            sb_upsert_batch("sac_calls", sb_rows, on_conflict="call_id")

        # Push contacts
        if contact_map:
            log.info("  Pushing %d contacts...", len(contact_map))
            sb_upsert_batch("sac_contacts", list(contact_map.values()), on_conflict="contact_number")

        # Step 4: Rebuild weekly metrics for March
        log.info("")
        log.info("Step 4: Rebuilding weekly metrics for March...")

        # Weeks of March: 3/2-3/8, 3/9-3/15, 3/16-3/22
        week_starts = [
            (datetime(2026, 3, 2), datetime(2026, 3, 8)),
            (datetime(2026, 3, 9), datetime(2026, 3, 15)),
            (datetime(2026, 3, 16), datetime(2026, 3, 22)),
        ]

        for ws, we in week_starts:
            ws_str = ws.strftime("%Y-%m-%d")
            we_str = we.strftime("%Y-%m-%d")

            # Query sac_calls for this week
            url = f"{SUPABASE_URL}/rest/v1/sac_calls?call_time=gte.{ws_str}T00:00:00&call_time=lte.{we_str}T23:59:59&select=person_id,scores,duration_s,classification"
            headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
            try:
                resp = requests.get(url, headers=headers, timeout=30)
                if resp.status_code != 200:
                    log.warning("  Failed to query week %s: %d", ws_str, resp.status_code)
                    continue

                calls = resp.json()
                if not calls:
                    continue

                # Group by person
                by_person = defaultdict(list)
                for c in calls:
                    by_person[c["person_id"]].append(c)

                for pid, pcalls in by_person.items():
                    avg_scores = {}
                    for d in SAC_DIMENSIONS:
                        vals = [c["scores"].get(d, 0) for c in pcalls if c.get("scores")]
                        avg_scores[d] = round(sum(vals) / len(vals), 1) if vals else 0.0
                    gs = round(sum(avg_scores.values()) / len(SAC_DIMENSIONS), 1)
                    avg_dur = round(sum(c.get("duration_s", 0) for c in pcalls) / len(pcalls))
                    breakdown = defaultdict(int)
                    for c in pcalls:
                        breakdown[c.get("classification", "autre")] += 1

                    sb_upsert("sac_coaching_metrics", {
                        "person_id": pid,
                        "period_type": "week",
                        "period_start": ws_str,
                        "period_end": we_str,
                        "calls_analyzed": len(pcalls),
                        "avg_duration_s": avg_dur,
                        "scores": avg_scores,
                        "global_score": gs,
                        "score_trend": 0,
                        "call_breakdown": dict(breakdown),
                    }, on_conflict="person_id,period_type,period_start")

                log.info("  Week %s: %d calls across %d agents", ws_str, len(calls), len(by_person))

            except Exception as e:
                log.warning("  Week %s metrics failed: %s", ws_str, e)

        # Summary
        elapsed = round(time.time() - start_time)
        log.info("")
        log.info("=" * 60)
        log.info("BACKFILL COMPLETE in %d seconds (%.1f hours)", elapsed, elapsed / 3600)
        log.info("  Processed: %d", processed)
        log.info("  Failed: %d", failed)
        log.info("  Contacts: %d", len(contact_map))
        log.info("=" * 60)

    except Exception as e:
        log.exception("FATAL: %s", e)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
