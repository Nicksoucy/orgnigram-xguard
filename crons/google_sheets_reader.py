"""
google_sheets_reader.py — Read Jessica's inscription Google Sheet.

Auto-detects email + paid status columns across all tabs.
Returns list of {email, phone, name, source_tab, source_row, paid_indicator}.

Uses OAuth2 refresh token stored in secrets/google_token.json.
Run setup_google_oauth.py once to create the token.
"""

import logging
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from kb_config import (
    GOOGLE_OAUTH_JSON, GOOGLE_TOKEN_JSON, GOOGLE_SHEETS_SCOPES,
    JESSICA_SHEET_ID,
)

log = logging.getLogger("sheets_reader")

# Regex for valid email
EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')

# Header patterns (case-insensitive contains)
EMAIL_HEADERS = ['email', 'courriel', 'e-mail', 'mail']
PAID_HEADERS = ['paid', 'paye', 'payé', 'payment', 'paiement', 'statut', 'status', 'stripe', 'interac']
PHONE_HEADERS = ['phone', 'tel', 'telephone', 'téléphone', 'mobile', 'cell']
NAME_HEADERS = ['name', 'nom', 'fullname', 'full name', 'nom complet']
FIRST_HEADERS = ['first', 'prenom', 'prénom', 'first name']
LAST_HEADERS = ['last', 'last name', 'nom de famille']

# Truthy values indicating "paid"
TRUTHY = {'x', 'yes', 'oui', 'y', 'o', 'true', '1', 'paid', 'paye', 'payé',
          'complete', 'completed', 'done', 'ok', '✓', '✔', 'confirmed'}


def get_credentials():
    """Load OAuth credentials, refreshing if expired."""
    if not os.path.exists(GOOGLE_TOKEN_JSON):
        raise FileNotFoundError(
            f"Token not found: {GOOGLE_TOKEN_JSON}. "
            "Run setup_google_oauth.py first."
        )

    creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_JSON, GOOGLE_SHEETS_SCOPES)

    if creds and creds.expired and creds.refresh_token:
        log.info("Token expired, refreshing...")
        creds.refresh(Request())
        with open(GOOGLE_TOKEN_JSON, "w") as token:
            token.write(creds.to_json())
        log.info("Token refreshed OK")

    if not creds or not creds.valid:
        raise RuntimeError(
            f"Invalid credentials. Token may be revoked. Re-run setup_google_oauth.py."
        )

    return creds


def _find_column(headers, patterns):
    """Find column index where header contains any pattern (case-insensitive).
    Returns index or None.
    """
    if not headers:
        return None
    for i, h in enumerate(headers):
        if not h:
            continue
        h_lower = str(h).lower().strip()
        for p in patterns:
            if p in h_lower:
                return i
    return None


def _is_paid(value):
    """Check if a cell value indicates paid status.
    Uses word boundaries for TRUTHY matching to avoid false positives
    like 'no' matching because 'o' is a truthy keyword.
    """
    if value is None or value == "":
        return False
    v = str(value).lower().strip()
    if not v:
        return False
    # Truthy keywords — exact match OR word-boundary match (not substring)
    if v in TRUTHY:
        return True
    for t in TRUTHY:
        # Skip very short keywords (1-2 chars) for substring match — too risky
        if len(t) < 3:
            continue
        if re.search(rf'\b{re.escape(t)}\b', v):
            return True
    # Has a date format (likely payment date)
    if re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}', v):
        return True
    # Has a $ amount
    if re.search(r'\$\s*\d', v) or re.search(r'\d+[\.,]\d{2}', v):
        return True
    return False


def _safe_str(v):
    """Convert any cell value to stripped string."""
    if v is None:
        return ""
    return str(v).strip()


def _valid_email(email):
    """Check if email is valid format."""
    if not email:
        return False
    return bool(EMAIL_RE.match(email.strip().lower()))


