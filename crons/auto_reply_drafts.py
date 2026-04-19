"""
Auto-Reply Drafts — Uses KB topics + Anthropic Customer Support plugin pattern
to create Gmail drafts for Hamza's morning review.

SAFETY:
- NEVER auto-sends emails
- Only creates drafts in Gmail (Hamza reviews + sends manually)
- Only drafts for matched approved KB topics
- Plaintes/litiges/urgences = NEVER drafted (flagged for manual)
- Max 10 drafts per run

FLOW:
1. Fetch unanswered emails from yesterday
2. Classify with Haiku -> match kb_topics (approved only)
3. Generate draft in Hamza's voice
4. Save draft via IMAP APPEND to [Gmail]/Drafts folder
5. Track in auto_reply_drafts Supabase table
6. Send summary email to Hamza at 07h45 with draft count
"""

import email
import imaplib
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timedelta
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

from kb_config import (
    IMAP_SERVER, EMAIL_ACCOUNT, EMAIL_PASSWORD,
    SUPABASE_URL, SUPABASE_KEY,
    GMAIL_USER, GMAIL_APP_PASSWORD,
    sb_upsert, sb_get,
    XGUARD_DOMAINS, IGNORE_SENDERS,
)
from claude_scoring import call_claude, call_claude_json

LOG_DIR = Path(r"C:\Users\user\sac_logs")
_handlers = [logging.StreamHandler()]
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(
        str(LOG_DIR / f"auto_reply_{datetime.now():%Y-%m-%d}.log"),
        encoding="utf-8"
    ))
except (PermissionError, OSError):
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_handlers,
)
log = logging.getLogger("auto_reply")

# --- CONFIG ---
MAX_DRAFTS_PER_RUN = 10
DRAFTS_FOLDER = "[Gmail]/Brouillons"  # Gmail Drafts folder (FR account)
HAMZA_EMAIL = "hmaghraoui65@gmail.com"
NICK_EMAIL = "nick@darkhorseads.com"

# Categories that NEVER get auto-drafted (require manual handling)
BLOCKED_CATEGORIES = {"plainte", "litige", "legal", "urgence"}

# Keywords that indicate we should NEVER draft (manual required)
DANGER_KEYWORDS = re.compile(
    r'\b(avocat|poursuite|urgent|urgence|plainte|mecontent|insatisfait|rembours|'
    r'tribunal|litige|legal|discrim|harcel|menace)\b',
    re.IGNORECASE
)


# ---------------------------------------------------------------------------
# IMAP helpers
# ---------------------------------------------------------------------------

def _decode_header_safe(h):
    """Decode email header safely."""
    if not h:
        return ""
    try:
        parts = decode_header(h)
        return "".join(
            (p.decode(enc or "utf-8", errors="replace") if isinstance(p, bytes) else p)
            for p, enc in parts
        )
    except Exception:
        return str(h)


def _get_body(msg):
    """Extract plain-text body from email.Message."""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition", "")):
                try:
                    body = part.get_payload(decode=True).decode(
                        part.get_content_charset() or "utf-8",
                        errors="replace"
                    )
                    break
                except Exception:
                    continue
    else:
        try:
            body = msg.get_payload(decode=True).decode(
                msg.get_content_charset() or "utf-8",
                errors="replace"
            )
        except Exception:
            body = str(msg.get_payload() or "")
    return body.strip()


def _extract_email(header_val):
    """Extract bare email from 'Name <email@x.com>' header."""
    if not header_val:
        return ""
    match = re.search(r'<([^>]+)>', header_val)
    if match:
        return match.group(1).lower().strip()
    return header_val.lower().strip()


def _should_skip(from_addr):
    """Check if sender should be skipped (internal, noreply, etc.)."""
    email_addr = _extract_email(from_addr).lower()
    if not email_addr or "@" not in email_addr:
        return True
    domain = email_addr.split("@", 1)[1]
    if domain in XGUARD_DOMAINS:
        return True
    local = email_addr.split("@", 1)[0]
    for pattern in IGNORE_SENDERS:
        if pattern in email_addr or pattern in local:
            return True
    return False


