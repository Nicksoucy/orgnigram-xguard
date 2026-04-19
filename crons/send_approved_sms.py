#!/usr/bin/env python3
"""
send_approved_sms.py — Dispatcher for approved SMS.

Runs every 30 minutes. Polls Telegram for new approvals/rejections,
then sends any SMS that has been approved via the approval workflow.

Flow:
  1. poll_once() — check Telegram for button clicks / commands
  2. For each row in pending_sms_approvals with status='approved':
     - Validate SMS one more time (sms_validator)
     - Send via JustCall
     - On success: status='sent', write GHL note, update prospects_intelligence
     - On failure: status='error', log, Telegram notification

Safety: also processes 'expired' — if approval is >24h old and still pending,
marks as expired (doesn't send, doesn't bother user).
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

from kb_config import sb_get, sb_patch
from sms_validator import validate_sms
from ghl_helpers import ghl_log_action

# JustCall SMS config
JUSTCALL_API_KEY = "daf60d953694336f07c84c74205eb311dd85c996"
JUSTCALL_API_SECRET = "20612f8fcb80ef33845cbdc226bc8174853c82dd"
JUSTCALL_FROM = "14388020475"

LOG_DIR = Path(r"C:\Users\user\sac_logs")
_handlers = [logging.StreamHandler()]
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(
        str(LOG_DIR / f"sms_dispatcher_{datetime.now():%Y-%m-%d}.log"),
        encoding="utf-8",
    ))
except (PermissionError, OSError):
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_handlers,
)
log = logging.getLogger("sms_dispatcher")


EXPIRY_HOURS = 24


def send_sms_via_justcall(phone, body):
    """Send SMS via JustCall. Returns (ok, response_text)."""
    url = "https://api.justcall.io/v1/texts/new"
    headers = {
        "Authorization": f"{JUSTCALL_API_KEY}:{JUSTCALL_API_SECRET}",
        "Content-Type": "application/json",
    }
    to_number = phone if phone.startswith("1") else f"1{phone}"
    payload = {"from": JUSTCALL_FROM, "to": to_number, "body": body}
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        return r.status_code in (200, 201), r.text[:500]
    except Exception as e:
        return False, f"Exception: {e}"


def expire_old_pending():
    """Mark approvals older than EXPIRY_HOURS as expired."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=EXPIRY_HOURS)).isoformat()
    rows = sb_get(f"pending_sms_approvals?status=eq.pending&created_at=lt.{cutoff}&select=id")
    if not rows or isinstance(rows, dict):
        return 0
    for r in rows:
        sb_patch("pending_sms_approvals", f"id=eq.{r['id']}",
                 {"status": "expired", "decided_at": datetime.now().isoformat()})
    if rows:
        log.info("Expired %d old pending approvals", len(rows))
    return len(rows)


def process_approved_sms():
    """Fetch approved SMS and send them via JustCall."""
    rows = sb_get("pending_sms_approvals?status=eq.approved&order=id&limit=50")
    if not rows or isinstance(rows, dict):
        return 0

    sent_count = 0
    error_count = 0

    for approval in rows:
        approval_id = approval["id"]
        phone = approval["phone_number"]
        sms_body = approval["sms_body"]
        name = approval.get("contact_name", "")
        ghl_id = approval.get("ghl_contact_id")
        priority = approval.get("priority", "")
        context = approval.get("context_summary", "")

        log.info("[%d] Sending to %s (%s)", approval_id, name or phone, phone)

        # Re-validate (in case the validator rules changed)
        ok, reason = validate_sms(sms_body)
        if not ok:
            log.error("  Validation FAILED at dispatch: %s", reason)
            sb_patch("pending_sms_approvals", f"id=eq.{approval_id}",
                     {"status": "error", "send_error": f"Validator rejected: {reason}"})
            error_count += 1
            continue

        # Send
        success, resp = send_sms_via_justcall(phone, sms_body)
        if success:
            log.info("  SMS SENT")
            sb_patch("pending_sms_approvals", f"id=eq.{approval_id}",
                     {"status": "sent", "sent_at": datetime.now().isoformat()})

            # GHL note
            if ghl_id:
                try:
                    ghl_log_action(
                        ghl_id,
                        action=f"SMS envoye (approuve) — {priority}",
                        details=f"Approval #{approval_id}\nContexte: {context}\n\nMessage:\n{sms_body}",
                    )
                except Exception as e:
                    log.warning("  GHL note add failed: %s", e)

            sent_count += 1
            time.sleep(1.5)  # Rate limit
        else:
            log.error("  SMS FAILED: %s", resp[:200])
            sb_patch("pending_sms_approvals", f"id=eq.{approval_id}",
                     {"status": "error", "send_error": resp[:500]})
            error_count += 1

    log.info("Dispatch: %d sent, %d errors", sent_count, error_count)
    return sent_count


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-poll", action="store_true",
                        help="Skip Telegram polling (only dispatch approved)")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("SMS DISPATCHER — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 60)

    # Expire old pending
    expire_old_pending()

    # Poll Telegram for button clicks / commands
    if not args.no_poll:
        try:
            from telegram_bot import poll_once
            n = poll_once()
            if n > 0:
                log.info("Processed %d Telegram updates", n)
        except Exception as e:
            log.warning("Telegram poll failed (non-critical): %s", e)

    # Dispatch approved SMS
    sent = process_approved_sms()
    log.info("DONE — %d SMS sent", sent)


if __name__ == "__main__":
    main()
