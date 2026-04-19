"""
Generate the Opus coaching report using 1,560 AI-scored calls.
Prepares data summary + best/worst transcripts per agent, sends to Opus.
"""

import json
import logging
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from claude_scoring import generate_opus_report
from sac_scoring import SAC_DIMENSIONS, classify_call, detect_objections_normalized

os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts")
REPORT_DIR = Path(r"C:\Users\user\sac_reports")
PERSON_IDS = {"hamza": "L3", "lilia": "s2", "sekou": "s3"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("opus_report")


def load_scored_calls():
    """Load all calls that have ai_global_score from JSON files."""
    buckets = {"hamza": [], "lilia": [], "sekou": []}

    for person in ["hamza", "lilia", "sekou"]:
        tdir = TRANSCRIPT_BASE / person
        if not tdir.exists():
            continue
        for fp in tdir.glob("*.json"):
            if fp.name.endswith(".tmp"):
                continue
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    t = json.load(f)
                if t.get("ai_global_score") is not None:
                    buckets[person].append(t)
            except Exception:
                continue

    return buckets


def prepare_opus_data(buckets):
    """Prepare summary data for Opus."""
    data = {"period": "Mars 2026", "agents": {}}

    for person in ["hamza", "lilia", "sekou"]:
        calls = buckets[person]
        if not calls:
            continue

        name = person.capitalize()
        pid = PERSON_IDS[person]

        # Sort by AI score
        sorted_calls = sorted(calls, key=lambda c: c.get("ai_global_score", 0), reverse=True)

        # Average score
        scores = [c["ai_global_score"] for c in calls]
        avg_score = round(sum(scores) / len(scores), 1)

        # Duration stats
        durs = [c.get("duration_s", 0) for c in calls]
        avg_dur = round(sum(durs) / len(durs) / 60, 1) if durs else 0

        # Categories
        cats = defaultdict(int)
        for c in calls:
            cats[classify_call(c.get("transcript", ""))] += 1

        # Objections
        obj_counts = defaultdict(int)
        for c in calls:
            for cat, raw in detect_objections_normalized(c.get("transcript", "")):
                obj_counts[cat] += 1

        # Score distribution
        dist = {"excellent_7plus": 0, "bon_5_7": 0, "moyen_3_5": 0, "faible_0_3": 0}
        for s in scores:
            if s >= 7: dist["excellent_7plus"] += 1
            elif s >= 5: dist["bon_5_7"] += 1
            elif s >= 3: dist["moyen_3_5"] += 1
            else: dist["faible_0_3"] += 1

        # AI dimension scores (from calls that have full ai_scores)
        dim_avgs = {}
        for dim in SAC_DIMENSIONS:
            vals = [c.get("ai_scores", {}).get(dim) for c in calls if c.get("ai_scores", {}).get(dim) is not None]
            dim_avgs[dim] = round(sum(vals) / len(vals), 1) if vals else None

        # Best 5 calls with transcript excerpts
        best = []
        for c in sorted_calls[:5]:
            text = c.get("transcript", "")
            best.append({
                "score": c.get("ai_global_score", 0),
                "contact": c.get("contact_name", "Inconnu"),
                "duration_min": round(c.get("duration_s", 0) / 60, 1),
                "classification": classify_call(text),
                "coaching_note": c.get("coaching_note", ""),
                "transcript_start": " ".join(text.split()[:100]),
                "transcript_end": " ".join(text.split()[-100:]) if len(text.split()) > 100 else "",
            })

        # Worst 5
        worst = []
        for c in sorted_calls[-5:]:
            text = c.get("transcript", "")
            worst.append({
                "score": c.get("ai_global_score", 0),
                "contact": c.get("contact_name", "Inconnu"),
                "duration_min": round(c.get("duration_s", 0) / 60, 1),
                "classification": classify_call(text),
                "coaching_note": c.get("coaching_note", ""),
                "transcript_start": " ".join(text.split()[:100]),
            })

        data["agents"][name] = {
            "person_id": pid,
            "total_calls": len(calls),
            "avg_ai_score": avg_score,
            "avg_duration_min": avg_dur,
            "dimension_scores": dim_avgs,
            "score_distribution": dist,
            "categories": dict(cats),
            "top_objections": dict(sorted(obj_counts.items(), key=lambda x: -x[1])[:7]),
            "best_calls": best,
            "worst_calls": worst,
        }

    return data


def main():
    log.info("=" * 60)
    log.info("OPUS REPORT GENERATION")
    log.info("=" * 60)

    # Load scored calls
    log.info("Loading scored calls...")
    buckets = load_scored_calls()
    total = sum(len(v) for v in buckets.values())
    log.info("  Hamza: %d, Lilia: %d, Sekou: %d = %d total",
             len(buckets["hamza"]), len(buckets["lilia"]), len(buckets["sekou"]), total)

    # Prepare data
    log.info("Preparing Opus data...")
    data = prepare_opus_data(buckets)

    # Save data for reference
    data_path = REPORT_DIR / "opus_data.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    with open(data_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.info("Data saved: %s", data_path)

    # Call Opus
    log.info("Calling Opus for coaching report...")
    start = time.time()
    report_text = generate_opus_report(data)
    elapsed = time.time() - start
    log.info("Opus responded in %.0f seconds (%d chars)", elapsed, len(report_text))

    # Save report
    report_path = REPORT_DIR / "rapport_opus_mars_2026.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    log.info("Report saved: %s", report_path)

    # Print it
    print("\n" + "=" * 60)
    print("RAPPORT OPUS — MARS 2026")
    print("=" * 60)
    print(report_text)

    log.info("")
    log.info("DONE!")


if __name__ == "__main__":
    main()
