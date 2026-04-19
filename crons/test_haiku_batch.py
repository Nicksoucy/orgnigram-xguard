"""Test Haiku scoring on 5 calls to measure time + token usage."""
import json
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from claude_scoring import score_call_haiku, call_claude

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("test_haiku")

# Load 5 sample transcripts from Nitro
TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts\sekou")

def main():
    # Get 5 transcript files
    files = sorted(TRANSCRIPT_BASE.glob("*.json"))[:5]
    log.info("Testing with %d calls", len(files))

    calls = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            calls.append(json.load(f))

    # Score each one sequentially (to measure individual time)
    total_start = time.time()
    results = []

    for i, call in enumerate(calls):
        start = time.time()
        log.info("")
        log.info("--- Call %d/%d: %s (%d words, %ds) ---",
                 i + 1, len(calls), call.get("id", "?"),
                 len((call.get("transcript", "") or "").split()),
                 call.get("duration_s", 0))

        result = score_call_haiku(call)
        elapsed = time.time() - start

        if result:
            log.info("  AI scores: %s", json.dumps(result.get("ai_scores", {})))
            log.info("  AI global: %s", result.get("ai_global_score"))
            log.info("  Coaching: %s", result.get("coaching_note", "")[:100])
            log.info("  Time: %.1fs", elapsed)

            # Compare with regex
            from sac_scoring import score_call, global_score
            text = call.get("transcript", "")
            dur = call.get("duration_s", 0)
            regex_scores = score_call(text, dur)
            regex_global = global_score(regex_scores)
            log.info("  Regex global: %s vs AI global: %s (diff: %+.1f)",
                     regex_global, result["ai_global_score"],
                     result["ai_global_score"] - regex_global)
        else:
            log.warning("  FAILED - no result")
            elapsed = time.time() - start

        results.append({"call_id": call.get("id"), "result": result, "time_sec": round(elapsed, 1)})

    total_elapsed = time.time() - total_start
    log.info("")
    log.info("=" * 60)
    log.info("DONE — %d calls in %.1f seconds (avg %.1fs/call)", len(calls), total_elapsed, total_elapsed / len(calls))
    successes = sum(1 for r in results if r["result"])
    log.info("Success rate: %d/%d", successes, len(calls))
    log.info("=" * 60)


if __name__ == "__main__":
    main()
