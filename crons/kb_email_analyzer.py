#!/usr/bin/env python3
"""
KB Email Analyzer — Nightly cron (23h) on Nitro.
Connects to IMAP, fetches emails from SAC-relevant folders,
classifies each with Haiku, pushes to Supabase kb_emails.

Processes ~1500 emails/night with 5 parallel Haiku workers.
Resumable: skips emails already in kb_emails (by email_msg_id).
"""

import imaplib
import email as email_lib
import json
import logging
import os
import re
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_config import (
    IMAP_SERVER, EMAIL_ACCOUNT, EMAIL_PASSWORD,
    PRIORITY_FOLDERS, MAX_PER_FOLDER,
    XGUARD_DOMAINS, XGUARD_EMAILS, IGNORE_SENDERS,
    MAX_EMAILS_PER_RUN, BATCH_SIZE, BATCH_PAUSE_SEC,
    MAX_WORKERS, MAX_CONSECUTIVE_FAILURES, HAIKU_TIMEOUT,
    sb_upsert, sb_get, sb_count,
)
from claude_scoring import call_claude_json

os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / f"kb_analyzer_{datetime.now():%Y-%m-%d}.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger("kb_analyzer")

BATCH_ID = f"kb_{datetime.now():%Y%m%d}_{uuid.uuid4().hex[:6]}"

# ---------------------------------------------------------------------------
# Haiku classification prompt (same as email_faq_builder.py)
# ---------------------------------------------------------------------------

CLASSIFY_PROMPT = """Tu es un analyste du service a la clientele de l'Academie XGuard (formation gardiennage/securite au Quebec).
Analyse cet email et extrais les informations suivantes.

EMAIL:
Dossier: {folder}
De: {from_addr}
Sujet: {subject}
Date: {date}
Corps: {body}

Reponds UNIQUEMENT en JSON:
{{
  "category": "inscription|info|paiement|plainte|annulation|changement_date|certificat|emploi|technique|spam|autre",
  "question": "la question principale du client en 1 phrase (ou null si pas de question)",
  "intent": "ce que le client veut (en 1 phrase courte)",
  "urgency": "haute|moyenne|basse",
  "needs_response": true/false,
  "suggested_response": "reponse courte suggeree (ou null si spam/pas de question)",
  "faq_topic": "sujet pour le FAQ (ex: prix, horaire, inscription en ligne, paiement, certificat BSP...)"
}}"""


# ---------------------------------------------------------------------------
# IMAP helpers
# ---------------------------------------------------------------------------

def _decode_header_val(raw):
    if not raw:
        return ""
    parts = decode_header(raw)
    decoded = []
    for val, charset in parts:
        if isinstance(val, bytes):
            decoded.append(val.decode(charset or "utf-8", errors="ignore"))
        else:
            decoded.append(str(val))
    return " ".join(decoded).strip()


def _extract_email(from_field):
    match = re.search(r'<([^>]+)>', from_field or "")
    return match.group(1).strip().lower() if match else (from_field or "").strip().lower()


def _is_skip_sender(from_addr):
    addr = from_addr.lower().strip()
    # Internal domains
    if "@" in addr:
        domain = addr.split("@")[-1]
        if domain in XGUARD_DOMAINS:
            return True
    # Specific emails
    if addr in XGUARD_EMAILS:
        return True
    # System senders
    for pattern in IGNORE_SENDERS:
        if pattern in addr:
            return True
    return False


# ---------------------------------------------------------------------------
# IMAP fetch — headers only pass, then body for unanalyzed
# ---------------------------------------------------------------------------

