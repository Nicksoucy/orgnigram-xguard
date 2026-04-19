"""
Recover 1,359 Haiku scores from the backfill log file.
Parse call_id + global_score + coaching_note from each log line.
Save to transcript JSON files + PATCH to Supabase.
"""

import json
import logging
import os
import re
import sys
import time
from pathlib import Path

import requests

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)
LOG_FILE = Path(r"C:\Users\user\sac_logs\backfill_haiku.log")
TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("recover")

# Pattern: [N] call_id: score/10 — coaching_note
# Example: [42] 352005004: 4.8/10 — Se présenter clairement...
SCORE_PATTERN = re.compile(r'\[(\d+)\]\s+(\d+):\s+([\d.]+)/10\s+.*?\s+(.*)')


def sb_patch(call_id, data):
    url = f"{SUPABASE_URL}/rest/v1/sac_calls?call_id=eq.{call_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json"}
    try:
        resp = requests.patch(url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            return False
        return True
    except Exception:
        return False


def main():
    log.info("=" * 60)
    log.info("RECOVERING SCORES FROM LOG FILE")
    log.info("=" * 60)

    # Read log file
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Parse scores from the FIRST run (2026-03-29 14:xx to 21:xx)
    scores = []
    for line in lines:
        if "2026-03-29" not in line:
            continue
        if "/10" not in line:
            continue
        if "FAILED" in line:
            continue

        # Match pattern: [N] call_id: score/10
        m = re.search(r'\[(\d+)\]\s+(\d+):\s+([\d.]+)/10', line)
        if m:
            idx = int(m.group(1))
            call_id = m.group(2)
            global_score = float(m.group(3))

            # Extract coaching note after the dash
            note_match = re.search(r'/10\s+[^\w]*(.*)', line)
            coaching_note = ""
            if note_match:
                coaching_note = note_match.group(1).strip()
                # Clean encoding artifacts
                coaching_note = coaching_note.replace("\x00", "").strip()

            scores.append({
                "call_id": call_id,
                "ai_global_score": global_score,
                "coaching_note": coaching_note[:200],
            })

    log.info("Parsed %d scores from log", len(scores))

    if not scores:
        log.info("Nothing to recover!")
        return

    # Build call_id -> file path mapping
    file_map = {}
    for person in ["hamza", "lilia", "sekou"]:
        tdir = TRANSCRIPT_BASE / person
        if not tdir.exists():
            continue
        for fp in tdir.glob("*.json"):
            if fp.name.endswith(".tmp"):
                continue
            file_map[fp.stem] = str(fp)

    log.info("Found %d transcript files", len(file_map))

    # Save scores to files + push to Supabase
    saved_files = 0
    pushed_sb = 0

    for i, s in enumerate(scores):
        call_id = s["call_id"]

        # Save to file
        fp = file_map.get(call_id)
        if fp:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Only save if not already scored
                if not data.get("ai_global_score"):
                    data["ai_global_score"] = s["ai_global_score"]
                    data["coaching_note"] = s["coaching_note"]
                    # We don't have individual dimension scores from the log,
                    # but we have the global score and coaching note
                    with open(fp, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    saved_files += 1
            except Exception as e:
                log.warning("  File save failed for %s: %s", call_id, e)

        # Push to Supabase via PATCH
        if sb_patch(call_id, {
            "ai_global_score": s["ai_global_score"],
            "coaching_note": s["coaching_note"],
        }):
            pushed_sb += 1

        if (i + 1) % 100 == 0:
            log.info("  %d/%d processed (files=%d, supabase=%d)", i + 1, len(scores), saved_files, pushed_sb)
            time.sleep(0.5)

    log.info("")
    log.info("=" * 60)
    log.info("RECOVERY COMPLETE")
    log.info("  Scores parsed: %d", len(scores))
    log.info("  Files updated: %d", saved_files)
    log.info("  Supabase pushed: %d", pushed_sb)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
