#!/usr/bin/env python3
"""
Conversion Sync — Daily cron (06h) on Nitro.
Fetches "Gagné"/"Closed" opportunities from GHL pipelines,
matches against sac_calls/sac_contacts by phone number,
and upserts to conversions table.

Usage:
  python conversion_sync.py            # sync last 7 days
  python conversion_sync.py --backfill # sync ALL Gagné/Closed (historical)
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from kb_config import sb_upsert, sb_get, sb_patch, sb_count
from phone_utils import normalize_number

LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / f"conversion_sync_{datetime.now():%Y-%m-%d}.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger("conversion_sync")

# GHL config (from heidys_daily_email.py)
GHL_TOKEN = "pit-7de455ab-c46e-47a4-af9e-0b07a6c3a1ee"
GHL_LOCATION = "dfkLurZY2ADWAUZl4zYc"
GHL_BASE = "https://services.leadconnectorhq.com"
GHL_HEADERS = {"Authorization": f"Bearer {GHL_TOKEN}", "Version": "2021-07-28"}

PIPELINES = {
    "heidys_gardiennage": {
        "pipeline_id": "7vru0wO6zRcDJsfQGdFI",
        "won_stage_id": "f32a33ea-c7be-4faa-8a6e-43ef52256f74",
        "program_type": "gardiennage",
    },
    "domingos_drone": {
        "pipeline_id": "W08jXuPPrQDM0EFcCgAR",
        "won_stage_id": "bc4ebcda-f447-41e0-beb9-e0fb3fafc4bb",
        "program_type": "drone",
    },
}


def fetch_won_opportunities(pipeline_name, pipeline_config, since_days=7):
    """Fetch all won/closed opportunities from a GHL pipeline."""
    won = []
    cutoff = datetime.now() - timedelta(days=since_days) if since_days else None

    for page in range(1, 20):
        try:
            params = {
                "location_id": GHL_LOCATION,
                "pipeline_id": pipeline_config["pipeline_id"],
                "pipeline_stage_id": pipeline_config["won_stage_id"],
                "limit": 100,
                "page": page,
            }
            r = requests.get(f"{GHL_BASE}/opportunities/search",
                             params=params, headers=GHL_HEADERS, timeout=30)
            if r.status_code != 200:
                log.warning("GHL API error %d: %s", r.status_code, r.text[:200])
                break
            opps = r.json().get("opportunities", [])
            if not opps:
                break

            for opp in opps:
                updated = opp.get("updatedAt", "") or opp.get("createdAt", "")
                if cutoff and updated:
                    try:
                        opp_date = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        if opp_date.replace(tzinfo=None) < cutoff:
                            continue
                    except Exception:
                        pass

                contact = opp.get("contact", {}) or {}
                phone = normalize_number(contact.get("phone", ""))
                if not phone:
                    continue

                won.append({
                    "opp_id": opp.get("id", ""),
                    "contact_id": opp.get("contactId", ""),
                    "name": opp.get("name", "") or contact.get("name", ""),
                    "phone": phone,
                    "email": contact.get("email", ""),
                    "monetary_value": opp.get("monetaryValue", 0) or 0,
                    "updated_at": updated[:10] if updated else datetime.now().strftime("%Y-%m-%d"),
                    "pipeline": pipeline_name,
                    "program": pipeline_config["program_type"],
                })

            if len(opps) < 100:
                break
            time.sleep(0.3)
        except Exception as e:
            log.error("GHL fetch error: %s", e)
            break

    return won


def match_call_history(phone_10):
    """Find call history in sac_calls for a normalized 10-digit phone."""
    # sac_calls stores numbers as "14381234567" (11-digit with leading 1)
    # Match on last 10 digits
    calls = sb_get(f"sac_calls?contact_number=like.*{phone_10}"
                   f"&select=call_time,person_id,classification,ai_global_score,global_score"
                   f"&order=call_time.asc&limit=50")
    if not calls:
        return None

    inscription_calls = [c for c in calls if c.get("classification") == "inscription"]
    scores = [c.get("ai_global_score") or c.get("global_score") or 0 for c in calls if (c.get("ai_global_score") or c.get("global_score"))]

    first_call = calls[0].get("call_time", "")[:10] if calls else None
    first_inscription = inscription_calls[0] if inscription_calls else None
    attributed = first_inscription.get("person_id") if first_inscription else (calls[0].get("person_id") if calls else None)

    return {
        "first_contact_date": first_call,
        "total_calls": len(calls),
        "attributed_agent": attributed,
        "best_score": round(max(scores), 1) if scores else None,
        "avg_score": round(sum(scores) / len(scores), 1) if scores else None,
    }


def sync_conversions(backfill=False):
    """Main sync: fetch GHL wins, match calls, upsert conversions."""
    log.info("=" * 60)
    log.info("CONVERSION SYNC — %s%s", datetime.now().strftime("%Y-%m-%d %H:%M"),
             " (BACKFILL MODE)" if backfill else "")
    log.info("=" * 60)

    since_days = None if backfill else 7
    total_synced = 0
    total_matched = 0

    for pipeline_name, config in PIPELINES.items():
        log.info("")
        log.info("--- %s ---", pipeline_name)
        won = fetch_won_opportunities(pipeline_name, config, since_days=since_days)
        log.info("  %d won opportunities found", len(won))

        for opp in won:
            # Check if already synced
            existing = sb_get(f"conversions?ghl_opportunity_id=eq.{opp['opp_id']}&select=id")
            if existing:
                continue

            # Match call history
            history = match_call_history(opp["phone"])

            first_contact = history["first_contact_date"] if history else None
            enrollment_date = opp["updated_at"]
            days_to = None
            if first_contact and enrollment_date:
                try:
                    d1 = datetime.strptime(first_contact, "%Y-%m-%d")
                    d2 = datetime.strptime(enrollment_date, "%Y-%m-%d")
                    days_to = (d2 - d1).days
                except Exception:
                    pass

            row = {
                "contact_number": opp["phone"],
                "contact_name": opp["name"],
                "contact_email": opp["email"],
                "pipeline_source": pipeline_name,
                "ghl_opportunity_id": opp["opp_id"],
                "ghl_contact_id": opp["contact_id"],
                "program_type": opp["program"],
                "monetary_value": opp["monetary_value"],
                "first_contact_date": first_contact,
                "enrollment_date": enrollment_date,
                "days_to_conversion": days_to,
                "first_touchpoint": "call" if history else "unknown",
                "attributed_agent": history["attributed_agent"] if history else None,
                "total_calls_before": history["total_calls"] if history else 0,
                "best_call_score": history["best_score"] if history else None,
                "avg_call_score": history["avg_score"] if history else None,
            }

            sb_upsert("conversions", row, on_conflict="ghl_opportunity_id")
            total_synced += 1
            if history:
                total_matched += 1

            # Update sac_contacts
            if history:
                sb_patch("sac_contacts", f"contact_number=like.*{opp['phone']}",
                         {"converted": True, "conversion_date": enrollment_date})

            log.info("  %s %s | %s | %s days | agent: %s | score: %s",
                     "MATCHED" if history else "NEW    ",
                     opp["name"][:25], opp["program"],
                     days_to if days_to is not None else "?",
                     (history["attributed_agent"] if history else "?"),
                     (history["avg_score"] if history else "?"))

    log.info("")
    log.info("=" * 60)
    log.info("DONE — %d synced, %d matched with call history", total_synced, total_matched)
    log.info("Total in conversions: %d", sb_count("conversions"))
    log.info("=" * 60)


def main():
    backfill = "--backfill" in sys.argv
    sync_conversions(backfill=backfill)


if __name__ == "__main__":
    main()
