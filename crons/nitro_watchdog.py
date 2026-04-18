#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nitro_watchdog.py — Persistent scheduler & watchdog for Nitro GPU cron jobs.

Replaces Windows Task Scheduler with a self-healing Python service that:
- Schedules all 4 cron jobs (Heidys, Domingos, SAC daily + weekly report)
- Sends heartbeat to Supabase every 5 minutes
- Detects and runs missed jobs on startup
- Enforces a GPU mutex (only 1 transcription job at a time)
- Retries failed jobs with exponential backoff
- Logs everything to watchdog.log + console

Usage:
    python nitro_watchdog.py              # run in foreground
    python nitro_watchdog.py --once       # run missed jobs then exit (testing)

Requires: pip install apscheduler requests
"""

import argparse
import importlib
import json
import logging
import os
import shutil
import sys
import threading
import time
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

VERSION = "1.0"
HEARTBEAT_INTERVAL_SEC = 300  # 5 minutes
MAX_JOB_RETRIES = 2
RETRY_DELAYS = [60, 120]  # seconds between retries
MISFIRE_GRACE_SEC = 3600  # run a job up to 1 hour late

LOG_DIR = r"C:\Users\user\xguard_transcripts"
LOG_FILE = os.path.join(LOG_DIR, "watchdog.log")

# Schedule: maps job_id -> module, function, cron kwargs
SCHEDULE = {
    "dom_daily": {
        "module": "nitro_dom_daily",
        "func": "main",
        "cron": {"hour": 23, "minute": 0},
        "person_ids": ["t11"],
        "description": "Domingos daily sync",
    },
    "heidys_daily": {
        "module": "nitro_heidys_daily",
        "func": "main",
        "cron": {"hour": 23, "minute": 15},
        "person_ids": ["v1"],
        "description": "Heidys daily sync",
    },
    "sac_daily": {
        "module": "nitro_sac_daily",
        "func": "main",
        "cron": {"hour": 23, "minute": 30},
        "person_ids": ["L3", "s2", "s3"],
        "description": "SAC daily sync (Hamza, Lilia, Sekou)",
    },
    "weekly_report": {
        "module": "nitro_weekly_report",
        "func": "run",
        "cron": {"day_of_week": "fri", "hour": 15, "minute": 0},
        "person_ids": ["v1", "t11", "L3", "s2", "s3"],
        "description": "Weekly coaching report",
    },
}

# ---------------------------------------------------------------------------
# Logging — unified for watchdog + all child jobs
# ---------------------------------------------------------------------------

os.makedirs(LOG_DIR, exist_ok=True)

log = logging.getLogger("nitro_watchdog")
log.setLevel(logging.INFO)

_fmt = logging.Formatter(
    "%(asctime)s [WATCHDOG] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

_console = logging.StreamHandler()
_console.setFormatter(_fmt)
log.addHandler(_console)

try:
    _fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _fh.setFormatter(_fmt)
    log.addHandler(_fh)
except OSError:
    log.warning("Could not open log file %s — console only", LOG_FILE)

# ---------------------------------------------------------------------------
# GPU Mutex — prevents OOM when two jobs would load Whisper simultaneously
# ---------------------------------------------------------------------------

_gpu_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Import helpers — lazy-import cron modules
# ---------------------------------------------------------------------------

# Add crons directory to path so we can import sibling modules
_crons_dir = os.path.dirname(os.path.abspath(__file__))
if _crons_dir not in sys.path:
    sys.path.insert(0, _crons_dir)


def _import_and_run(module_name: str, func_name: str):
    """Import a cron module and call its entry function."""
    mod = importlib.import_module(module_name)
    # Reload to pick up any code changes without restarting watchdog
    importlib.reload(mod)
    fn = getattr(mod, func_name)
    fn()


# ---------------------------------------------------------------------------
# Safe job runner with retry + GPU lock
# ---------------------------------------------------------------------------


def run_job_safe(job_id: str):
    """Run a scheduled job with GPU mutex, retries, and error logging."""
    config = SCHEDULE[job_id]
    module_name = config["module"]
    func_name = config["func"]
    description = config["description"]

    log.info("=== JOB START: %s (%s) ===", job_id, description)

    for attempt in range(MAX_JOB_RETRIES + 1):
        try:
            log.info("Acquiring GPU lock for %s (attempt %d/%d)...",
                     job_id, attempt + 1, MAX_JOB_RETRIES + 1)
            with _gpu_lock:
                log.info("GPU lock acquired. Running %s.%s()", module_name, func_name)
                t0 = time.time()
                _import_and_run(module_name, func_name)
                elapsed = time.time() - t0
                log.info("=== JOB DONE: %s (%.0fs) ===", job_id, elapsed)
            return  # success

        except Exception as exc:
            elapsed = time.time() - t0 if 't0' in dir() else 0
            log.error("JOB FAILED: %s (attempt %d/%d, %.0fs): %s",
                      job_id, attempt + 1, MAX_JOB_RETRIES + 1, elapsed, exc,
                      exc_info=True)

            if attempt < MAX_JOB_RETRIES:
                wait = RETRY_DELAYS[attempt]
                log.info("Retrying %s in %ds...", job_id, wait)
                time.sleep(wait)
            else:
                log.error("=== JOB ABANDONED: %s after %d attempts ===",
                          job_id, MAX_JOB_RETRIES + 1)
                # Push error to cron_logs via nitro_common
                try:
                    from nitro_common import push_cron_log
                    for pid in config["person_ids"]:
                        push_cron_log(
                            person_id=pid,
                            cron_type="daily_sync" if "daily" in job_id else "weekly_report",
                            status="error",
                            error_msg=f"Watchdog: {MAX_JOB_RETRIES + 1} attempts failed. Last: {str(exc)[:300]}",
                        )
                except Exception:
                    log.warning("Could not push error log to Supabase")


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------

_started_at = datetime.now(timezone.utc)


def heartbeat(scheduler=None):
    """Push heartbeat to Supabase watchdog_heartbeat table."""
    try:
        from nitro_common import push_watchdog_heartbeat, check_disk_space

        uptime = int((datetime.now(timezone.utc) - _started_at).total_seconds())

        # Get next scheduled jobs
        next_jobs = []
        if scheduler:
            for job in scheduler.get_jobs():
                nrt = job.next_run_time
                if nrt:
                    next_jobs.append({
                        "id": job.id,
                        "next": nrt.isoformat(),
                    })

        # Disk space
        disk_free = 0
        try:
            disk_free = check_disk_space(LOG_DIR, min_mb=0)
        except Exception:
            pass

        push_watchdog_heartbeat(
            status="alive",
            uptime_sec=uptime,
            next_jobs=next_jobs,
            disk_free_mb=disk_free,
            version=VERSION,
        )
        log.info("Heartbeat sent (uptime=%ds, disk=%dMB, jobs=%d)",
                 uptime, disk_free, len(next_jobs))

    except Exception as exc:
        log.warning("Heartbeat failed: %s", exc)


# ---------------------------------------------------------------------------
# Missed-run detection — catches up jobs that should have run but didn't
# ---------------------------------------------------------------------------


def check_and_run_missed_jobs():
    """Check if any daily job missed today's run; if so, trigger it now."""
    log.info("Checking for missed jobs...")
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    try:
        from nitro_common import supabase_get
    except ImportError:
        log.error("Cannot import nitro_common — skipping missed job check")
        return

    for job_id, config in SCHEDULE.items():
        # Skip weekly report — it has its own logic
        if job_id == "weekly_report":
            continue

        cron = config["cron"]
        scheduled_hour = cron.get("hour", 23)
        scheduled_minute = cron.get("minute", 0)

        # Only trigger catch-up if we're past the scheduled time
        if now.hour < scheduled_hour or (now.hour == scheduled_hour and now.minute < scheduled_minute):
            continue

        # Check if any person_id in this job has a successful run today
        has_run_today = False
        for pid in config["person_ids"]:
            rows = supabase_get("cron_logs", {
                "person_id": f"eq.{pid}",
                "cron_type": "eq.daily_sync",
                "status": "eq.success",
                "started_at": f"gte.{today_str}T00:00:00Z",
                "order": "started_at.desc",
                "limit": "1",
            })
            if rows:
                has_run_today = True
                break

        if not has_run_today:
            log.info("CATCH-UP: %s missed today's run — triggering now", job_id)
            run_job_safe(job_id)
        else:
            log.info("OK: %s already ran today", job_id)

    # Weekly report catch-up DISABLED — sac_weekly_v3 scheduled task runs
    # Monday 07:00. Old nitro_weekly_report.py has schema mismatches.

    log.info("Missed job check complete.")