def fetch_candidate_emails(since_days=180):
    """
    Two-pass IMAP fetch:
    1) Headers-only from all priority folders (fast)
    2) Filter out already-analyzed (check Supabase)
    3) Fetch body only for new emails
    Returns list of email dicts ready for classification.
    """
    target_date = datetime.now() - timedelta(days=since_days)
    since_str = target_date.strftime("%d-%b-%Y")

    log.info("Connecting to IMAP...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)

    # Pass 1: Collect headers from all priority folders
    candidates = []  # (folder, imap_uid, msg_id, from, subject, date_str)

    for folder in PRIORITY_FOLDERS:
        try:
            status, _ = mail.select(f'"{folder}"', readonly=True)
            if status != "OK":
                continue

            status, msg_nums = mail.search(None, f'(SINCE "{since_str}")')
            if status != "OK" or not msg_nums[0]:
                continue

            nums = msg_nums[0].split()
            # Take last MAX_PER_FOLDER
            nums = nums[-MAX_PER_FOLDER:]

            for num in nums:
                try:
                    status, data = mail.fetch(
                        num,
                        "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID)])"
                    )
                    if status != "OK" or not data[0] or not data[0][1]:
                        continue

                    hdr = data[0][1].decode(errors="ignore") if isinstance(data[0][1], bytes) else str(data[0][1])

                    from_match = re.search(r'From:\s*(.+?)(?:\r?\n(?!\s)|$)', hdr, re.IGNORECASE | re.DOTALL)
                    subj_match = re.search(r'Subject:\s*(.+?)(?:\r?\n(?!\s)|$)', hdr, re.IGNORECASE | re.DOTALL)
                    date_match = re.search(r'Date:\s*(.+?)(?:\r?\n(?!\s)|$)', hdr, re.IGNORECASE | re.DOTALL)
                    msgid_match = re.search(r'Message-ID:\s*(<[^>]+>)', hdr, re.IGNORECASE)

                    from_raw = _decode_header_val(from_match.group(1).strip()) if from_match else ""
                    subject = _decode_header_val(subj_match.group(1).strip()) if subj_match else "(sans sujet)"
                    date_raw = date_match.group(1).strip() if date_match else ""
                    msg_id = msgid_match.group(1).strip() if msgid_match else ""

                    from_email = _extract_email(from_raw)

                    # Skip internal/system
                    if _is_skip_sender(from_email):
                        continue

                    # Need a msg_id for dedup
                    if not msg_id:
                        msg_id = f"<{folder}_{num.decode()}@generated>"

                    candidates.append({
                        "folder": folder,
                        "imap_num": num,
                        "msg_id": msg_id,
                        "from_addr": from_raw[:100],
                        "from_email": from_email,
                        "subject": subject[:200],
                        "date_raw": date_raw,
                    })
                except Exception:
                    pass

            log.info("  %s: %d candidates", folder, sum(1 for c in candidates if c["folder"] == folder))

        except Exception as e:
            log.warning("  Folder '%s' error: %s", folder, str(e)[:80])

    log.info("Pass 1 done: %d total candidates from %d folders", len(candidates), len(PRIORITY_FOLDERS))

    # Pass 2: Check which are already in Supabase
    existing_ids = set()
    try:
        # Fetch all existing msg_ids (paginated)
        offset = 0
        page_size = 1000
        while True:
            rows = sb_get(f"kb_emails?select=email_msg_id&offset={offset}&limit={page_size}")
            if not rows:
                break
            existing_ids.update(r["email_msg_id"] for r in rows)
            if len(rows) < page_size:
                break
            offset += page_size
        log.info("Already analyzed in Supabase: %d emails", len(existing_ids))
    except Exception as e:
        log.warning("Could not check existing: %s", e)

    new_candidates = [c for c in candidates if c["msg_id"] not in existing_ids]
    log.info("New to analyze: %d (skipping %d already done)", len(new_candidates), len(candidates) - len(new_candidates))

    # Limit to MAX_EMAILS_PER_RUN
    new_candidates = new_candidates[:MAX_EMAILS_PER_RUN]

    # Pass 3: Fetch body for new candidates
    log.info("Fetching email bodies for %d emails...", len(new_candidates))
    emails_with_body = []
    current_folder = None

    for c in new_candidates:
        try:
            if c["folder"] != current_folder:
                mail.select(f'"{c["folder"]}"', readonly=True)
                current_folder = c["folder"]

            status, data = mail.fetch(c["imap_num"], "(BODY.PEEK[TEXT])")
            body = ""
            if status == "OK" and data[0] and data[0][1]:
                raw_body = data[0][1]
                if isinstance(raw_body, bytes):
                    body = raw_body.decode(errors="ignore")
                else:
                    body = str(raw_body)

            # Clean and truncate body
            body = body.strip()[:800]

            # Parse date
            email_date = None
            try:
                email_date = parsedate_to_datetime(c["date_raw"]).isoformat()
            except Exception:
                pass

            emails_with_body.append({
                "msg_id": c["msg_id"],
                "folder": c["folder"],
                "from_addr": c["from_addr"],
                "subject": c["subject"],
                "date_raw": c["date_raw"],
                "email_date": email_date,
                "body": body,
            })
        except Exception:
            pass

    try:
        mail.logout()
    except Exception:
        pass

    log.info("Pass 3 done: %d emails with body ready for classification", len(emails_with_body))
    return emails_with_body


# ---------------------------------------------------------------------------
# Haiku classification
# ---------------------------------------------------------------------------

def classify_email(em):
    """Classify a single email with Haiku. Returns dict or None."""
    prompt = CLASSIFY_PROMPT.format(
        folder=em.get("folder", "INBOX"),
        from_addr=em["from_addr"][:50],
        subject=em["subject"][:100],
        date=em["date_raw"][:30],
        body=em["body"][:800],
    )
    result = call_claude_json(prompt, model="haiku", timeout=HAIKU_TIMEOUT)
    if result and isinstance(result, dict) and "category" in result:
        return result
    return None


def classify_and_push(em, idx=0):
    """Classify one email and push to Supabase. Returns True on success."""
    # Stagger start for parallel workers
    time.sleep(1.0 * (idx % MAX_WORKERS))

    result = classify_email(em)
    if not result:
        return False

    row = {
        "email_msg_id": em["msg_id"],
        "folder": em["folder"],
        "from_addr": em["from_addr"],
        "subject": em["subject"],
        "email_date": em.get("email_date"),
        "body_preview": (em.get("body") or "")[:500],
        "category": result.get("category", "autre"),
        "question": result.get("question"),
        "intent": result.get("intent"),
        "urgency": result.get("urgency", "basse"),
        "needs_response": result.get("needs_response", True),
        "suggested_response": result.get("suggested_response"),
        "faq_topic": result.get("faq_topic", "autre"),
        "batch_id": BATCH_ID,
    }
    resp = sb_upsert("kb_emails", row, on_conflict="email_msg_id")
    return resp is not None and resp.status_code in (200, 201)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    log.info("=" * 60)
    log.info("KB EMAIL ANALYZER — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("Batch: %s | Max: %d emails | Workers: %d", BATCH_ID, MAX_EMAILS_PER_RUN, MAX_WORKERS)
    log.info("=" * 60)

    # Log run start
    sb_upsert("kb_run_log", {
        "script": "kb_email_analyzer",
        "batch_id": BATCH_ID,
        "status": "running",
    })

    start_time = time.time()

    # Fetch candidate emails
    emails = fetch_candidate_emails(since_days=365)

    if not emails:
        log.info("No new emails to analyze. Done!")
        sb_upsert("kb_run_log", {
            "script": "kb_email_analyzer",
            "batch_id": BATCH_ID,
            "status": "completed",
            "finished_at": datetime.utcnow().isoformat() + "Z",
            "emails_fetched": 0,
            "emails_analyzed": 0,
            "details": json.dumps({"message": "no new emails"}),
        })
        return

    log.info("")
    log.info("--- Starting classification (%d emails) ---", len(emails))

    classified = 0
    failed = 0
    consecutive_failures = 0

    # Process in batches with ThreadPoolExecutor
    for batch_start in range(0, len(emails), BATCH_SIZE):
        batch = emails[batch_start:batch_start + BATCH_SIZE]
        batch_ok = 0
        batch_fail = 0

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = {
                executor.submit(classify_and_push, em, idx): em
                for idx, em in enumerate(batch)
            }
            for future in as_completed(futures):
                em = futures[future]
                try:
                    success = future.result()
                    if success:
                        batch_ok += 1
                        consecutive_failures = 0
                    else:
                        batch_fail += 1
                        consecutive_failures += 1
                except Exception as e:
                    batch_fail += 1
                    consecutive_failures += 1
                    log.warning("  Error classifying '%s': %s", em.get("subject", "?")[:30], e)

        classified += batch_ok
        failed += batch_fail

        pct = (batch_start + len(batch)) / len(emails) * 100
        log.info("  Batch %d-%d: %d ok, %d fail | Total: %d/%d (%.0f%%)",
                 batch_start, batch_start + len(batch), batch_ok, batch_fail,
                 classified, len(emails), pct)

        # Rate limit detection
        if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            log.warning("RATE LIMIT DETECTED — %d consecutive failures. Stopping.", consecutive_failures)
            break

        # Batch failure detection (>80% fail = stop)
        if batch_fail > 0 and batch_ok == 0 and len(batch) >= 5:
            log.warning("FULL BATCH FAILURE — possible rate limit. Stopping.")
            break

        # Pause between batches
        if batch_start + BATCH_SIZE < len(emails):
            time.sleep(BATCH_PAUSE_SEC)

    elapsed = time.time() - start_time
    log.info("")
    log.info("=" * 60)
    log.info("DONE — %d classified, %d failed in %.0f seconds (%.1f min)",
             classified, failed, elapsed, elapsed / 60)
    log.info("Total in kb_emails: %d", sb_count("kb_emails"))
    log.info("=" * 60)

    # Log run completion
    sb_upsert("kb_run_log", {
        "script": "kb_email_analyzer",
        "batch_id": BATCH_ID,
        "status": "completed" if consecutive_failures < MAX_CONSECUTIVE_FAILURES else "paused",
        "finished_at": datetime.utcnow().isoformat() + "Z",
        "emails_fetched": len(emails),
        "emails_analyzed": classified,
        "emails_failed": failed,
        "details": json.dumps({
            "elapsed_sec": round(elapsed),
            "rate_per_min": round(classified / (elapsed / 60), 1) if elapsed > 0 else 0,
        }),
    })


if __name__ == "__main__":
    main()
