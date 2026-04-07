"""
Email Stats for Daily SAC Report — Sprint 5
Connects to academie@academiexguard.ca via IMAP, fetches today's emails,
identifies unanswered inbound emails that need a response.

Usage:
    from email_stats import fetch_email_stats, email_html_section
    stats = fetch_email_stats("2026-04-06")
    html = email_html_section(stats)
"""

import imaplib
import email as email_lib
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from email.header import decode_header
from email.utils import parsedate_to_datetime

log = logging.getLogger("email_stats")

IMAP_SERVER = "imap.gmail.com"
EMAIL_ACCOUNT = "academie@academiexguard.ca"
EMAIL_PASSWORD = "qlhoktyrfnrcbomd"

# Folders to scan for inbound emails
SCAN_FOLDERS = [
    "INBOX",
    "Service &AOA- la client&AOg-le a traiter",
    "Annuler",
    "Litige",
    "BSP",
    "Secourisme",
    "Recouvrement",
    "Drone",
    "Retard / absence",
    "Winback",
    "service a confirmer",
]

# Internal/system senders to ignore
IGNORE_SENDERS = {
    "noreply", "no-reply", "mailer-daemon", "postmaster", "notifications",
    "justcall", "gohighlevel", "calendly", "stripe", "paypal",
    "support@justcall", "notification@", "system@", "alert@",
}

# XGuard internal email patterns
# Internal domains — any email @these domains is internal/automated
XGUARD_DOMAINS = {"xguard.ca", "academiexguard.ca"}

# Additional specific internal addresses
XGUARD_EMAILS = {
    "nick@darkhorseads.com",
}


def _decode_header_val(raw):
    """Safely decode an email header value."""
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


def _is_system_sender(from_addr):
    """Check if sender is a system/noreply address."""
    addr_lower = from_addr.lower()
    for pattern in IGNORE_SENDERS:
        if pattern in addr_lower:
            return True
    return False


def _is_internal_sender(from_addr):
    """Check if sender is an XGuard internal email or domain."""
    addr_lower = from_addr.lower().strip()
    # Check specific addresses
    if addr_lower in XGUARD_EMAILS:
        return True
    # Check domains
    if "@" in addr_lower:
        domain = addr_lower.split("@")[-1]
        if domain in XGUARD_DOMAINS:
            return True
    return False


def _extract_email(from_field):
    """Extract bare email address from 'Name <email>' format."""
    match = re.search(r'<([^>]+)>', from_field or "")
    if match:
        return match.group(1).strip().lower()
    # Fallback: the whole field might be just an email
    return (from_field or "").strip().lower()


def _get_message_date(msg):
    """Parse the Date header into a datetime."""
    date_str = msg.get("Date", "")
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return None