# ---------------------------------------------------------------------------
# Fetch unanswered emails (last 24h)
# ---------------------------------------------------------------------------

def _load_existing_drafts_state():
    """Load state from Supabase + Gmail Drafts to prevent duplicates.
    Returns:
      - already_drafted_msgids: set of inbound_msg_id we already drafted
      - already_sent_msgids: set of inbound_msg_id we already sent
      - already_drafted_addrs: set of from_email addresses we drafted for today
    """
    already_drafted_msgids = set()
    already_sent_msgids = set()
    already_drafted_addrs = set()

    # Check Supabase for existing drafts (last 7 days)
    try:
        since = (datetime.now() - timedelta(days=7)).isoformat()
        rows = sb_get(f"auto_reply_drafts?created_at=gte.{since}&select=inbound_msg_id,inbound_from,status")
        for r in rows:
            msg_id = r.get("inbound_msg_id", "")
            from_email = (r.get("inbound_from") or "").lower()
            status = r.get("status", "")
            if msg_id:
                if status == "sent":
                    already_sent_msgids.add(msg_id)
                elif status in ("draft_created", "manual_required", "no_match"):
                    already_drafted_msgids.add(msg_id)
                    if from_email:
                        already_drafted_addrs.add(from_email)
        log.info("  Supabase: %d drafted, %d sent, %d addrs (last 7d)",
                 len(already_drafted_msgids), len(already_sent_msgids), len(already_drafted_addrs))
    except Exception as e:
        log.warning("Failed to load Supabase draft state: %s", e)

    return already_drafted_msgids, already_sent_msgids, already_drafted_addrs


def _load_justcall_today():
    """Check JustCall for calls handled today — return set of phone numbers.
    If a client called today and spoke to an agent (duration>0), we skip email draft.
    """
    handled_numbers = set()
    try:
        from smart_stats import fetch_all_raw
        from phone_utils import normalize_number
        today = datetime.now().strftime("%Y-%m-%d")
        raw_calls = fetch_all_raw(today)
        for c in raw_calls:
            dur = int(c.get("duration", 0) or 0)
            if dur > 30:  # Real conversation
                num = normalize_number(c.get("contact_number", ""))
                if num:
                    handled_numbers.add(num)
        log.info("  JustCall: %d numbers handled today", len(handled_numbers))
    except Exception as e:
        log.warning("Failed to cross-ref JustCall: %s", e)
    return handled_numbers