def read_sheet(sheet_id=JESSICA_SHEET_ID, tab_filter=None):
    """Read all tabs of the sheet. Returns list of dicts.

    Args:
        sheet_id: Google Sheet ID
        tab_filter: Optional — only read this tab name (for testing)

    Returns:
        list[{email, phone, name, first_name, last_name, source_tab,
              source_row, paid_indicator, raw_row}]
    """
    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    # Get sheet metadata (list of tabs)
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    tabs = [s["properties"]["title"] for s in meta.get("sheets", [])]
    log.info("Sheet has %d tabs: %s", len(tabs), tabs)

    if tab_filter:
        tabs = [t for t in tabs if t == tab_filter]
        log.info("Filtered to tab: %s", tabs)

    rows_out = []
    skipped_tabs = []

    for tab in tabs:
        try:
            # Read all values from this tab
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=tab,
            ).execute()
            values = result.get("values", [])
        except Exception as e:
            log.warning("Failed to read tab '%s': %s", tab, e)
            skipped_tabs.append((tab, str(e)))
            continue

        if not values or len(values) < 2:
            log.info("Tab '%s': empty or no data rows, skipping", tab)
            skipped_tabs.append((tab, "empty"))
            continue

        # First non-empty row = headers
        headers = values[0]
        email_col = _find_column(headers, EMAIL_HEADERS)
        paid_col = _find_column(headers, PAID_HEADERS)
        phone_col = _find_column(headers, PHONE_HEADERS)
        name_col = _find_column(headers, NAME_HEADERS)
        first_col = _find_column(headers, FIRST_HEADERS)
        last_col = _find_column(headers, LAST_HEADERS)

        if email_col is None:
            log.warning("Tab '%s': no email column detected in headers: %s", tab, headers[:10])
            skipped_tabs.append((tab, "no email column"))
            continue

        log.info("Tab '%s': email_col=%d, paid_col=%s, phone_col=%s, name_col=%s",
                 tab, email_col, paid_col, phone_col, name_col)

        # Process data rows
        tab_count = 0
        for row_idx, row in enumerate(values[1:], start=2):  # row 2 = first data row
            if not row:
                continue

            # Extract email
            if email_col >= len(row):
                continue
            email = _safe_str(row[email_col]).lower()
            if not _valid_email(email):
                continue

            # Extract paid status
            # If no paid column, assume every row with email = paid (sheet is for paid only)
            if paid_col is None:
                is_paid = True
                paid_indicator = "(no paid column — assumed paid)"
            else:
                paid_value = _safe_str(row[paid_col]) if paid_col < len(row) else ""
                is_paid = _is_paid(paid_value)
                paid_indicator = paid_value

            if not is_paid:
                continue

            # Extract optional fields
            phone = _safe_str(row[phone_col]) if phone_col is not None and phone_col < len(row) else ""
            name = _safe_str(row[name_col]) if name_col is not None and name_col < len(row) else ""
            first_name = _safe_str(row[first_col]) if first_col is not None and first_col < len(row) else ""
            last_name = _safe_str(row[last_col]) if last_col is not None and last_col < len(row) else ""

            rows_out.append({
                "email": email,
                "phone": phone,
                "name": name,
                "first_name": first_name,
                "last_name": last_name,
                "source_tab": tab,
                "source_row": row_idx,
                "paid_indicator": paid_indicator,
            })
            tab_count += 1

        log.info("Tab '%s': %d paid rows with valid emails", tab, tab_count)

    # Dedupe by email (keep first occurrence)
    seen = set()
    unique_rows = []
    for r in rows_out:
        if r["email"] in seen:
            continue
        seen.add(r["email"])
        unique_rows.append(r)

    dupes = len(rows_out) - len(unique_rows)
    log.info("Total: %d rows (dedup: removed %d duplicate emails)", len(unique_rows), dupes)
    if skipped_tabs:
        log.info("Skipped tabs: %s", skipped_tabs)

    return unique_rows


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    rows = read_sheet()
    print(f"\n=== Found {len(rows)} paid rows ===\n")
    for r in rows[:10]:
        print(f"  {r['email']:<40} | {r['source_tab']:<20} | row {r['source_row']} | {r['paid_indicator'][:30]}")
    if len(rows) > 10:
        print(f"  ... and {len(rows) - 10} more")
