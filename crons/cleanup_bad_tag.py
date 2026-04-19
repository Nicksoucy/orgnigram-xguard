"""
One-time cleanup: remove the wrong 'xguard paid' tag from contacts
that got it by mistake from google_sheets_sync.py earlier today.

We'll read the Supabase sync log for today's tagged contacts and
remove the wrong tag. We'll NOT add 'gard paid' here — the next
full sync run will handle that properly.
"""

import logging
import os
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

from kb_config import sb_get
from ghl_helpers import ghl_remove_tag, ghl_get_contact, ghl_has_tag

WRONG_TAG = "xguard paid"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cleanup")


def main():
    # Fetch contacts tagged today
    today = date.today().isoformat()
    rows = sb_get(
        f"google_sheets_sync_log?run_date=eq.{today}&status=eq.tagged"
        f"&select=email,contact_id&order=run_started_at"
    )

    log.info("Found %d contacts that got the wrong tag today", len(rows))
    if not rows:
        return

    removed = 0
    skipped = 0
    errors = 0

    for i, row in enumerate(rows, start=1):
        contact_id = row.get("contact_id")
        email = row.get("email")
        if not contact_id:
            continue

        # Get contact to confirm it has the wrong tag
        contact = ghl_get_contact(contact_id)
        if not contact:
            log.warning("[%d] %s: contact not found", i, email)
            errors += 1
            continue

        if not ghl_has_tag(contact, WRONG_TAG):
            log.info("[%d] %s: already clean (no '%s' tag)", i, email, WRONG_TAG)
            skipped += 1
            continue

        # Remove wrong tag
        ok = ghl_remove_tag(contact_id, WRONG_TAG)
        if ok:
            log.info("[%d/%d] %s: removed '%s'", i, len(rows), email, WRONG_TAG)
            removed += 1
        else:
            log.error("[%d/%d] %s: remove failed", i, len(rows), email)
            errors += 1

    log.info("")
    log.info("DONE: removed=%d, already_clean=%d, errors=%d", removed, skipped, errors)


if __name__ == "__main__":
    main()