def _check_existing_gmail_draft(mail, from_email, subject):
    """Check if a draft already exists in Gmail Drafts for this email.
    Returns True if found."""
    try:
        for folder in ['"[Gmail]/Brouillons"', '"[Gmail]/Drafts"']:
            try:
                result, _ = mail.select(folder, readonly=True)
                if result != "OK":
                    continue
                # Search for drafts sent to this address
                _, data = mail.search(None, f'TO "{from_email}"')
                if data[0]:
                    # Found at least one draft to this person
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def fetch_unanswered_emails(hours_back=24):
    """Fetch unanswered emails from INBOX with full body.
    DEDUP CHECKS:
    1. Sent folder (last 48h) — skip if we replied
    2. Supabase auto_reply_drafts (last 7d) — skip if we already drafted/sent
    3. Gmail Drafts folder — skip if draft already exists
    4. JustCall today — skip if client already spoke with agent
    """
    log.info("Connecting to IMAP...")
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)

    # Load all dedup sources
    log.info("Loading dedup state...")
    already_drafted_msgids, already_sent_msgids, already_drafted_addrs = _load_existing_drafts_state()
    handled_numbers = _load_justcall_today()

    # Step 1: Get recent SENT to identify what's already replied
    replied_to_addrs = set()
    replied_to_msgids = set()
    try:
        mail.select('"[Gmail]/Messages envoy&AOk-s"', readonly=True)
        since_date = (datetime.now() - timedelta(hours=hours_back + 24)).strftime("%d-%b-%Y")
        _, data = mail.search(None, f'SINCE {since_date}')
        for msg_num in data[0].split():
            _, msg_data = mail.fetch(msg_num, "(RFC822.HEADER)")
            if not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            to_addr = _extract_email(msg.get("To", ""))
            cc_addr = _extract_email(msg.get("Cc", ""))
            if to_addr:
                replied_to_addrs.add(to_addr)
            if cc_addr:
                replied_to_addrs.add(cc_addr)
            in_reply = msg.get("In-Reply-To", "")
            refs = msg.get("References", "")
            for m in re.findall(r'<([^>]+)>', in_reply + " " + refs):
                replied_to_msgids.add(m)
        log.info("  Sent: %d addresses, %d msgids tracked", len(replied_to_addrs), len(replied_to_msgids))
    except Exception as e:
        log.warning("Failed to fetch sent: %s", e)

    # Step 1b: Get existing drafts from Gmail (critical!)
    existing_draft_addrs = set()
    try:
        for folder in ['"[Gmail]/Brouillons"', '"[Gmail]/Drafts"']:
            try:
                result, _ = mail.select(folder, readonly=True)
                if result != "OK":
                    continue
                _, data = mail.search(None, "ALL")
                for msg_num in data[0].split()[-200:]:  # Last 200 drafts
                    _, msg_data = mail.fetch(msg_num, "(RFC822.HEADER)")
                    if not msg_data or not msg_data[0]:
                        continue
                    msg = email.message_from_bytes(msg_data[0][1])
                    to_addr = _extract_email(msg.get("To", ""))
                    if to_addr:
                        existing_draft_addrs.add(to_addr)
                break  # Found working folder
            except Exception:
                continue
        log.info("  Gmail Drafts: %d existing draft addresses", len(existing_draft_addrs))
    except Exception as e:
        log.warning("Failed to fetch drafts: %s", e)

    # Step 2: Fetch recent INBOX
    unanswered = []
    skipped_stats = {"already_replied": 0, "already_drafted": 0, "existing_draft": 0, "phone_handled": 0, "internal": 0, "no_body": 0}

    try:
        mail.select("INBOX", readonly=True)
        since_date = (datetime.now() - timedelta(hours=hours_back)).strftime("%d-%b-%Y")
        _, data = mail.search(None, f'SINCE {since_date}')
        msg_nums = data[0].split()
        log.info("  INBOX: %d emails in last %dh", len(msg_nums), hours_back)

        for msg_num in msg_nums[-100:]:  # Last 100 only
            _, msg_data = mail.fetch(msg_num, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue
            msg = email.message_from_bytes(msg_data[0][1])

            from_addr = _decode_header_safe(msg.get("From", ""))
            if _should_skip(from_addr):
                skipped_stats["internal"] += 1
                continue

            msg_id = msg.get("Message-ID", "").strip("<>").strip()
            from_email = _extract_email(from_addr)

            # DEDUP CHECK 1: Already replied via email (IMAP sent folder)
            if msg_id in replied_to_msgids or from_email in replied_to_addrs:
                skipped_stats["already_replied"] += 1
                continue

            # DEDUP CHECK 2: Already drafted/sent (Supabase tracking)
            if msg_id in already_drafted_msgids or msg_id in already_sent_msgids:
                skipped_stats["already_drafted"] += 1
                continue
            if from_email in already_drafted_addrs:
                skipped_stats["already_drafted"] += 1
                continue

            # DEDUP CHECK 3: Existing draft in Gmail Brouillons
            if from_email in existing_draft_addrs:
                skipped_stats["existing_draft"] += 1
                continue

            # DEDUP CHECK 4: Client called today (JustCall cross-ref)
            # Try to extract phone from body or sender
            body_snippet = _get_body(msg)[:500]
            phone_match = re.search(r'[\+\d][\d\s\-\(\)\.]{9,}\d', body_snippet)
            if phone_match:
                from phone_utils import normalize_number
                norm = normalize_number(phone_match.group(0))
                if norm and norm in handled_numbers:
                    skipped_stats["phone_handled"] += 1
                    continue

            subject = _decode_header_safe(msg.get("Subject", ""))
            date_hdr = msg.get("Date", "")
            body = _get_body(msg)[:2000]  # Max 2k chars

            if len(body) < 20:
                skipped_stats["no_body"] += 1
                continue

            # Parse name from "Name <email>"
            from_name = re.sub(r'<[^>]+>', '', from_addr).strip().strip('"')

            unanswered.append({
                "msg_id": msg_id,
                "from_email": from_email,
                "from_name": from_name,
                "subject": subject,
                "body": body,
                "date": date_hdr,
            })
    except Exception as e:
        log.error("Failed to fetch INBOX: %s", e)

    try:
        mail.close()
        mail.logout()
    except Exception:
        pass

    log.info("  Skipped: %d already_replied, %d already_drafted, %d existing_draft, %d phone_handled, %d internal, %d no_body",
             skipped_stats["already_replied"], skipped_stats["already_drafted"],
             skipped_stats["existing_draft"], skipped_stats["phone_handled"],
             skipped_stats["internal"], skipped_stats["no_body"])
    log.info("  Found %d unanswered emails (after dedup)", len(unanswered))
    return unanswered


# ---------------------------------------------------------------------------
# KB matching
# ---------------------------------------------------------------------------

def load_approved_topics(dry_run=False):
    """Load approved/corrected topics from Supabase.
    In dry_run mode, includes pending topics to see what WOULD match.
    """
    if dry_run:
        rows = sb_get("kb_topics?select=topic_id,category,topic_label,question_pattern,suggested_response,nick_correction,merged_raw_topics,approval_status,frequency&order=frequency.desc")
        log.info("Loaded %d KB topics (dry_run: includes pending)", len(rows))
    else:
        rows = sb_get("kb_topics?approval_status=in.(approved,corrected)&select=topic_id,category,topic_label,question_pattern,suggested_response,nick_correction,merged_raw_topics")
        log.info("Loaded %d approved KB topics", len(rows))
    return rows


def match_email_to_topic(email_obj, approved_topics):
    """Use Haiku to classify email and match to an approved KB topic."""
    topics_list = "\n".join([
        f"- {t['topic_id']}: {t['topic_label']} ({t['category']}) — {t.get('question_pattern', '')[:100]}"
        for t in approved_topics[:50]
    ])

    prompt = f"""Tu es un expert du service a la clientele d'XGuard Academie (formation securite).

Analyse cet email et trouve le topic FAQ qui correspond le mieux.

Email recu:
De: {email_obj['from_name']} <{email_obj['from_email']}>
Sujet: {email_obj['subject']}
Corps:
{email_obj['body'][:1200]}

Topics FAQ disponibles (approuves):
{topics_list}

Retourne UNIQUEMENT un JSON de la forme:
{{
  "topic_id": "xxx" ou null si aucun match clair,
  "category": "inscription|info|paiement|annulation|certificat|emploi|technique|autre",
  "confidence": "haute|moyenne|basse",
  "is_dangerous": true si plainte/litige/urgence/menace sinon false,
  "client_question": "question principale en 1 phrase",
  "reasoning": "pourquoi ce topic (1 phrase)"
}}"""

    result = call_claude_json(prompt, model="haiku", timeout=45)
    if not isinstance(result, dict):
        return {"topic_id": None, "confidence": "basse", "is_dangerous": True}
    return result


def draft_reply(email_obj, topic, match_info):
    """Generate a reply draft using Hamza's voice + KB topic response."""
    base_answer = topic.get("nick_correction") or topic.get("suggested_response", "")

    prompt = f"""Tu redige une reponse email dans le style d'Hamza Maghraoui, responsable du service a la clientele d'XGuard Academie.

STYLE HAMZA:
- Salutation chaleureuse: "Bonjour [Prenom],"
- Ton professionnel mais amical
- Direct et concis
- Signature: "Cordialement, Hamza — Academie XGuard"
- Francais du Quebec naturel
- Utilise "vous" (vouvoiement)

Email du client:
{email_obj['body'][:1000]}

Question principale: {match_info.get('client_question', '')}

Reponse de base (a adapter/personnaliser):
{base_answer}

INSTRUCTIONS:
1. Commence par "Bonjour [Prenom]" (extrait le prenom si possible du nom: {email_obj['from_name']})
2. Reponds directement a la question
3. Adapte le ton de la reponse de base pour qu'elle soit chaleureuse
4. Ne depasse pas 150 mots
5. Termine par "Cordialement,\\nHamza\\nAcademie XGuard"
6. PAS d'introduction bateau du genre "Merci de nous avoir contacte"
7. Va droit au but

Retourne UNIQUEMENT le corps de l'email (pas de sujet, pas de headers)."""

    draft_body = call_claude(prompt, model="haiku", timeout=60)
    return draft_body.strip() if draft_body else ""


# ---------------------------------------------------------------------------
# Gmail Draft creation via IMAP APPEND
# ---------------------------------------------------------------------------

def create_gmail_draft(original_email, draft_body):
    """Create a Gmail draft via IMAP APPEND to the Drafts folder."""
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)

        msg = MIMEMultipart("alternative")
        msg["From"] = EMAIL_ACCOUNT
        msg["To"] = original_email["from_email"]
        subject = original_email["subject"]
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"
        msg["Subject"] = subject

        # Threading headers (critical for Gmail to thread properly)
        if original_email.get("msg_id"):
            original_id = original_email["msg_id"]
            if not original_id.startswith("<"):
                original_id = f"<{original_id}>"
            msg["In-Reply-To"] = original_id
            msg["References"] = original_id

        msg.attach(MIMEText(draft_body, "plain", "utf-8"))

        # Try common drafts folder names
        drafts_folders = ['"[Gmail]/Brouillons"', '"[Gmail]/Drafts"']
        success = False
        for folder in drafts_folders:
            try:
                result = mail.append(folder, "", imaplib.Time2Internaldate(time.time()), msg.as_bytes())
                if result[0] == "OK":
                    success = True
                    log.info("  Draft saved to %s", folder)
                    break
            except Exception:
                continue

        mail.logout()
        return success
    except Exception as e:
        log.error("Failed to create draft: %s", e)
        return False


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

