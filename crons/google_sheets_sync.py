"""
google_sheets_sync.py — Daily sync: Jessica's Google Sheet -> GHL "xguard paid" tag.

For each paid row in the sheet:
  1. Find contact in GHL by email
  2. If found + not tagged: add "xguard paid" tag
  3. If found + already tagged: skip (idempotent)
  4. If not found: create contact with email + tag
  5. Log everything to Supabase google_sheets_sync_log

Flags:
  --dry-run       Don't actually tag/create. Log what WOULD happen.
  --limit N       Process max N rows (for testing)
  --tab "Name"    Only process one specific tab

Run on Nitro daily at 21h00 via scheduled task XGuard_SheetsSync.
"""

import argparse
import logging
import os
import smtplib
import sys
import traceback
from datetime import datetime, date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

from kb_config import (
    sb_upsert, sb_get,
    GMAIL_USER, GMAIL_APP_PASSWORD, NICK_EMAIL,
    XGUARD_PAID_TAG,
)
from google_sheets_reader import read_sheet
from ghl_helpers import (
    ghl_find_contact_by_email, ghl_create_contact,
    ghl_add_tag, ghl_has_tag,
)

# Logging setup
LOG_DIR = Path(r"C:\Users\user\sac_logs")
_handlers = [logging.StreamHandler()]
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(
        str(LOG_DIR / f"sheets_sync_{datetime.now():%Y-%m-%d}.log"),
        encoding="utf-8",
    ))
except (PermissionError, OSError):
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_handlers,
)
log = logging.getLogger("sheets_sync")


def track(row, status, contact_id=None, error=None, tag_added=False):
    """Log a sync result to Supabase."""
    try:
        data = {
            "run_date": date.today().isoformat(),
            "email": row["email"],
            "phone": row.get("phone") or None,
            "name": row.get("name") or f"{row.get('first_name', '')} {row.get('last_name', '')}".strip() or None,
            "source_tab": row["source_tab"],
            "source_row": row["source_row"],
            "contact_id": contact_id,
            "status": status,
            "error": error[:500] if error else None,
            "tag_added_at": datetime.now().isoformat() if tag_added else None,
        }
        sb_upsert("google_sheets_sync_log", data, on_conflict="run_date,email")
    except Exception as e:
        log.warning("Failed to log to Supabase: %s", e)


def process_row(row, dry_run=False):
    """Process one row. Returns status string."""
    email = row["email"]

    try:
        # Step 1: Find contact in GHL
        contact = ghl_find_contact_by_email(email)

        if contact:
            contact_id = contact.get("id")

            # Step 2a: Already tagged?
            if ghl_has_tag(contact, XGUARD_PAID_TAG):
                track(row, "already_tagged", contact_id=contact_id)
                return "already_tagged"

            # Step 2b: Tag it
            if dry_run:
                track(row, "would_tag", contact_id=contact_id)
                return "would_tag"

            ok = ghl_add_tag(contact_id, XGUARD_PAID_TAG)
            if ok:
                track(row, "tagged", contact_id=contact_id, tag_added=True)
                return "tagged"
            else:
                track(row, "error", contact_id=contact_id, error="ghl_add_tag failed")
                return "error"

        # Step 3: Not found — create
        if dry_run:
            track(row, "would_create")
            return "would_create"

        created = ghl_create_contact(
            email=email,
            first_name=row.get("first_name") or None,
            last_name=row.get("last_name") or None,
            phone=row.get("phone") or None,
            tags=[XGUARD_PAID_TAG],
        )

        if created and created.get("id"):
            track(row, "created_and_tagged", contact_id=created["id"], tag_added=True)
            return "created_and_tagged"
        else:
            track(row, "error", error="ghl_create_contact returned None")
            return "error"

    except Exception as e:
        err_msg = f"{type(e).__name__}: {e}"
        log.error("Row error for %s: %s", email, err_msg)
        track(row, "error", error=err_msg)
        return "error"


