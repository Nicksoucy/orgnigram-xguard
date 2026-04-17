"""
Re-score calls that are missing ai_global_score.
Run: python rescore_missing.py [YYYY-MM-DD]
"""

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

import requests
from claude_scoring import score_call_haiku, CLAUDE_EXE

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

TRANSCRIPT_BASE = Path("C:/Users/user/xguard_transcripts")
PERSON_TO_DIR = {"L3": "hamza", "s2": "lilia", "s3": "sekou"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("rescore")


def sb_get(path):
    r = requests.get(
        f"{SUPABASE_URL}/rest/v1/{path}",
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
        timeout=30,
    )
    return r.json() if r.status_code == 200 else []


def sb_patch(call_id, data):
    r = requests.patch(
        f"{SUPABASE_URL}/rest/v1/sac_calls?call_id=eq.{call_id}",
        headers={
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
        json=data,
        timeout=30,
    )
    return r.status_code in (200, 204)


def main():
    date_filter = ""
    if len(sys.argv) > 1:
        date_str = sys.argv[1]
        date_filter = f"&call_time=gte.{date_str}T00:00:00&call_time=lt.{date_str}T23:59:59"

    log.info("Using Claude: %s", CLAUDE_EXE)

    # Fetch calls missing ai_global_score
    path = (
        "sac_calls?ai_global_score=is.null"
        "&select=call_id,person_id,contact_name,call_time,duration_s"
        f"{date_filter}"
        "&order=call_time.desc&limit=500"
    )
    calls = sb_get(path)
    log.info("Found %d calls missing AI scores", len(calls))
    if not calls:
        return

    scored_ok = 0
    scored_failed = 0

    for i, call in enumerate(calls, 1):
        call_id = str(call["call_id"])
        pid = call.get("person_id", "")
        person_dir = PERSON_TO_DIR.get(pid)
        if not person_dir:
            continue

        json_path = TRANSCRIPT_BASE / person_dir / f"{call_id}.json"
        if not json_path.exists():
            log.warning("[%d/%d] %s: transcript missing at %s", i, len(calls), call_id, json_path)
            continue

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                t = json.load(f)
        except Exception as e:
            log.warning("[%d/%d] %s: load error: %s", i, len(calls), call_id, e)
            continue

        if not t.get("transcript"):
            continue

        try:
            result = score_call_haiku(t)
        except Exception as e:
            log.error("[%d/%d] %s: score error: %s", i, len(calls), call_id, e)
            scored_failed += 1
            continue

        if not result or not result.get("ai_scores"):
            log.warning("[%d/%d] %s: empty result", i, len(calls), call_id)
            scored_failed += 1
            continue

        # Update transcript file
        t["ai_scores"] = result["ai_scores"]
        t["ai_global_score"] = result["ai_global_score"]
        t["coaching_note"] = result.get("coaching_note", "")
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(t, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

        # Patch Supabase
        ok = sb_patch(call_id, {
            "ai_scores": result["ai_scores"],
            "ai_global_score": result["ai_global_score"],
            "coaching_note": result.get("coaching_note", ""),
        })
        if ok:
            scored_ok += 1
            log.info("[%d/%d] %s [%s]: %.1f/10 %s",
                     i, len(calls), call_id, pid,
                     result["ai_global_score"],
                     (call.get("contact_name") or "")[:30])
        else:
            scored_failed += 1

    log.info("")
    log.info("DONE: %d scored, %d failed", scored_ok, scored_failed)


if __name__ == "__main__":
    main()
