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
# GoHighLevel (GHL) API
# ---------------------------------------------------------------------------
GHL_BASE = "https://services.leadconnectorhq.com"
GHL_PIT_TOKEN = "pit-7de455ab-c46e-47a4-af9e-0b07a6c3a1ee"
GHL_LOCATION = "dfkLurZY2ADWAUZl4zYc"
GHL_API_VERSION = "2021-07-28"
GHL_HEADERS = {
    "Authorization": f"Bearer {GHL_PIT_TOKEN}",
    "Version": GHL_API_VERSION,
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
}

# ---------------------------------------------------------------------------
# Google Sheets — Jessica's inscription tracking sheet
# ---------------------------------------------------------------------------
import os as _os
_BASE_DIR = _os.path.dirname(_os.path.abspath(__file__))
GOOGLE_OAUTH_JSON = _os.path.join(_BASE_DIR, "secrets", "google_oauth.json")
GOOGLE_TOKEN_JSON = _os.path.join(_BASE_DIR, "secrets", "google_token.json")
GOOGLE_SHEETS_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
JESSICA_SHEET_ID = "11lHzYWzRJXsDWCk9soYu2uKwOFPSqqKe3QfyHzq0AKc"
XGUARD_PAID_TAG = "gard paid"  # real tag used by Jessica's workflow in GHL

# ---------------------------------------------------------------------------
# Claude CLI (on Nitro)
# ---------------------------------------------------------------------------
# Claude CLI — use claude_scoring.CLAUDE_EXE (auto-detected) instead of hardcoded path
# This hardcoded value is kept for backwards compat but should NOT be used (will break on updates)
try:
    from claude_scoring import CLAUDE_EXE
except ImportError:
    CLAUDE_EXE = None  # will be detected at runtime by claude_scoring
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
    "twilio", "vercel", "supabase", "interac", "brave.com",
    "qualtrics", "mailchimp", "sendgrid", "hubspot",
    "google.com", "microsoft.com", "apple.com", "amazon.com",
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