def send_summary_email(stats, dry_run, duration_sec, tab_filter=None):
    """Send summary email to Nick."""
    total = sum(stats.values())
    status_counts = "".join(
        f'<tr><td style="padding:4px 8px;"><strong>{k}</strong></td><td style="padding:4px 8px;text-align:right;">{v}</td></tr>'
        for k, v in sorted(stats.items(), key=lambda x: -x[1])
    )

    mode_label = "DRY RUN" if dry_run else "PRODUCTION"
    tab_label = f" (tab: {tab_filter})" if tab_filter else ""

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
<div style="background:#1B3A5C;padding:15px;border-radius:8px 8px 0 0;text-align:center;">
  <h2 style="color:white;margin:0;">Google Sheets Sync — {mode_label}{tab_label}</h2>
  <p style="color:#ccc;margin:4px 0 0;font-size:12px;">{date.today().isoformat()} | {total} rows | {duration_sec:.0f}s</p>
</div>
<div style="padding:15px;border:1px solid #ddd;border-top:none;">
  <table style="width:100%;border-collapse:collapse;font-size:13px;">
    <tr style="background:#f5f5f5;"><th style="padding:6px;text-align:left;">Status</th><th style="padding:6px;text-align:right;">Count</th></tr>
    {status_counts}
    <tr style="background:#f5f5f5;"><td style="padding:6px;"><strong>TOTAL</strong></td><td style="padding:6px;text-align:right;"><strong>{total}</strong></td></tr>
  </table>
  <p style="margin-top:12px;font-size:11px;color:#777;">
    Dashboard: <a href="https://ctjsdpfegpsfpwjgusyi.supabase.co/project/ctjsdpfegpsfpwjgusyi/editor/google_sheets_sync_log">Supabase google_sheets_sync_log</a>
  </p>
</div>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = NICK_EMAIL
    msg["Subject"] = f"[SheetsSync {mode_label}] {date.today().isoformat()} — {total} rows"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [NICK_EMAIL], msg.as_string())
        log.info("Summary email sent")
    except Exception as e:
        log.warning("Summary email failed: %s", e)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't actually tag/create")
    parser.add_argument("--limit", type=int, default=None, help="Max rows to process")
    parser.add_argument("--tab", default=None, help="Only process this tab")
    args = parser.parse_args()

    t0 = datetime.now()

    log.info("=" * 60)
    log.info("GOOGLE SHEETS SYNC — %s", "DRY RUN" if args.dry_run else "PRODUCTION")
    log.info("=" * 60)
    if args.limit:
        log.info("Limit: %d rows", args.limit)
    if args.tab:
        log.info("Tab filter: %s", args.tab)

    # Read sheet
    try:
        rows = read_sheet(tab_filter=args.tab)
    except Exception as e:
        log.error("Sheet read failed: %s", e, exc_info=True)
        # Send error email
        msg = MIMEMultipart("alternative")
        msg["From"] = GMAIL_USER
        msg["To"] = NICK_EMAIL
        msg["Subject"] = f"[SheetsSync ERROR] {date.today().isoformat()} — sheet read failed"
        msg.attach(MIMEText(f"<pre>{traceback.format_exc()}</pre>", "html", "utf-8"))
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_USER, [NICK_EMAIL], msg.as_string())
        except Exception:
            pass
        sys.exit(1)

    if args.limit:
        rows = rows[:args.limit]

    log.info("Processing %d rows", len(rows))

    # Process each row
    stats = {}
    for i, row in enumerate(rows, start=1):
        if i % 25 == 0:
            log.info("Progress: %d/%d (%.0f%%)", i, len(rows), i / len(rows) * 100)
        status = process_row(row, dry_run=args.dry_run)
        stats[status] = stats.get(status, 0) + 1

    # Summary
    duration = (datetime.now() - t0).total_seconds()
    log.info("")
    log.info("=" * 60)
    log.info("DONE in %.0fs", duration)
    for k, v in sorted(stats.items(), key=lambda x: -x[1]):
        log.info("  %s: %d", k, v)
    log.info("=" * 60)

    # Send email
    if stats:
        send_summary_email(stats, args.dry_run, duration, tab_filter=args.tab)


if __name__ == "__main__":
    main()