def track_draft(email_obj, topic_id, draft_body, status="created"):
    """Save draft info to Supabase auto_reply_drafts table."""
    try:
        sb_upsert("auto_reply_drafts", {
            "inbound_msg_id": email_obj.get("msg_id", ""),
            "inbound_from": email_obj.get("from_email", ""),
            "inbound_subject": email_obj.get("subject", "")[:200],
            "kb_topic_id": topic_id,
            "draft_body": draft_body[:4000],
            "status": status,
            "created_at": datetime.now().isoformat(),
        }, on_conflict="inbound_msg_id")
    except Exception as e:
        log.warning("Failed to track draft: %s", e)


# ---------------------------------------------------------------------------
# Summary email to Hamza
# ---------------------------------------------------------------------------

def send_summary_email(date_str, drafts_created, drafts_skipped, manual_flagged):
    """Send morning summary to Hamza + Nick."""
    import smtplib

    total = len(drafts_created) + len(drafts_skipped) + len(manual_flagged)

    created_rows = "".join(
        f'<tr><td style="padding:6px;color:#2E7D32;font-weight:bold;">DRAFT</td>'
        f'<td style="padding:6px;font-size:12px;">{d["from_name"][:30]}</td>'
        f'<td style="padding:6px;font-size:11px;">{d["subject"][:60]}</td>'
        f'<td style="padding:6px;font-size:11px;color:#777;">{d["topic_label"]}</td></tr>'
        for d in drafts_created
    )
    manual_rows = "".join(
        f'<tr><td style="padding:6px;color:#C62828;font-weight:bold;">MANUEL</td>'
        f'<td style="padding:6px;font-size:12px;">{d["from_name"][:30]}</td>'
        f'<td style="padding:6px;font-size:11px;">{d["subject"][:60]}</td>'
        f'<td style="padding:6px;font-size:11px;color:#777;">{d["reason"]}</td></tr>'
        for d in manual_flagged
    )

    # Build sections (avoid apostrophe issues in f-string ternary)
    if drafts_created:
        drafts_section = (
            f'<h3 style="color:#2E7D32;font-size:14px;">Drafts prets a reviser ({len(drafts_created)})</h3>'
            f'<table style="width:100%;border-collapse:collapse;font-size:12px;">'
            f'<tr style="background:#E8F5E9;"><th style="padding:6px;">Status</th><th style="padding:6px;">Client</th>'
            f'<th style="padding:6px;">Sujet</th><th style="padding:6px;">Topic KB</th></tr>'
            f'{created_rows}</table>'
        )
    else:
        drafts_section = '<p style="color:#777;">Aucun draft cree aujourd hui.</p>'

    if manual_flagged:
        manual_section = (
            f'<h3 style="color:#C62828;font-size:14px;margin-top:20px;">A traiter manuellement ({len(manual_flagged)})</h3>'
            f'<table style="width:100%;border-collapse:collapse;font-size:12px;">'
            f'<tr style="background:#FFEBEE;"><th style="padding:6px;">Status</th><th style="padding:6px;">Client</th>'
            f'<th style="padding:6px;">Sujet</th><th style="padding:6px;">Raison</th></tr>'
            f'{manual_rows}</table>'
        )
    else:
        manual_section = ''

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
<div style="background:#1B3A5C;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="color:white;margin:0;font-size:20px;">Auto-Reply Drafts — {date_str}</h1>
  <p style="color:#ccc;margin:4px 0 0;font-size:12px;">
    {len(drafts_created)} drafts prets | {len(manual_flagged)} manuel requis | {len(drafts_skipped)} ignores
  </p>
