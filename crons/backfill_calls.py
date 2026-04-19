#!/usr/bin/env python3
"""
One-time backfill: reads all existing transcript JSONs from Nitro,
scores them, pushes to sac_calls + sac_contacts + sac_coaching_metrics.
"""

import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests

# Add crons dir to path for sac_scoring import
sys.path.insert(0, str(Path(__file__).parent))
from sac_scoring import (
    score_call, global_score, classify_call, detect_agent_from_transcript,
    detect_objections_normalized, SAC_DIMENSIONS,
)

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)
PERSON_IDS = {"hamza": "L3", "lilia": "s2", "sekou": "s3"}
TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("backfill")

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def sb_upsert(table, data, on_conflict=""):
    oc = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{oc}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
    resp = requests.post(url, json=data, headers=headers, timeout=30)
    if resp.status_code >= 400:
        log.error("Supabase %s failed (%d): %s", table, resp.status_code, resp.text[:200])
        return False
    return True

def sb_upsert_batch(table, rows, on_conflict="", batch_size=50):
    ok = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        if sb_upsert(table, batch, on_conflict):
            ok += len(batch)
        time.sleep(0.3)
    return ok

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("BACKFILL — Loading all transcripts")
    log.info("=" * 60)

    all_calls = []
    contacts = {}  # contact_number -> contact data

    for person in ["hamza", "lilia", "sekou"]:
        tdir = TRANSCRIPT_BASE / person
        if not tdir.exists():
            log.warning("Dir not found: %s", tdir)
            continue

        files = list(tdir.glob("*.json"))
        log.info("%s: %d transcript files", person, len(files))

        for fp in files:
            if fp.name.endswith(".tmp"):
                continue
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    t = json.load(f)
            except Exception:
                continue

            text = t.get("transcript", "") or ""
            if not text.strip():
                continue

            call_id = str(t.get("id", fp.stem))
            dur = int(t.get("duration_s", 0) or 0)
            call_time_str = t.get("call_time", "")

            # Parse call_time
            call_time = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S%z"):
                try:
                    call_time = datetime.strptime(call_time_str, fmt)
                    break
                except ValueError:
                    continue
            if call_time is None:
                continue

            # Re-attribute by first name
            detected = detect_agent_from_transcript(text)
            notes = (t.get("notes", "") or "").lower()
            if detected:
                assigned = detected
            elif "lilia" in notes:
                assigned = "lilia"
            elif "hamza" in notes:
                assigned = "hamza"
            elif "sekou" in notes:
                assigned = "sekou"
            else:
                assigned = person

            person_id = PERSON_IDS.get(assigned, PERSON_IDS.get(person, "L3"))

            # Score
            scores = score_call(text, dur)
            gs = global_score(scores)
            classification = classify_call(text)
            language = t.get("language", "fr")

            contact_num = (t.get("contact_number", "") or "").strip()
            contact_name = (t.get("contact_name", "") or "").strip()

            row = {
                "call_id": call_id,
                "person_id": person_id,
                "call_time": call_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "duration_s": dur,
                "direction": t.get("direction", ""),
                "contact_name": contact_name,
                "contact_number": contact_num,
                "classification": classification,
                "language": language,
                "transcript": text,
                "word_count": len(text.split()),
                "scores": scores,
                "global_score": gs,
                "account": t.get("account", ""),
                "notes": t.get("notes", ""),
                "detected_agent": detected,
            }
            all_calls.append(row)

            # Contact tracking
            if contact_num and len(contact_num) >= 7:
                if contact_num not in contacts:
                    contacts[contact_num] = {
                        "contact_number": contact_num,
                        "contact_name": contact_name or None,
                        "first_call_date": call_time.strftime("%Y-%m-%d"),
                        "last_call_date": call_time.strftime("%Y-%m-%d"),
                        "total_calls": 0,
                        "total_duration_s": 0,
                        "primary_agent": person_id,
                        "primary_category": classification,
                        "languages": [language] if language else [],
                    }
                c = contacts[contact_num]
                c["total_calls"] += 1
                c["total_duration_s"] += dur
                if call_time.strftime("%Y-%m-%d") < c["first_call_date"]:
                    c["first_call_date"] = call_time.strftime("%Y-%m-%d")
                if call_time.strftime("%Y-%m-%d") > c["last_call_date"]:
                    c["last_call_date"] = call_time.strftime("%Y-%m-%d")
                if contact_name and not c["contact_name"]:
                    c["contact_name"] = contact_name
                if language and language not in c["languages"]:
                    c["languages"].append(language)

    log.info("")
    log.info("Total calls to push: %d", len(all_calls))
    log.info("Total contacts to push: %d", len(contacts))

    # Push sac_calls
    log.info("")
    log.info("Pushing sac_calls...")
    ok = sb_upsert_batch("sac_calls", all_calls, on_conflict="call_id", batch_size=30)
    log.info("  sac_calls: %d/%d pushed", ok, len(all_calls))

    # Push sac_contacts
    log.info("Pushing sac_contacts...")
    contact_rows = list(contacts.values())
    ok = sb_upsert_batch("sac_contacts", contact_rows, on_conflict="contact_number", batch_size=30)
    log.info("  sac_contacts: %d/%d pushed", ok, len(contact_rows))

    # Build weekly metrics from sac_calls data
    log.info("")
    log.info("Building weekly metrics...")
    weekly = defaultdict(lambda: {"calls": 0, "dur": 0, "scores_sum": defaultdict(float), "breakdown": defaultdict(int)})

    for row in all_calls:
        ct = datetime.strptime(row["call_time"], "%Y-%m-%dT%H:%M:%S")
        # Week start = Monday
        from datetime import timedelta
        ws = ct - timedelta(days=ct.weekday())
        ws_str = ws.strftime("%Y-%m-%d")
        we_str = (ws + timedelta(days=6)).strftime("%Y-%m-%d")
        key = (row["person_id"], ws_str, we_str)
        w = weekly[key]
        w["calls"] += 1
        w["dur"] += row["duration_s"]
        for d in SAC_DIMENSIONS:
            w["scores_sum"][d] += row["scores"].get(d, 0)
        w["breakdown"][row["classification"]] += 1

    metrics_rows = []
    for (pid, ws, we), w in weekly.items():
        avg_scores = {d: round(w["scores_sum"][d] / w["calls"], 1) for d in SAC_DIMENSIONS}
        gs = round(sum(avg_scores.values()) / len(SAC_DIMENSIONS), 1)
        metrics_rows.append({
            "person_id": pid,
            "period_type": "week",
            "period_start": ws,
            "period_end": we,
            "calls_analyzed": w["calls"],
            "avg_duration_s": round(w["dur"] / w["calls"]) if w["calls"] else 0,
            "scores": avg_scores,
            "global_score": gs,
            "score_trend": 0,
            "call_breakdown": dict(w["breakdown"]),
        })

    log.info("  %d weekly metrics to push", len(metrics_rows))
    ok = sb_upsert_batch("sac_coaching_metrics", metrics_rows, on_conflict="person_id,period_type,period_start", batch_size=20)
    log.info("  sac_coaching_metrics: %d/%d pushed", ok, len(metrics_rows))

    log.info("")
    log.info("=" * 60)
    log.info("BACKFILL COMPLETE")
    log.info("  Calls: %d", len(all_calls))
    log.info("  Contacts: %d", len(contacts))
    log.info("  Weekly metrics: %d", len(metrics_rows))
    log.info("=" * 60)


if __name__ == "__main__":
    main()
