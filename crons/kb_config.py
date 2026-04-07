"""
KB Config — Shared constants for all Knowledge Base scripts.
"""

import logging
import requests

# ---------------------------------------------------------------------------
# IMAP
# ---------------------------------------------------------------------------
IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "academie@academiexguard.ca"
EMAIL_PASSWORD = "qlhoktyrfnrcbomd"

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------
SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

# ---------------------------------------------------------------------------
# SMTP
# ---------------------------------------------------------------------------
GMAIL_USER = "nick@darkhorseads.com"
GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"
NICK_EMAIL = "nick@darkhorseads.com"

# ---------------------------------------------------------------------------
# Claude CLI (on Nitro)
# ---------------------------------------------------------------------------
CLAUDE_EXE = r"C:\Users\User\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code\2.1.63\claude.exe"
GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"

# ---------------------------------------------------------------------------
# Processing limits
# ---------------------------------------------------------------------------
MAX_EMAILS_PER_RUN = 2000       # ~2.5h of Haiku calls with 5 workers
BATCH_SIZE = 20                  # emails per batch
BATCH_PAUSE_SEC = 10             # pause between batches
MAX_WORKERS = 5                  # parallel Haiku workers
MAX_CONSECUTIVE_FAILURES = 15    # abort threshold
HAIKU_TIMEOUT = 60               # seconds per call

# ---------------------------------------------------------------------------
# Smart folder selection — SAC-relevant folders only
# ---------------------------------------------------------------------------
PRIORITY_FOLDERS = [
    "INBOX",
    "Service &AOA- la client&AOg-le a traiter",
    "Annuler",
    "Litige",
    "BSP",
    "Secourisme",
    "Secourisme &AOA- choisir",
    "Recouvrement",
    "Drone",
    "Retard / absence",
    "Winback",
    "service a confirmer",
    "$Vente",
    "$Vente/Hamza",
    "$Vente/Heidys Garcia",
    "$Vente/Domingos",
    "$Vente/Manel",
    "*Sekou",
    "internatonnal",
    "usage de la force/Gestion",
]

MAX_PER_FOLDER = 1500  # last N emails per folder (increased for deeper coverage)

# ---------------------------------------------------------------------------
# Internal senders to skip
# ---------------------------------------------------------------------------
XGUARD_DOMAINS = {"xguard.ca", "academiexguard.ca"}
XGUARD_EMAILS = {"nick@darkhorseads.com"}
IGNORE_SENDERS = {
    "noreply", "no-reply", "mailer-daemon", "postmaster", "notifications",
    "justcall", "gohighlevel", "calendly", "stripe", "paypal",
    "support@justcall", "notification@", "system@", "alert@",
}

# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------
log = logging.getLogger("kb_config")


def _sb_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


def sb_upsert(table, data, on_conflict=""):
    """Insert or update rows in Supabase."""
    oc = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{oc}"
    headers = _sb_headers()
    headers["Prefer"] = "resolution=merge-duplicates"
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=30)
        if resp.status_code not in (200, 201):
            log.warning("sb_upsert %s failed (%d): %s", table, resp.status_code, resp.text[:200])
        return resp
    except Exception as e:
        log.error("sb_upsert %s error: %s", table, e)
        return None


def sb_get(path):
    """GET from Supabase REST API."""
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    try:
        resp = requests.get(url, headers=_sb_headers(), timeout=30)
        return resp.json() if resp.status_code == 200 else []
    except Exception as e:
        log.error("sb_get error: %s", e)
        return []


def sb_patch(table, filter_str, data):
    """PATCH (update) rows in Supabase."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?{filter_str}"
    try:
        resp = requests.patch(url, json=data, headers=_sb_headers(), timeout=30)
        if resp.status_code not in (200, 204):
            log.warning("sb_patch %s failed (%d): %s", table, resp.status_code, resp.text[:200])
        return resp
    except Exception as e:
        log.error("sb_patch error: %s", e)
        return None


def sb_count(table, filter_str=""):
    """Count rows in a table."""
    url = f"{SUPABASE_URL}/rest/v1/{table}?select=id&{filter_str}" if filter_str else f"{SUPABASE_URL}/rest/v1/{table}?select=id"
    headers = _sb_headers()
    headers["Prefer"] = "count=exact"
    headers["Range"] = "0-0"
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        cr = resp.headers.get("Content-Range", "")
        # Format: "0-0/123" or "*/0"
        if "/" in cr:
            return int(cr.split("/")[-1])
        return 0
    except Exception:
        return 0