# ---------------------------------------------------------------------------
# Main — APScheduler loop
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Nitro Watchdog Service")
    parser.add_argument("--once", action="store_true",
                        help="Run missed jobs then exit (for testing)")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("NITRO WATCHDOG v%s starting", VERSION)
    log.info("Python %s | PID %d", sys.version.split()[0], os.getpid())
    log.info("Log file: %s", LOG_FILE)
    log.info("=" * 60)

    # Send initial heartbeat
    heartbeat()

    # Check for missed jobs on startup
    check_and_run_missed_jobs()

    if args.once:
        log.info("--once mode: exiting after missed job check")
        return

    # Set up APScheduler
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
    except ImportError:
        log.error(
            "APScheduler not installed. Install with: pip install apscheduler\n"
            "Falling back to simple sleep loop."
        )
        _fallback_loop()
        return

    scheduler = BlockingScheduler(
        job_defaults={
            "max_instances": 1,
            "misfire_grace_time": MISFIRE_GRACE_SEC,
            "coalesce": True,
        },
        timezone="UTC",
    )

    # Add cron jobs
    for job_id, config in SCHEDULE.items():
        trigger = CronTrigger(**config["cron"], timezone="UTC")
        scheduler.add_job(
            run_job_safe,
            trigger=trigger,
            args=[job_id],
            id=job_id,
            name=config["description"],
        )
        log.info("Scheduled: %s -> %s (%s)", job_id, config["description"], config["cron"])

    # Add heartbeat (every 5 minutes)
    scheduler.add_job(
        heartbeat,
        trigger=IntervalTrigger(seconds=HEARTBEAT_INTERVAL_SEC),
        args=[scheduler],
        id="heartbeat",
        name="Watchdog heartbeat",
    )
    log.info("Scheduled: heartbeat every %ds", HEARTBEAT_INTERVAL_SEC)

    # Add daily missed-job check (run at 23:45, after all dailies should be done)
    scheduler.add_job(
        check_and_run_missed_jobs,
        trigger=CronTrigger(hour=23, minute=45, timezone="UTC"),
        id="missed_check",
        name="Missed job catch-up check",
    )
    log.info("Scheduled: missed job check at 23:45 UTC")

    log.info("=" * 60)
    log.info("Watchdog running. Press Ctrl+C to stop.")
    log.info("=" * 60)

    # Push startup heartbeat with scheduler info
    heartbeat(scheduler)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Watchdog shutting down gracefully...")
        try:
            from nitro_common import push_watchdog_heartbeat
            push_watchdog_heartbeat(status="shutdown", version=VERSION)
        except Exception:
            pass
        log.info("Watchdog stopped.")