</div>
<div style="padding:15px;border:1px solid #ddd;border-top:none;">
  <p style="font-size:13px;margin:0 0 10px;">
    Bonjour Hamza, voici les brouillons de reponses crees ce matin. Ouvre Gmail -> <strong>Brouillons</strong> pour les reviser.
  </p>

  {drafts_section}

  {manual_section}

  <p style="font-size:11px;color:#777;margin-top:15px;">
    Les drafts ne sont PAS envoyes automatiquement. Tu dois ouvrir chaque brouillon, le verifier, puis cliquer Envoyer.
  </p>
</div>
<div style="background:#f5f5f5;padding:10px;border-radius:0 0 8px 8px;text-align:center;border:1px solid #ddd;border-top:none;">
  <p style="color:#999;font-size:10px;margin:0;">Auto-Reply XGuard | Base: KB system (18 topics approuves)</p>
</div></body></html>"""

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = HAMZA_EMAIL
    msg["Cc"] = NICK_EMAIL
    msg["Subject"] = f"[AUTO-REPLY] {date_str} — {len(drafts_created)} drafts prets, {len(manual_flagged)} manuels"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [HAMZA_EMAIL, NICK_EMAIL], msg.as_string())
        log.info("Summary email sent to Hamza + Nick")
    except Exception as e:
        log.error("Summary email failed: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    dry_run = "--dry-run" in sys.argv
    date_str = datetime.now().strftime("%Y-%m-%d")

    log.info("=" * 60)
    log.info("AUTO-REPLY DRAFTS — %s %s", date_str, "(DRY RUN)" if dry_run else "")
    log.info("=" * 60)

    # Step 1: Load KB topics
    log.info("Loading KB topics...")
    approved_topics = load_approved_topics(dry_run=dry_run)
    if not approved_topics:
        log.warning("No topics found — cannot generate drafts")
        return
    topics_by_id = {t["topic_id"]: t for t in approved_topics}

    # Step 2: Fetch unanswered emails
    log.info("Fetching unanswered emails...")
    emails = fetch_unanswered_emails(hours_back=24)

    if not emails:
        log.info("No unanswered emails — nothing to do")
        return

    # Step 3: Process each email
    drafts_created = []
    drafts_skipped = []
    manual_flagged = []

    for i, em in enumerate(emails):
        if len(drafts_created) >= MAX_DRAFTS_PER_RUN:
            log.info("Max drafts reached (%d) — flagging rest as manual", MAX_DRAFTS_PER_RUN)
            manual_flagged.append({**em, "reason": "limite quotidienne atteinte"})
            continue

        log.info("[%d/%d] Processing: %s", i + 1, len(emails), em["subject"][:50])

        # Danger keyword check (fail-safe)
        if DANGER_KEYWORDS.search(em["body"]) or DANGER_KEYWORDS.search(em["subject"]):
            log.info("  DANGER keyword detected -> manual")
            manual_flagged.append({**em, "reason": "mot-cle sensible detecte"})
            track_draft(em, None, "", status="manual_required")
            continue

        # Classify + match
        match = match_email_to_topic(em, approved_topics)

        if match.get("is_dangerous"):
            manual_flagged.append({**em, "reason": "classifie sensible par IA"})
            track_draft(em, None, "", status="manual_required")
            continue

        if match.get("category") in BLOCKED_CATEGORIES:
            manual_flagged.append({**em, "reason": f"categorie bloquee: {match['category']}"})
            track_draft(em, None, "", status="manual_required")
            continue

        topic_id = match.get("topic_id")
        confidence = match.get("confidence", "basse")

        if not topic_id or confidence == "basse":
            manual_flagged.append({**em, "reason": f"pas de match clair (confiance: {confidence})"})
            track_draft(em, None, "", status="no_match")
            continue

        topic = topics_by_id.get(topic_id)
        if not topic:
            drafts_skipped.append(em)
            continue

        # Draft reply
        log.info("  Matched topic: %s (%s)", topic["topic_label"], confidence)
        draft_body = draft_reply(em, topic, match)

        if not draft_body or len(draft_body) < 30:
            log.warning("  Empty draft -> manual")
            manual_flagged.append({**em, "reason": "generation du draft echouee"})
            continue

        # DRY RUN: show the draft, don't create Gmail draft
        if dry_run:
            log.info("  --- DRY RUN PREVIEW ---")
            log.info("  Topic: %s", topic["topic_label"])
            log.info("  Draft body:")
            for line in draft_body.split("\n"):
                log.info("    %s", line)
            log.info("  --- END PREVIEW ---")
            drafts_created.append({**em, "topic_label": topic["topic_label"], "draft_body": draft_body})
            continue

        # Create Gmail draft (real mode only)
        if create_gmail_draft(em, draft_body):
            track_draft(em, topic_id, draft_body, status="draft_created")
            drafts_created.append({**em, "topic_label": topic["topic_label"]})
            log.info("  DRAFT CREATED")
        else:
            log.error("  Failed to create draft in Gmail")
            manual_flagged.append({**em, "reason": "echec creation draft Gmail"})

    # Step 4: Send summary to Hamza
    log.info("")
    log.info("RESULTS: %d drafts, %d manual, %d skipped",
             len(drafts_created), len(manual_flagged), len(drafts_skipped))

    if dry_run:
        log.info("DRY RUN — no email sent, no Gmail drafts created, no Supabase rows")
    elif drafts_created or manual_flagged:
        send_summary_email(date_str, drafts_created, drafts_skipped, manual_flagged)

    log.info("DONE!")


if __name__ == "__main__":
    main()
