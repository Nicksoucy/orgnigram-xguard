#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
nitro_common.py — Shared utilities for all Nitro cron scripts.

Centralizes Supabase helpers, Whisper model loading, disk checks,
and status/log push functions so all 4 cron scripts use identical logic.
"""

import json
import logging
import os
import shutil
import time
from datetime import datetime, timedelta, timezone

import requests

# ---------------------------------------------------------------------------
# Supabase credentials (single source of truth)
# ---------------------------------------------------------------------------

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

# ---------------------------------------------------------------------------
# Whisper defaults
# ---------------------------------------------------------------------------

WHISPER_MODEL = "medium"
WHISPER_LANGUAGE = "fr"
WHISPER_BEAM_SIZE = 3

# ---------------------------------------------------------------------------
# Disk check
# ---------------------------------------------------------------------------

MIN_DISK_FREE_MB = 500


def check_disk_space(path: str, min_mb: int = MIN_DISK_FREE_MB) -> int:
    """Check that at least `min_mb` MB are free. Returns free MB. Raises on low space."""
    usage = shutil.disk_usage(path)
    free_mb = usage.free // (1024 * 1024)
    if free_mb < min_mb:
        raise RuntimeError(
            f"Low disk space: {free_mb}MB free at {path} (need {min_mb}MB)"
        )
    return free_mb


# ---------------------------------------------------------------------------
# Supabase helpers — consistent across all scripts
# ---------------------------------------------------------------------------

log = logging.getLogger("nitro_common")


def supabase_headers(content_type: bool = True, prefer: str = "") -> dict:
    """Build standard Supabase REST headers."""
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }
    if content_type:
        h["Content-Type"] = "application/json"
    if prefer:
        h["Prefer"] = prefer
    return h


def supabase_upsert(
    table: str,
    data: dict | list,
    on_conflict: str = "",
    timeout: int = 30,
) -> requests.Response:
    """Upsert data into a Supabase table. Raises RuntimeError on failure."""
    oc = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{oc}"
    headers = supabase_headers(prefer="resolution=merge-duplicates")
    resp = requests.post(url, json=data, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        msg = f"Supabase upsert {table} failed ({resp.status_code}): {resp.text}"
        log.error(msg)
        raise RuntimeError(msg)
    return resp


def supabase_insert(
    table: str,
    data: dict,
    timeout: int = 30,
) -> requests.Response:
    """Insert a row into Supabase. Raises RuntimeError on failure."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = supabase_headers(prefer="return=minimal")
    resp = requests.post(url, json=data, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        msg = f"Supabase insert {table} failed ({resp.status_code}): {resp.text}"
        log.error(msg)
        raise RuntimeError(msg)
    return resp


def supabase_get(
    table: str,
    params: dict,
    timeout: int = 15,
) -> list:
    """GET rows from Supabase. Returns list of dicts."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = supabase_headers(content_type=False)
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    if resp.status_code >= 400:
        log.warning("Supabase GET %s failed (%s): %s", table, resp.status_code, resp.text)
        return []
    return resp.json()


# ---------------------------------------------------------------------------
# Status & log push helpers
# ---------------------------------------------------------------------------


def update_nitro_status(
    person_id: str,
    task_type: str = "daily_sync",
    **kwargs,
):
    """Push a status row to nitro_status. Non-fatal on error."""
    payload = {
        "person_id": person_id,
        "task_type": task_type,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        **kwargs,
    }
    try:
        supabase_upsert("nitro_status", payload, on_conflict="person_id,task_type")
    except RuntimeError:
        log.warning("Failed to update nitro_status for %s (non-fatal)", person_id)


def push_cron_log(
    person_id: str,
    cron_type: str,
    status: str,
    calls_processed: int = 0,
    transcripts_new: int = 0,
    duration_sec: int = 0,
    error_msg: str | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
):
    """Insert a cron_logs row. Raises on failure."""
    supabase_insert("cron_logs", {
        "person_id": person_id,
        "cron_type": cron_type,
        "status": status,
        "calls_processed": calls_processed,
        "transcripts_new": transcripts_new,
        "duration_sec": duration_sec,
        "error_msg": error_msg,
        "started_at": started_at or datetime.now(timezone.utc).isoformat(),
        "finished_at": finished_at or datetime.now(timezone.utc).isoformat(),
    })


def push_coaching_data(
    person_id: str,
    sync_date: str,
    calls_total: int,
    calls_transcribed: int,
    calls_new: int,
    avg_duration_sec: int,
    source: str = "justcall",
    call_breakdown: dict | None = None,
):
    """Upsert daily coaching_data row. Raises on failure."""
    payload = {
        "person_id": person_id,
        "sync_date": sync_date,
        "calls_total": calls_total,
        "calls_transcribed": calls_transcribed,
        "calls_new": calls_new,
        "avg_duration_sec": avg_duration_sec,
        "source": source,
    }
    if call_breakdown is not None:
        payload["call_breakdown"] = (
            json.dumps(call_breakdown) if isinstance(call_breakdown, dict) else call_breakdown
        )
    supabase_upsert("coaching_data", payload, on_conflict="person_id,sync_date")


def push_call_activity(
    person_id: str,
    activity_date: str,
    total_dials: int,
    answered: int,
    not_answered: int,
    short_calls: int,
    qualified_calls: int,
    transcribed: int,
    avg_duration_sec: int,
):
    """Upsert daily call_activity funnel row. Raises on failure."""
    supabase_upsert(
        "call_activity",
        {
            "person_id": person_id,
            "activity_date": activity_date,
            "total_dials": total_dials,
            "answered": answered,
            "not_answered": not_answered,
            "short_calls": short_calls,
            "qualified_calls": qualified_calls,
            "transcribed": transcribed,
            "avg_duration_sec": avg_duration_sec,
        },
        on_conflict="person_id,activity_date",
    )


# ---------------------------------------------------------------------------
# Catch-up helper (used by daily crons)
# ---------------------------------------------------------------------------


def get_last_successful_sync_date(person_id: str) -> str | None:
    """Query cron_logs for the last successful daily_sync date."""
    rows = supabase_get("cron_logs", {
        "person_id": f"eq.{person_id}",
        "cron_type": "eq.daily_sync",
        "status": "eq.success",
        "order": "started_at.desc",
        "limit": "1",
    })
    if rows and rows[0].get("started_at"):
        return rows[0]["started_at"][:10]
    return None


def compute_dates_to_sync(person_id: str, today_str: str, max_days: int = 14) -> list[str]:
    """Return list of dates to sync, catching up missed days (capped at max_days)."""
    last_sync = get_last_successful_sync_date(person_id)
    if last_sync:
        last_dt = datetime.strptime(last_sync, "%Y-%m-%d")
        today_dt = datetime.strptime(today_str, "%Y-%m-%d")
        start_dt = last_dt + timedelta(days=1)
        dates = []
        d = start_dt
        while d <= today_dt:
            dates.append(d.strftime("%Y-%m-%d"))
            d += timedelta(days=1)
        return dates[-max_days:]
    return [today_str]


# ---------------------------------------------------------------------------
# Whisper model loading
# ---------------------------------------------------------------------------


def load_whisper_model(
    model_size: str = WHISPER_MODEL,
    language: str = WHISPER_LANGUAGE,
):
    """Load faster-whisper model with CUDA, fall back to CPU. Returns (model, gpu_active)."""
    from faster_whisper import WhisperModel

    try:
        model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        log.info("Whisper model loaded on CUDA (int8_float16)")
        return model, True
    except Exception as exc:
        log.warning("CUDA unavailable (%s), falling back to CPU", exc)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        return model, False


# ---------------------------------------------------------------------------
# Watchdog heartbeat
# ---------------------------------------------------------------------------


def push_watchdog_heartbeat(
    status: str = "alive",
    uptime_sec: int = 0,
    next_jobs: list | None = None,
    disk_free_mb: int = 0,
    version: str = "1.0",
    error_msg: str | None = None,
):
    """Push watchdog heartbeat to watchdog_heartbeat table."""
    supabase_upsert(
        "watchdog_heartbeat",
        {
            "id": "nitro",
            "status": status,
            "last_heartbeat": datetime.now(timezone.utc).isoformat(),
            "uptime_sec": uptime_sec,
            "next_jobs": json.dumps(next_jobs or []),
            "disk_free_mb": disk_free_mb,
            "version": version,
            "error_msg": error_msg,
        },
        on_conflict="id",
    )
