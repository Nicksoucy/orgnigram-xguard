"""
Email FAQ Builder — Analyzes 6 months of emails to build a comprehensive FAQ.
Runs nightly at 23h on Nitro. Processes emails in batches to respect rate limits.
Uses Haiku to classify each email, then aggregates into FAQ categories.
Saves progress to resume if interrupted.
"""

import imaplib
import email as email_lib
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from email.header import decode_header
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from claude_scoring import call_claude_json

os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "academie@academiexguard.ca"
EMAIL_PASSWORD = "qlhoktyrfnrcbomd"

DATA_DIR = Path(r"C:\Users\user\sac_reports\email_analysis")
PROGRESS_FILE = DATA_DIR / "faq_progress.json"
FAQ_FILE = DATA_DIR / "faq_complete.json"
LOG_DIR = Path(r"C:\Users\user\sac_logs")

# Rate limit safety: process max N emails per session
MAX_EMAILS_PER_SESSION = 200  # ~200 Haiku calls = ~40% of 5h session
BATCH_SIZE = 10

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("faq_builder")
fh = logging.FileHandler(str(LOG_DIR / "faq_builder.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(fh)

# ---------------------------------------------------------------------------
# Haiku classification prompt
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


def load_progress():
    """Load previously analyzed email IDs."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {"analyzed_ids": [], "faq_entries": [], "last_run": None}


def save_progress(progress):
    """Save progress to resume later."""
    progress["last_run"] = datetime.now().isoformat()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(progress, f, ensure_ascii=False, indent=2)


def fetch_emails(since_days=180):
    """Fetch ALL emails from ALL folders (last N days)."""
    mail = imaplib.IMAP4_SSL(IMAP_SERVER)
    mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)

    # List all folders
    status, folder_list = mail.list()
    folders = []
    for f in folder_list:
        # Parse folder name from IMAP response
        # Format: (\flags) "delimiter" "folder_name"
        try:
            parts = f.decode().split('"')
            if len(parts) >= 3:
                folder_name = parts[-2]  # Last quoted string
                # Skip system folders we don't need
                if folder_name in ("[Gmail]",):
                    continue
                if "\\Noselect" in parts[0]:
                    continue
                folders.append(folder_name)
        except Exception:
            continue

    # Only scan FAQ-relevant folders (skip bulk folders like Formation BSP, Virement, etc.)
    PRIORITY_FOLDERS = {
        "INBOX", "Service &AOA- la client&AOg-le a traiter", "Annuler", "Litige",
        "BSP", "Secourisme", "Secourisme &AOA- choisir", "Recouvrement",
        "Drone", "Retard / absence", "internatonnal", "Winback",
        "$Vente", "$Vente/Hamza", "$Vente/Heidys Garcia", "$Vente/Domingos",
        "$Vente/Manel", "*Sekou", "service a confirmer", "cv a confirmer",
        "usage de la force/Gestion",
    }
    MAX_PER_FOLDER = 200  # Sample last 200 emails per folder

    relevant_folders = [f for f in folders if f in PRIORITY_FOLDERS]
    # Also include any folder not in a skip list
    SKIP_FOLDERS = {
        "Formation BSP", "Formation BSP/Recrutement", "Formation BSP/Formulaire de Renseignement",
        "Formation BSP/Formulaire de Renseignement/Banji / Fait",
        "Virement / Comptant / d&AOk-bit", "Virement / Comptant / d&AOk-bit/Paypal",
        "ID", "Facture", "justcall", "*Jessie", "*Jessie/Rush*",
        "t-Gohighlevel", "&- Nicolas", "* Anglais / Mitch",
        "[Gmail]/Importants", "[Gmail]/Corbeille", "[Gmail]/Favoris",
        "[Gmail]/Brouillons", "[Gmail]/Pourriel", "[Gmail]/Tous les messages",
        "[Gmail]/Messages envoy&AOk-s",
        "*Template", "Vieux template", "&AMk-lite", "$Vente/Formation anglais",
        "Banji", "RDV",
    }
    scan_folders = [f for f in folders if f in PRIORITY_FOLDERS or f not in SKIP_FOLDERS]
    # Deduplicate
    scan_folders = list(dict.fromkeys(scan_folders))

    log.info("Found %d total folders, scanning %d relevant ones", len(folders), len(scan_folders))

    emails = []

    for folder in scan_folders:
        try:
            # Select folder (quote it for IMAP)
            status, _ = mail.select(f'"{folder}"', readonly=True)
            if status != "OK":
                continue

            status, messages = mail.search(None, "ALL")
            msg_ids = messages[0].split()

            if not msg_ids:
                continue

            # Take only the last MAX_PER_FOLDER (most recent)
            msg_ids = msg_ids[-MAX_PER_FOLDER:]

            folder_count = 0
            for mid in msg_ids:
                try:
                    status, data = mail.fetch(mid, "(RFC822)")
                    msg = email_lib.message_from_bytes(data[0][1])

                    subj = decode_header(msg["Subject"] or "")[0][0]
                    if isinstance(subj, bytes):
                        subj = subj.decode(errors="ignore")

                    from_addr = msg["From"] or ""
                    date_str = msg["Date"] or ""
                    msg_id = msg["Message-ID"] or f"{folder}_{mid.decode()}"

                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                payload = part.get_payload(decode=True)
                                if payload:
                                    body = payload.decode(errors="ignore")
                                break
                    else:
                        payload = msg.get_payload(decode=True)
                        if payload:
                            body = payload.decode(errors="ignore")

                    body = body[:1000]

                    emails.append({
                        "id": msg_id,
                        "mid": mid.decode(),
                        "folder": folder,
                        "from": from_addr,
                        "subject": str(subj),
                        "date": date_str,
                        "body": body,
                    })
                    folder_count += 1
                except Exception as e:
                    pass

            if folder_count > 0:
                log.info("  %s: %d emails", folder, folder_count)

        except Exception as e:
            log.warning("  Folder '%s' error: %s", folder, str(e)[:50])

    mail.logout()
    log.info("Total emails across all folders: %d", len(emails))
    return emails


def classify_email(em):
    """Classify a single email with Haiku."""
    prompt = CLASSIFY_PROMPT.format(
        folder=em.get("folder", "INBOX"),
        from_addr=em["from"][:50],
        subject=em["subject"][:100],
        date=em["date"][:30],
        body=em["body"][:800],
    )
    return call_claude_json(prompt, model="haiku", timeout=30)


def build_faq(faq_entries):
    """Aggregate classified emails into FAQ topics."""
    topics = defaultdict(lambda: {"count": 0, "questions": [], "suggested_responses": []})

    for entry in faq_entries:
        topic = entry.get("faq_topic", "autre")
        if not topic:
            topic = "autre"
        topics[topic]["count"] += 1

        q = entry.get("question")
        if q and q not in topics[topic]["questions"]:
            topics[topic]["questions"].append(q)

        resp = entry.get("suggested_response")
        if resp and resp not in topics[topic]["suggested_responses"]:
            topics[topic]["suggested_responses"].append(resp)

    # Sort by count
    faq = []
    for topic, data in sorted(topics.items(), key=lambda x: -x[1]["count"]):
        faq.append({
            "topic": topic,
            "frequency": data["count"],
            "top_questions": data["questions"][:5],
            "suggested_responses": data["suggested_responses"][:3],
        })

    return faq


def main():
    log.info("=" * 60)
    log.info("EMAIL FAQ BUILDER — Analyzing emails")
    log.info("=" * 60)

    # Load progress
    progress = load_progress()
    already_done = set(progress["analyzed_ids"])
    log.info("Previously analyzed: %d emails", len(already_done))

    # Fetch emails
    log.info("Fetching emails (last 6 months)...")
    emails = fetch_emails(since_days=180)
    log.info("Found %d emails total", len(emails))

    # Filter to not-yet-analyzed
    to_analyze = [e for e in emails if e["id"] not in already_done]
    log.info("New to analyze: %d", len(to_analyze))

    if not to_analyze:
        log.info("Nothing new to analyze!")
        # Rebuild FAQ from existing entries
        if progress["faq_entries"]:
            faq = build_faq(progress["faq_entries"])
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with open(FAQ_FILE, "w", encoding="utf-8") as f:
                json.dump(faq, f, ensure_ascii=False, indent=2)
            log.info("FAQ rebuilt with %d topics", len(faq))
        return

    # Limit per session
    batch = to_analyze[:MAX_EMAILS_PER_SESSION]
    log.info("Processing %d emails this session (max %d)", len(batch), MAX_EMAILS_PER_SESSION)

    # Classify each email
    classified = 0
    failed = 0
    for i, em in enumerate(batch):
        try:
            result = classify_email(em)
            if result:
                result["email_id"] = em["id"]
                result["subject"] = em["subject"]
                result["from"] = em["from"]
                result["date"] = em["date"]
                progress["faq_entries"].append(result)
                progress["analyzed_ids"].append(em["id"])
                classified += 1

                if (i + 1) % 10 == 0:
                    log.info("  %d/%d classified (%d failed)", classified, len(batch), failed)
                    save_progress(progress)
            else:
                failed += 1
        except Exception as e:
            failed += 1
            log.warning("  Email %d failed: %s", i, e)

        # Rate limit protection
        if classified >= MAX_EMAILS_PER_SESSION:
            log.info("Session limit reached (%d). Will continue next run.", MAX_EMAILS_PER_SESSION)
            break

    # Save progress
    save_progress(progress)
    log.info("Classified: %d, Failed: %d", classified, failed)

    # Build FAQ
    faq = build_faq(progress["faq_entries"])
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(FAQ_FILE, "w", encoding="utf-8") as f:
        json.dump(faq, f, ensure_ascii=False, indent=2)

    log.info("")
    log.info("=" * 60)
    log.info("FAQ BUILT — %d topics from %d emails", len(faq), len(progress["faq_entries"]))
    log.info("=" * 60)
    for entry in faq[:10]:
        log.info("  %s (%dx): %s", entry["topic"], entry["frequency"],
                 entry["top_questions"][0] if entry["top_questions"] else "N/A")

    remaining = len(to_analyze) - classified
    if remaining > 0:
        log.info("")
        log.info("%d emails remaining — will process in next session", remaining)


if __name__ == "__main__":
    main()