# ---------------------------------------------------------------------------
# Fallback loop (if APScheduler not installed)
# ---------------------------------------------------------------------------


def _fallback_loop():
    """Simple sleep-based scheduler. Less accurate but zero dependencies."""
    log.info("Running in fallback mode (no APScheduler)")

    last_daily_run = ""
    last_weekly_run = ""

    while True:
        try:
            now = datetime.now(timezone.utc)
            today_str = now.strftime("%Y-%m-%d")
            hhmm = now.strftime("%H:%M")

            # Heartbeat every 5 min (approximate)
            heartbeat()

            # Daily jobs: run once per day after 23:00
            if hhmm >= "23:00" and last_daily_run != today_str:
                last_daily_run = today_str
                for job_id in ["dom_daily", "heidys_daily", "sac_daily"]:
                    run_job_safe(job_id)

            # Weekly report: DISABLED — sac_weekly_v3 scheduled task handles this
            # on Monday 07:00. Old nitro_weekly_report.py has schema mismatches
            # with current Supabase tables. Keep commented for historical ref.
            # if now.weekday() == 4 and hhmm >= "15:00" and last_weekly_run != today_str:
            #     last_weekly_run = today_str
            #     run_job_safe("weekly_report")

            time.sleep(HEARTBEAT_INTERVAL_SEC)

        except KeyboardInterrupt:
            log.info("Fallback loop interrupted. Shutting down.")
            break
        except Exception as exc:
            log.error("Fallback loop error: %s", exc, exc_info=True)
            time.sleep(60)


if __name__ == "__main__":
    main()