def fetch_email_stats(date_str):
    """
    Fetch email stats for a given date.
    Returns dict with:
      - total_received: all inbound emails today
      - total_sent: outbound emails today
      - unanswered: list of {from, subject, folder, date, hours_waiting}
      - unanswered_count: len(unanswered)
      - by_folder: {folder: {received, sent}} breakdown
      - by_category: rough categorization
    """
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    # IMAP date format for SINCE/BEFORE
    since_str = target_date.strftime("%d-%b-%Y")
    before_str = (target_date + timedelta(days=1)).strftime("%d-%b-%Y")

    result = {
        "date": date_str,
        "total_received": 0,
        "total_sent": 0,
        "unanswered": [],
        "unanswered_count": 0,
        "by_folder": {},
        "by_category": defaultdict(int),
        "errors": [],
    }

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
    except Exception as e:
        log.error("IMAP login failed: %s", e)
        result["errors"].append(f"IMAP login failed: {e}")
        return result

    # First, get sent message-IDs + TO addresses to detect replies
    sent_in_reply_to = set()
    sent_references = set()
    sent_to_addresses = set()  # Track who we replied TO
    try:
        status, _ = mail.select('"[Gmail]/Messages envoy&AOk-s"', readonly=True)
        if status == "OK":
            status, msg_nums = mail.search(None, f'(SINCE "{since_str}" BEFORE "{before_str}")')
            if status == "OK" and msg_nums[0]:
                for num in msg_nums[0].split():
                    try:
                        status, data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (TO CC IN-REPLY-TO REFERENCES)])")
                        if status == "OK" and data[0] and data[0][1]:
                            header_data = data[0][1]
                            if isinstance(header_data, bytes):
                                header_data = header_data.decode(errors="ignore")
                            # Extract In-Reply-To
                            irt_match = re.search(r'In-Reply-To:\s*(<[^>]+>)', header_data, re.IGNORECASE)
                            if irt_match:
                                sent_in_reply_to.add(irt_match.group(1).strip())
                            # Extract References (may contain multiple IDs)
                            ref_match = re.search(r'References:\s*(.+?)(?:\r?\n(?!\s)|$)', header_data, re.IGNORECASE | re.DOTALL)
                            if ref_match:
                                refs = re.findall(r'<[^>]+>', ref_match.group(1))
                                sent_references.update(r.strip() for r in refs)
                            # Extract TO addresses (who we replied to)
                            to_match = re.search(r'To:\s*(.+?)(?:\r?\n(?!\s)|$)', header_data, re.IGNORECASE | re.DOTALL)
                            if to_match:
                                to_addrs = re.findall(r'[\w.+-]+@[\w.-]+', to_match.group(1))
                                sent_to_addresses.update(a.lower() for a in to_addrs)
                            cc_match = re.search(r'Cc:\s*(.+?)(?:\r?\n(?!\s)|$)', header_data, re.IGNORECASE | re.DOTALL)
                            if cc_match:
                                cc_addrs = re.findall(r'[\w.+-]+@[\w.-]+', cc_match.group(1))
                                sent_to_addresses.update(a.lower() for a in cc_addrs)
                            result["total_sent"] += 1
                    except Exception:
                        pass
    except Exception as e:
        log.warning("Could not scan sent folder: %s", e)

    # Remove internal addresses from sent_to (we don't count sending to ourselves as a reply)
    sent_to_addresses = {a for a in sent_to_addresses if not _is_internal_sender(a)}

    log.info("Found %d sent replies today, %d reference IDs, %d unique recipients",
             len(sent_in_reply_to), len(sent_references), len(sent_to_addresses))

    # Now scan inbound folders
    all_inbound = []

    for folder in SCAN_FOLDERS:
        try:
            status, _ = mail.select(f'"{folder}"', readonly=True)
            if status != "OK":
                continue

            status, msg_nums = mail.search(None, f'(SINCE "{since_str}" BEFORE "{before_str}")')
            if status != "OK" or not msg_nums[0]:
                continue

            folder_received = 0
            nums = msg_nums[0].split()

            for num in nums:
                try:
                    # Fetch headers only (lightweight)
                    status, data = mail.fetch(
                        num,
                        "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT DATE MESSAGE-ID IN-REPLY-TO)])"
                    )
                    if status != "OK" or not data[0] or not data[0][1]:
                        continue

                    header_bytes = data[0][1]
                    if isinstance(header_bytes, bytes):
                        header_text = header_bytes.decode(errors="ignore")
                    else:
                        header_text = str(header_bytes)

                    # Parse headers manually (more reliable than email.message_from_bytes for headers only)
                    from_match = re.search(r'From:\s*(.+?)(?:\r?\n(?!\s)|$)', header_text, re.IGNORECASE | re.DOTALL)
                    subj_match = re.search(r'Subject:\s*(.+?)(?:\r?\n(?!\s)|$)', header_text, re.IGNORECASE | re.DOTALL)
                    date_match = re.search(r'Date:\s*(.+?)(?:\r?\n(?!\s)|$)', header_text, re.IGNORECASE | re.DOTALL)
                    msgid_match = re.search(r'Message-ID:\s*(<[^>]+>)', header_text, re.IGNORECASE)

                    from_raw = from_match.group(1).strip() if from_match else ""
                    subject_raw = subj_match.group(1).strip() if subj_match else "(sans sujet)"
                    date_raw = date_match.group(1).strip() if date_match else ""
                    msg_id = msgid_match.group(1).strip() if msgid_match else ""

                    # Decode encoded headers
                    from_decoded = _decode_header_val(from_raw) if from_raw else ""
                    subject_decoded = _decode_header_val(subject_raw) if subject_raw else "(sans sujet)"

                    from_email = _extract_email(from_decoded)

                    # Skip system/internal senders
                    if _is_system_sender(from_decoded):
                        continue
                    if _is_internal_sender(from_email):
                        continue

                    folder_received += 1

                    # Check if this email was replied to
                    # Method 1: Message-ID match (In-Reply-To / References)
                    replied = False
                    if msg_id and msg_id in sent_in_reply_to:
                        replied = True
                    if msg_id and msg_id in sent_references:
                        replied = True
                    # Method 2: We sent an email TO the same person today
                    if not replied and from_email and from_email in sent_to_addresses:
                        replied = True

                    # Parse date for hours_waiting
                    hours_waiting = None
                    try:
                        from email.utils import parsedate_to_datetime as _pdt
                        email_dt = _pdt(date_raw)
                        now = datetime.now(email_dt.tzinfo) if email_dt.tzinfo else datetime.now()
                        hours_waiting = round((now - email_dt).total_seconds() / 3600, 1)
                    except Exception:
                        pass

                    # Rough category from subject
                    subj_lower = subject_decoded.lower()
                    cat = "autre"
                    if any(w in subj_lower for w in ["inscri", "formation", "cours", "session", "bsp", "gardiennage"]):
                        cat = "inscription"
                    elif any(w in subj_lower for w in ["annul", "rembours"]):
                        cat = "annulation"
                    elif any(w in subj_lower for w in ["paie", "paiement", "facture", "virement"]):
                        cat = "paiement"
                    elif any(w in subj_lower for w in ["plainte", "mecontent", "insatisf"]):
                        cat = "plainte"
                    elif any(w in subj_lower for w in ["certificat", "attestation", "diplome"]):
                        cat = "certificat"
                    elif any(w in subj_lower for w in ["emploi", "cv", "poste", "recrutement"]):
                        cat = "emploi"
                    elif any(w in subj_lower for w in ["prix", "tarif", "combien", "information", "renseignement"]):
                        cat = "info"

                    result["by_category"][cat] += 1

                    if not replied:
                        all_inbound.append({
                            "from": from_decoded[:60],
                            "from_email": from_email,
                            "subject": subject_decoded[:80],
                            "folder": folder,
                            "date": date_raw[:25],
                            "hours_waiting": hours_waiting,
                            "category": cat,
                            "msg_id": msg_id,
                        })

                except Exception as e:
                    pass

            result["by_folder"][folder] = {"received": folder_received}
            if folder_received > 0:
                log.info("  %s: %d emails", folder, folder_received)

        except Exception as e:
            log.warning("  Folder '%s' error: %s", folder, str(e)[:80])

    try:
        mail.logout()
    except Exception:
        pass

    # Count total received across folders
    result["total_received"] = sum(f["received"] for f in result["by_folder"].values())

    # Dedup: same sender + same subject = count as 1 (keep the oldest)
    seen_keys = set()
    deduped = []
    dupes_removed = 0
    for em in all_inbound:
        key = (em["from_email"], em["subject"].strip().lower())
        if key in seen_keys:
            dupes_removed += 1
            continue
        seen_keys.add(key)
        deduped.append(em)
    if dupes_removed > 0:
        log.info("  Dedup: removed %d duplicate emails (same sender+subject)", dupes_removed)

    # Sort unanswered by hours_waiting (most urgent first = longest waiting)
    deduped.sort(key=lambda x: -(x.get("hours_waiting") or 0))
    result["unanswered"] = deduped
    result["unanswered_count"] = len(deduped)
    result["dupes_removed"] = dupes_removed

    # Convert defaultdict to dict for JSON serialization
    result["by_category"] = dict(result["by_category"])

    log.info("Email stats: %d received, %d sent, %d unanswered",
             result["total_received"], result["total_sent"], result["unanswered_count"])

    return result


