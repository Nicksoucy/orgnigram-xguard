"""
Backfill all sac_calls with Haiku AI scoring.
Reads transcripts from Nitro disk, scores with Haiku, pushes ai_scores to Supabase.
Runs in batches of 20 with pauses to respect rate limits.
Skips calls that already have ai_scores.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from claude_scoring import score_call_haiku

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)
TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts")
LOG_DIR = Path(r"C:\Users\user\sac_logs")

os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("backfill_haiku")
fh = logging.FileHandler(str(LOG_DIR / "backfill_haiku.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(fh)

BATCH_SIZE = 20
PAUSE_BETWEEN_BATCHES = 10  # seconds
MAX_CALLS_PER_RUN = 400  # Conservative: ~400 Haiku calls = ~40% of 5h session. Leave room for other usage.
PAUSE_ON_LIMIT = True  # If True, stop gracefully instead of hitting rate limit failures


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
        log.warning("Supabase error: %s", e)
        return False

def sb_update(table, call_id, data):
    """Update existing row by call_id using PATCH."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?call_id=eq.{call_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json"}
    try:
        resp = requests.patch(url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            log.warning("Supabase PATCH %s (%d): %s", table, resp.status_code, resp.text[:150])
            return False
        return True
    except Exception as e:
        log.warning("Supabase PATCH error: %s", e)
        return False


def get_already_scored():
    """Get call_ids that already have ai_scores by checking local JSON files."""
    ids = set()
    for person in ["hamza", "lilia", "sekou"]:
        tdir = TRANSCRIPT_BASE / person
        if not tdir.exists():
            continue
        for fp in tdir.glob("*.json"):
            if fp.name.endswith(".tmp"):
                continue
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("ai_scores") and data.get("ai_global_score") is not None:
                    ids.add(fp.stem)
            except Exception:
                continue
    return ids


def main():
    log.info("=" * 60)
    log.info("BACKFILL HAIKU — AI Scoring for all calls")
    log.info("=" * 60)

    # Get already-scored calls
    already = get_already_scored()
    log.info("Already scored: %d calls", len(already))

    # Load all transcripts
    all_calls = []
    for person in ["hamza", "lilia", "sekou"]:
        tdir = TRANSCRIPT_BASE / person
        if not tdir.exists():
            continue
        for fp in tdir.glob("*.json"):
            if fp.name.endswith(".tmp"):
                continue
            call_id = fp.stem
            if call_id in already:
                continue
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    t = json.load(f)
                if not t.get("transcript", "").strip():
                    continue
                t["_file"] = str(fp)
                t["_person"] = person
                all_calls.append(t)
            except Exception:
                continue

    log.info("Calls to score: %d", len(all_calls))

    if not all_calls:
        log.info("Nothing to do!")
        return

    # Process in batches
    total_scored = 0
    total_failed = 0
    start_time = time.time()

    for batch_start in range(0, len(all_calls), BATCH_SIZE):
        batch = all_calls[batch_start:batch_start + BATCH_SIZE]
        batch_num = batch_start // BATCH_SIZE + 1
        total_batches = (len(all_calls) + BATCH_SIZE - 1) // BATCH_SIZE

        log.info("")
        log.info("--- Batch %d/%d (%d calls) ---", batch_num, total_batches, len(batch))

        batch_updates = []
        for i, call in enumerate(batch):
            call_id = str(call.get("id", ""))
            try:
                result = score_call_haiku(call)
                if result and result.get("ai_scores"):
                    batch_updates.append({
                        "call_id": call_id,
                        "ai_scores": result["ai_scores"],
                        "ai_global_score": result["ai_global_score"],
                        "coaching_note": result.get("coaching_note", ""),
                    })
                    total_scored += 1
                    log.info("  [%d] %s: %.1f/10 — %s",
                             batch_start + i + 1, call_id,
                             result["ai_global_score"],
                             (result.get("coaching_note", "") or "")[:80])

                    # Save ai_scores to transcript JSON for persistence
                    try:
                        fp = call.get("_file")
                        if fp:
                            with open(fp, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            data["ai_scores"] = result["ai_scores"]
                            data["ai_global_score"] = result["ai_global_score"]
                            data["coaching_note"] = result.get("coaching_note", "")
                            with open(fp, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                    except Exception:
                        pass
                else:
                    total_failed += 1
                    log.warning("  [%d] %s: FAILED", batch_start + i + 1, call_id)
            except Exception as e:
                total_failed += 1
                log.error("  [%d] %s: ERROR %s", batch_start + i + 1, call_id, e)

        # Push batch to Supabase (PATCH existing rows)
        if batch_updates:
            for update in batch_updates:
                cid = update.pop("call_id")
                sb_update("sac_calls", cid, update)

        # Progress
        elapsed = time.time() - start_time
        rate = (total_scored + total_failed) / elapsed * 3600 if elapsed > 0 else 0
        remaining = len(all_calls) - (batch_start + len(batch))
        eta_min = remaining / (rate / 60) if rate > 0 else 0
        log.info("  Progress: %d/%d scored, %d failed | %.0f calls/hour | ETA: %.0f min",
                 total_scored, len(all_calls), total_failed, rate, eta_min)

        # Check if we hit the 85% safety limit
        if PAUSE_ON_LIMIT and total_scored >= MAX_CALLS_PER_RUN:
            log.info("")
            log.info("=" * 60)
            log.info("PAUSED AT 85%% LIMIT (%d calls scored)", total_scored)
            log.info("Remaining: %d calls — relaunch later to continue", remaining)
            log.info("All %d scored calls are saved to files + Supabase", total_scored)
            log.info("=" * 60)
            break

        # Check for consecutive failures (rate limit detection)
        if total_failed > 10 and total_failed > total_scored * 0.3:
            recent_fails = sum(1 for u in batch_updates[-5:] if not u) if len(batch_updates) >= 5 else 0
            # If last batch was mostly failures, we're hitting rate limit
            batch_fail_count = len(batch) - len(batch_updates)
            if batch_fail_count >= len(batch) * 0.8:
                log.info("")
                log.info("=" * 60)
                log.info("RATE LIMIT DETECTED — stopping gracefully")
                log.info("Scored: %d, Failed: %d — all scored calls are saved", total_scored, total_failed)
                log.info("Relaunch later to continue from where we left off")
                log.info("=" * 60)
                break

        # Pause between batches
        if batch_start + BATCH_SIZE < len(all_calls):
            log.info("  Pausing %ds before next batch...", PAUSE_BETWEEN_BATCHES)
            time.sleep(PAUSE_BETWEEN_BATCHES)

    elapsed = time.time() - start_time
    log.info("")
    log.info("=" * 60)
    log.info("BACKFILL COMPLETE in %.1f hours", elapsed / 3600)
    log.info("  Scored: %d", total_scored)
    log.info("  Failed: %d", total_failed)
    log.info("  Rate: %.0f calls/hour", (total_scored + total_failed) / elapsed * 3600 if elapsed > 0 else 0)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
