#!/usr/bin/env python3
"""
nitro_heartbeat.py — Lightweight heartbeat for Nitro GPU server.

Replaces the old nitro_watchdog.py (400+ lines of dangerous catch-up logic).

WHAT THIS DOES:
- Pushes heartbeat to Supabase every 5 minutes
- Reports disk space + scheduled tasks snapshot
- Nothing else. Windows Task Scheduler is the source of truth for crons.

WHAT THIS DOES NOT DO:
- No APScheduler — crons live in Windows Task Scheduler only
- No catch-up logic — missed crons are detected by health_check.py at 20h
- No GPU mutex — crons are staggered (19:00, 22:00, 23:30)
- No retry — each cron script handles its own retries

Run as: scheduled task ONLOGON (replaces XGuard_Watchdog)
"""

import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from nitro_common import push_watchdog_heartbeat, check_disk_space

VERSION = "2.0-heartbeat-only"
HEARTBEAT_INTERVAL_SEC = 300  # 5 minutes

LOG_DIR = Path(r"C:\Users\user\xguard_transcripts")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "heartbeat.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_FILE), encoding="utf-8"),
    ],
)
log = logging.getLogger("heartbeat")

_started_at = datetime.now(timezone.utc)


def get_scheduled_tasks_snapshot():
    """Get a snapshot of XGuard scheduled tasks via schtasks.
    Returns list of {id, next_run, status} for the dashboard.
    """
    import subprocess
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/FO", "CSV"],
            capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return []

        tasks = []
        for line in result.stdout.splitlines():
            if "XGuard_" not in line or "TaskName" in line:
                continue
            # CSV: "TaskName","Next Run Time","Status"
            parts = [p.strip('"') for p in line.split('","')]
            if len(parts) >= 3:
                name = parts[0].lstrip('"').lstrip("\\")
                next_run = parts[1]
                status = parts[2].rstrip('"')
                tasks.append({
                    "id": name,
                    "next": next_run,
                    "status": status,
                })
        return tasks[:20]
    except Exception as e:
        log.warning("Failed to get scheduled tasks: %s", e)
        return []


def heartbeat():
    """Push heartbeat to Supabase."""
    try:
        uptime = int((datetime.now(timezone.utc) - _started_at).total_seconds())

        disk_free = 0
        try:
            disk_free = check_disk_space(str(LOG_DIR), min_mb=0)
        except Exception:
            pass

        tasks = get_scheduled_tasks_snapshot()

        push_watchdog_heartbeat(
            status="alive",
            uptime_sec=uptime,
            next_jobs=tasks,
            disk_free_mb=disk_free,
            version=VERSION,
        )
        log.info("Heartbeat sent (uptime=%ds, disk=%dMB, tasks=%d)",
                 uptime, disk_free, len(tasks))

    except Exception as exc:
        log.warning("Heartbeat failed: %s", exc)


def main():
    log.info("=" * 60)
    log.info("nitro_heartbeat.py v%s — starting", VERSION)
    log.info("=" * 60)
    log.info("This is the LEAN replacement for nitro_watchdog.py")
    log.info("Windows Task Scheduler is the source of truth for crons.")
    log.info("")

    # Initial heartbeat
    heartbeat()

    # Loop
    while True:
        try:
            time.sleep(HEARTBEAT_INTERVAL_SEC)
            heartbeat()
        except KeyboardInterrupt:
            log.info("Shutdown requested")
            try:
                push_watchdog_heartbeat(status="shutdown", version=VERSION)
            except Exception:
                pass
            break
        except Exception as exc:
            log.error("Heartbeat loop error: %s", exc, exc_info=True)
            time.sleep(60)  # brief pause before retry


if __name__ == "__main__":
    main()