def email_html_section(stats):
    """Generate HTML section for the daily email report."""
    if not stats or stats.get("total_received", 0) == 0:
        return ""

    total = stats["total_received"]
    sent = stats["total_sent"]
    unanswered = stats["unanswered_count"]
    answered = total - unanswered

    # Color coding
    if unanswered == 0:
        badge_color = "#2E7D32"
        badge_text = "Tout repondu!"
    elif unanswered <= 5:
        badge_color = "#E65100"
        badge_text = f"{unanswered} en attente"
    else:
        badge_color = "#C62828"
        badge_text = f"{unanswered} en attente"

    # Category breakdown
    cat_labels = {
        "inscription": "Inscription", "annulation": "Annulation", "paiement": "Paiement",
        "plainte": "Plainte", "certificat": "Certificat", "emploi": "Emploi",
        "info": "Information", "autre": "Autre",
    }
    cat_pills = ""
    for cat, count in sorted(stats.get("by_category", {}).items(), key=lambda x: -x[1]):
        label = cat_labels.get(cat, cat.capitalize())
        cat_pills += f'<span style="display:inline-block;background:#E8EAF6;color:#283593;padding:2px 8px;border-radius:10px;font-size:11px;margin:2px;">{label}: {count}</span> '

    # Unanswered table rows (top 10)
    unanswered_rows = ""
    for em in stats.get("unanswered", [])[:10]:
        hw = em.get("hours_waiting")
        if hw is not None:
            if hw >= 8:
                wait_color = "#C62828"
                wait_icon = "&#9888;"  # warning
            elif hw >= 4:
                wait_color = "#E65100"
                wait_icon = "&#9200;"  # clock
            else:
                wait_color = "#2E7D32"
                wait_icon = ""
            wait_str = f"{wait_icon} {hw:.0f}h" if hw >= 1 else f"{int(hw * 60)}min"
        else:
            wait_color = "#777"
            wait_str = "?"

        # Category badge
        cat = em.get("category", "autre")
        cat_color = {
            "plainte": "#C62828", "annulation": "#E65100", "paiement": "#1565C0",
            "inscription": "#2E7D32", "certificat": "#6A1B9A", "emploi": "#00695C",
        }.get(cat, "#777")

        folder_short = em.get("folder", "INBOX")
        if len(folder_short) > 15:
            folder_short = folder_short[:12] + "..."

        unanswered_rows += f"""
        <tr>
          <td style="padding:5px;font-size:11px;max-width:120px;overflow:hidden;text-overflow:ellipsis;">{em.get('from','')[:35]}</td>
          <td style="padding:5px;font-size:11px;max-width:200px;overflow:hidden;text-overflow:ellipsis;">{em.get('subject','')[:50]}</td>
          <td style="padding:5px;font-size:11px;color:#777;">{folder_short}</td>
          <td style="padding:5px;font-size:11px;text-align:center;color:{wait_color};font-weight:bold;">{wait_str}</td>
          <td style="padding:5px;text-align:center;"><span style="color:{cat_color};font-size:10px;font-weight:bold;">{cat_labels.get(cat, cat)}</span></td>
        </tr>"""

    more_text = ""
    if unanswered > 10:
        more_text = f'<p style="font-size:11px;color:#777;text-align:center;">... et {unanswered - 10} autres emails en attente</p>'

    # Folder breakdown
    folder_pills = ""
    for fname, fdata in sorted(stats.get("by_folder", {}).items(), key=lambda x: -x[1].get("received", 0)):
        cnt = fdata.get("received", 0)
        if cnt > 0:
            short = fname if len(fname) <= 20 else fname[:17] + "..."
            folder_pills += f'<span style="display:inline-block;background:#f5f5f5;color:#555;padding:2px 6px;border-radius:8px;font-size:10px;margin:1px;">{short}: {cnt}</span> '

    html = f"""
<!-- EMAIL SECTION -->
<h2 style="color:#1565C0;border-bottom:2px solid #1565C0;padding-bottom:5px;font-size:15px;">&#9993; Emails ({total} recus)</h2>

<!-- KPI row -->
<table style="width:100%;border-collapse:collapse;margin:0 0 10px;">
  <tr>
    <td style="padding:10px;text-align:center;background:#E3F2FD;border:1px solid #BBDEFB;">
      <div style="font-size:22px;font-weight:bold;color:#1565C0;">{total}</div>
      <div style="font-size:10px;color:#777;">Recus</div>
    </td>
    <td style="padding:10px;text-align:center;background:#E8F5E9;border:1px solid #C8E6C9;">
      <div style="font-size:22px;font-weight:bold;color:#2E7D32;">{sent}</div>
      <div style="font-size:10px;color:#777;">Envoyes</div>
    </td>
    <td style="padding:10px;text-align:center;background:#E8F5E9;border:1px solid #C8E6C9;">
      <div style="font-size:22px;font-weight:bold;color:#2E7D32;">{answered}</div>
      <div style="font-size:10px;color:#777;">Repondus</div>
    </td>
    <td style="padding:10px;text-align:center;background:{'#FFEBEE' if unanswered > 5 else '#FFF3E0' if unanswered > 0 else '#E8F5E9'};border:1px solid #eee;">
      <div style="font-size:22px;font-weight:bold;color:{badge_color};">{unanswered}</div>
      <div style="font-size:10px;color:#777;">En attente</div>
    </td>
  </tr>
</table>

<!-- Categories -->
<div style="margin:5px 0 10px;">{cat_pills}</div>

{'<!-- Unanswered list -->' + chr(10) + '<div style="background:#FFF8E1;border-left:4px solid #F57F17;padding:10px 12px;margin:0 0 10px;">' + chr(10) + f'<strong style="color:#E65100;">{badge_text}</strong>' + chr(10) + '<table style="width:100%;border-collapse:collapse;margin:8px 0 0;">' + chr(10) + '<tr style="color:#999;font-size:10px;"><th style="padding:3px;text-align:left;">De</th><th style="padding:3px;text-align:left;">Sujet</th><th style="padding:3px;">Dossier</th><th style="padding:3px;">Attente</th><th style="padding:3px;">Cat.</th></tr>' + chr(10) + unanswered_rows + chr(10) + '</table>' + chr(10) + more_text + chr(10) + '</div>' if unanswered > 0 else '<div style="background:#E8F5E9;border-left:4px solid #2E7D32;padding:10px 12px;margin:0 0 10px;"><strong style="color:#2E7D32;">&#10003; Tous les emails ont ete repondus!</strong></div>'}

<!-- Folders -->
<div style="margin:0 0 15px;font-size:11px;color:#777;">Dossiers: {folder_pills}</div>
"""
    return html


# --- CLI test ---
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    print(f"Fetching email stats for {date}...")
    stats = fetch_email_stats(date)
    print(f"  Received: {stats['total_received']}")
    print(f"  Sent: {stats['total_sent']}")
    print(f"  Unanswered: {stats['unanswered_count']}")
    print(f"  Categories: {stats['by_category']}")
    print(f"  Folders: {list(stats['by_folder'].keys())}")
    if stats["unanswered"]:
        print(f"\n  Top unanswered:")
        for em in stats["unanswered"][:5]:
            print(f"    [{em['category']}] {em['from'][:30]} — {em['subject'][:40]} ({em.get('hours_waiting',0):.0f}h)")
    html = email_html_section(stats)
    if html:
        with open("email_section_test.html", "w", encoding="utf-8") as f:
            f.write(f"<html><body>{html}</body></html>")
        print(f"\n  HTML preview saved to email_section_test.html ({len(html)} chars)")
