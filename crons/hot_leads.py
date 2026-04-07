#!/usr/bin/env python3
"""
Sprint 9 — Hot Lead List
Runs daily at 17h on Nitro. Cross-references:
  1. Missed calls (JustCall) — people who called but nobody answered
  2. Unanswered SMS (JustCall) — people who texted but got no reply
  3. Unanswered emails (IMAP) — people who emailed but got no response

Outputs a prioritized "Hot List" email to Hamza + Nick:
  - URGENT: missed call + unanswered SMS (same number, trying both channels)
  - HIGH: SMS with inscription/paiement intent (money on the table)
  - MEDIUM: missed call only OR unanswered SMS only
  - LOW: unanswered email only

Each lead shows: name, number, what they tried, when, and suggested action.
"""

import json
import logging
import os
import smtplib
import sys
from collections import defaultdict
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

from smart_stats import fetch_all_raw
from sms_stats import fetch_sms_for_date, classify_sms, INTENT_PATTERNS
from email_stats import fetch_email_stats

GMAIL_USER = "nick@darkhorseads.com"
GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"

LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / f"hot_leads_{datetime.now():%Y-%m-%d}.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger("hot_leads")

DAYS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"}


def normalize_number(num):
    """Normalize phone number for matching."""
    if not num:
        return ""
    num = num.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if num.startswith("+1"):
        num = num[2:]
    elif num.startswith("1") and len(num) == 11:
        num = num[1:]
    return num[-10:] if len(num) >= 10 else num


def get_missed_calls(date_str):
    """Get today's missed calls (inbound, duration=0, work hours 8-18)."""
    raw_calls = fetch_all_raw(date_str)
    missed = {}  # by normalized number

    for c in raw_calls:
        hour = None
        try:
            dt = datetime.strptime(c.get("time", ""), "%Y-%m-%d %H:%M:%S")
            hour = dt.hour
        except Exception:
            continue

        if hour < 8 or hour >= 18:
            continue

        is_inbound = str(c.get("direction", "")) == "1"
        duration = int(c.get("duration", 0) or 0)
        is_missed = is_inbound and duration == 0

        num = normalize_number(c.get("contact_number", ""))
        name = (c.get("contact_name", "") or "").strip()

        if not num:
            continue

        if num not in missed:
            missed[num] = {
                "number": num,
                "name": name,
                "missed_count": 0,
                "answered": False,
                "times": [],
                "last_time": "",
            }

        if is_inbound and duration > 0:
            missed[num]["answered"] = True

        if is_missed:
            missed[num]["missed_count"] += 1
            missed[num]["times"].append(c.get("time", "")[-8:-3])  # HH:MM
            missed[num]["last_time"] = c.get("time", "")

        if name and not missed[num]["name"]:
            missed[num]["name"] = name

    # Only keep truly missed (never answered today)
    return {k: v for k, v in missed.items() if v["missed_count"] > 0 and not v["answered"]}


def get_unanswered_sms(date_str):
    """Get today's unanswered inbound SMS with intent classification."""
    sms_list = fetch_sms_for_date(date_str)
    if not sms_list:
        return {}

    by_number = defaultdict(lambda: {"inbound": [], "outbound": []})
    for s in sms_list:
        num = normalize_number(s.get("contact_number", ""))
        if not num:
            continue
        direction = s.get("direction", "")
        if direction == "Incoming":
            by_number[num]["inbound"].append(s)
        elif direction == "Outgoing":
            by_number[num]["outbound"].append(s)

    unanswered = {}
    for num, data in by_number.items():
        if data["inbound"] and not data["outbound"]:
            last_sms = data["inbound"][-1]
            body = (last_sms.get("sms_info", {}) or {}).get("body", "") or ""
            name = (last_sms.get("contact_name", "") or "").strip()
            intents = classify_sms(body) if body else []

            unanswered[num] = {
                "number": num,
                "name": name,
                "sms_count": len(data["inbound"]),
                "last_message": body[:200],
                "last_time": f"{last_sms.get('sms_date', '')} {last_sms.get('sms_time', '')}".strip(),
                "intents": intents,
                "is_hot": any(i in intents for i in ["inscription", "paiement"]),
            }

    return unanswered


def build_hot_list(date_str):
    """Build the prioritized hot lead list."""
    log.info("Fetching missed calls...")
    missed = get_missed_calls(date_str)
    log.info("  %d truly missed contacts", len(missed))

    log.info("Fetching unanswered SMS...")
    sms = get_unanswered_sms(date_str)
    log.info("  %d unanswered SMS contacts", len(sms))

    log.info("Fetching unanswered emails...")
    emails = fetch_email_stats(date_str)
    log.info("  %d unanswered emails", emails.get("unanswered_count", 0))

    # Build unified lead list
    leads = {}  # by number or email

    # Add missed calls
    for num, data in missed.items():
        leads[num] = {
            "number": num,
            "display_number": f"+1{num}" if len(num) == 10 else num,
            "name": data["name"],
            "missed_calls": data["missed_count"],
            "call_times": data["times"],
            "sms_count": 0,
            "sms_message": "",
            "sms_intents": [],
            "sms_hot": False,
            "email": None,
            "email_subject": "",
            "priority": "MEDIUM",
            "channels": ["appel"],
            "action": "Rappeler",
        }

    # Merge unanswered SMS
    for num, data in sms.items():
        if num in leads:
            # URGENT: same person called AND texted
            leads[num]["sms_count"] = data["sms_count"]
            leads[num]["sms_message"] = data["last_message"]
            leads[num]["sms_intents"] = data["intents"]
            leads[num]["sms_hot"] = data["is_hot"]
            leads[num]["channels"].append("SMS")
            leads[num]["priority"] = "URGENT"
            leads[num]["action"] = "Rappeler + repondre SMS"
            if not leads[num]["name"] and data["name"]:
                leads[num]["name"] = data["name"]
        else:
            priority = "HIGH" if data["is_hot"] else "MEDIUM"
            action = "Repondre SMS (inscription/paiement!)" if data["is_hot"] else "Repondre SMS"
            leads[num] = {
                "number": num,
                "display_number": f"+1{num}" if len(num) == 10 else num,
                "name": data["name"],
                "missed_calls": 0,
                "call_times": [],
                "sms_count": data["sms_count"],
                "sms_message": data["last_message"],
                "sms_intents": data["intents"],
                "sms_hot": data["is_hot"],
                "email": None,
                "email_subject": "",
                "priority": priority,
                "channels": ["SMS"],
                "action": action,
            }

    # Add unanswered emails (can't cross-ref by phone, separate entries)
    for em in emails.get("unanswered", [])[:15]:  # Top 15 most urgent
        key = f"email_{em.get('from_email', '')}"
        leads[key] = {
            "number": "",
            "display_number": "",
            "name": em.get("from", "")[:40],
            "missed_calls": 0,
            "call_times": [],
            "sms_count": 0,
            "sms_message": "",
            "sms_intents": [],
            "sms_hot": False,
            "email": em.get("from_email", ""),
            "email_subject": em.get("subject", "")[:60],
            "priority": "HIGH" if em.get("category") in ("inscription", "paiement", "plainte") else "LOW",
            "channels": ["email"],
            "action": f"Repondre email ({em.get('category', 'autre')})",
        }

    # Sort by priority
    priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_leads = sorted(leads.values(), key=lambda l: (priority_order.get(l["priority"], 9), -l["missed_calls"], -l["sms_count"]))

    return sorted_leads, len(missed), len(sms), emails.get("unanswered_count", 0)


def build_html(date_str, leads, n_missed, n_sms, n_emails):
    """Build Hot List HTML email."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = DAYS_FR.get(dt.weekday(), "")

    urgent = [l for l in leads if l["priority"] == "URGENT"]
    high = [l for l in leads if l["priority"] == "HIGH"]
    medium = [l for l in leads if l["priority"] == "MEDIUM"]
    low = [l for l in leads if l["priority"] == "LOW"]

    priority_colors = {
        "URGENT": ("#C62828", "#FFEBEE", "URGENT"),
        "HIGH": ("#E65100", "#FFF3E0", "HIGH"),
        "MEDIUM": ("#F57F17", "#FFF8E1", "MEDIUM"),
        "LOW": ("#777", "#F5F5F5", "LOW"),
    }

    def lead_rows(lead_list):
        rows = ""
        for l in lead_list:
            pc, bg, label = priority_colors.get(l["priority"], ("#777", "#f5f5f5", "?"))
            channels = " + ".join(l["channels"])
            name = l["name"] or "Inconnu"

            details = []
            if l["missed_calls"] > 0:
                times = ", ".join(l["call_times"][:3])
                details.append(f'{l["missed_calls"]} appel(s) manque(s) a {times}')
            if l["sms_count"] > 0:
                msg_preview = l["sms_message"][:80] + "..." if len(l["sms_message"]) > 80 else l["sms_message"]
                intents_str = ", ".join(l["sms_intents"]) if l["sms_intents"] else ""
                details.append(f'{l["sms_count"]} SMS{" [" + intents_str + "]" if intents_str else ""}: "{msg_preview}"')
            if l["email"]:
                details.append(f'Email: {l["email_subject"]}')

            details_html = "<br>".join(f'<span style="font-size:10px;color:#555;">{d}</span>' for d in details)

            rows += f"""
            <tr style="border-bottom:1px solid #eee;">
              <td style="padding:8px;text-align:center;"><span style="background:{bg};color:{pc};padding:2px 8px;border-radius:10px;font-size:10px;font-weight:bold;">{label}</span></td>
              <td style="padding:8px;">
                <strong style="font-size:12px;">{name}</strong><br>
                <span style="font-size:11px;color:#1565C0;">{l['display_number'] or l.get('email','')}</span>
              </td>
              <td style="padding:8px;font-size:11px;">{channels}</td>
              <td style="padding:8px;font-size:10px;">{details_html}</td>
              <td style="padding:8px;font-size:11px;font-weight:bold;color:{pc};">{l['action']}</td>
            </tr>"""
        return rows

    html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:800px;margin:0 auto;">

<div style="background:linear-gradient(135deg,#C62828,#E65100);padding:20px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="color:white;margin:0;font-size:20px;">HOT LIST — Leads a rappeler</h1>
  <p style="color:#ffcdd2;margin:5px 0 0;font-size:12px;">{day_name} {date_str} | Genere a 17h</p>
</div>

<div style="padding:15px;border:1px solid #ddd;border-top:none;">

<!-- KPI Cards -->
<table style="width:100%;border-collapse:collapse;margin:0 0 15px;">
  <tr>
    <td style="padding:10px;text-align:center;background:#FFEBEE;border:1px solid #FFCDD2;">
      <div style="font-size:28px;font-weight:bold;color:#C62828;">{len(urgent)}</div>
      <div style="font-size:10px;color:#777;">URGENT</div>
      <div style="font-size:9px;color:#999;">appel + SMS</div>
    </td>
    <td style="padding:10px;text-align:center;background:#FFF3E0;border:1px solid #FFE0B2;">
      <div style="font-size:28px;font-weight:bold;color:#E65100;">{len(high)}</div>
      <div style="font-size:10px;color:#777;">HIGH</div>
      <div style="font-size:9px;color:#999;">inscription/paiement</div>
    </td>
    <td style="padding:10px;text-align:center;background:#FFF8E1;border:1px solid #FFF176;">
      <div style="font-size:28px;font-weight:bold;color:#F57F17;">{len(medium)}</div>
      <div style="font-size:10px;color:#777;">MEDIUM</div>
      <div style="font-size:9px;color:#999;">appel ou SMS</div>
    </td>
    <td style="padding:10px;text-align:center;background:#F5F5F5;border:1px solid #eee;">
      <div style="font-size:28px;font-weight:bold;color:#777;">{len(low)}</div>
      <div style="font-size:10px;color:#777;">LOW</div>
      <div style="font-size:9px;color:#999;">email seulement</div>
    </td>
    <td style="padding:10px;text-align:center;background:#E3F2FD;border:1px solid #BBDEFB;">
      <div style="font-size:28px;font-weight:bold;color:#1565C0;">{len(leads)}</div>
      <div style="font-size:10px;color:#777;">TOTAL</div>
      <div style="font-size:9px;color:#999;">leads a traiter</div>
    </td>
  </tr>
</table>

<!-- Source breakdown -->
<div style="background:#f5f5f5;padding:8px 12px;border-radius:6px;margin:0 0 15px;font-size:11px;color:#555;">
  Sources: <strong>{n_missed}</strong> appels manques | <strong>{n_sms}</strong> SMS sans reponse | <strong>{n_emails}</strong> emails sans reponse
</div>

"""
    # URGENT section
    if urgent:
        html += f"""
<h2 style="color:#C62828;border-bottom:2px solid #C62828;padding-bottom:5px;font-size:14px;">
  URGENT — Appel + SMS du meme contact ({len(urgent)})
</h2>
<table style="width:100%;border-collapse:collapse;margin:8px 0 15px;font-size:12px;">
  <tr style="background:#FFEBEE;"><th style="padding:6px;width:60px;">Priorite</th><th style="padding:6px;">Contact</th><th style="padding:6px;width:70px;">Canaux</th><th style="padding:6px;">Details</th><th style="padding:6px;width:120px;">Action</th></tr>
  {lead_rows(urgent)}
</table>"""

    # HIGH section
    if high:
        html += f"""
<h2 style="color:#E65100;border-bottom:2px solid #E65100;padding-bottom:5px;font-size:14px;">
  HIGH — Inscription / Paiement ({len(high)})
</h2>
<table style="width:100%;border-collapse:collapse;margin:8px 0 15px;font-size:12px;">
  <tr style="background:#FFF3E0;"><th style="padding:6px;width:60px;">Priorite</th><th style="padding:6px;">Contact</th><th style="padding:6px;width:70px;">Canaux</th><th style="padding:6px;">Details</th><th style="padding:6px;width:120px;">Action</th></tr>
  {lead_rows(high)}
</table>"""

    # MEDIUM section
    if medium:
        html += f"""
<h2 style="color:#F57F17;border-bottom:2px solid #F57F17;padding-bottom:5px;font-size:14px;">
  MEDIUM — Appel ou SMS sans reponse ({len(medium)})
</h2>
<table style="width:100%;border-collapse:collapse;margin:8px 0 15px;font-size:12px;">
  <tr style="background:#FFF8E1;"><th style="padding:6px;width:60px;">Priorite</th><th style="padding:6px;">Contact</th><th style="padding:6px;width:70px;">Canaux</th><th style="padding:6px;">Details</th><th style="padding:6px;width:120px;">Action</th></tr>
  {lead_rows(medium)}
</table>"""

    # LOW section
    if low:
        html += f"""
<h2 style="color:#777;border-bottom:2px solid #ccc;padding-bottom:5px;font-size:14px;">
  LOW — Emails sans reponse ({len(low)})
</h2>
<table style="width:100%;border-collapse:collapse;margin:8px 0 15px;font-size:12px;">
  <tr style="background:#f5f5f5;"><th style="padding:6px;width:60px;">Priorite</th><th style="padding:6px;">Contact</th><th style="padding:6px;width:70px;">Canaux</th><th style="padding:6px;">Details</th><th style="padding:6px;width:120px;">Action</th></tr>
  {lead_rows(low)}
</table>"""

    if not leads:
        html += '<div style="background:#E8F5E9;border-left:4px solid #2E7D32;padding:15px;margin:10px 0;"><strong style="color:#2E7D32;">Aucun lead en attente!</strong> Tout a ete traite.</div>'

    html += """
</div>
<div style="background:#f5f5f5;padding:10px;border-radius:0 0 8px 8px;text-align:center;border:1px solid #ddd;border-top:none;">
  <p style="color:#999;font-size:10px;margin:0;">Academie XGuard — Hot Lead List IA | Genere automatiquement a 17h</p>
</div>
</body></html>"""

    return html


def send_email(date_str, html, n_leads):
    """Send Hot List via Gmail SMTP."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = DAYS_FR.get(dt.weekday(), "")

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = "hmaghraoui65@gmail.com"
    msg["Cc"] = "nick@darkhorseads.com"
    msg["Subject"] = f"HOT LIST {day_name} {date_str} — {n_leads} leads a rappeler"
    msg.attach(MIMEText(html, "html", "utf-8"))

    recipients = ["hmaghraoui65@gmail.com", "nick@darkhorseads.com"]

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        log.info("Hot List email SENT to %s", ", ".join(recipients))
    except Exception as e:
        log.error("Email send failed: %s", e)


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")

    log.info("=" * 60)
    log.info("HOT LEAD LIST — %s", date_str)
    log.info("=" * 60)

    leads, n_missed, n_sms, n_emails = build_hot_list(date_str)
    log.info("")
    log.info("RESULTS: %d total leads", len(leads))
    log.info("  URGENT: %d", len([l for l in leads if l["priority"] == "URGENT"]))
    log.info("  HIGH:   %d", len([l for l in leads if l["priority"] == "HIGH"]))
    log.info("  MEDIUM: %d", len([l for l in leads if l["priority"] == "MEDIUM"]))
    log.info("  LOW:    %d", len([l for l in leads if l["priority"] == "LOW"]))

    if not leads:
        log.info("No leads — skipping email")
        return

    html = build_html(date_str, leads, n_missed, n_sms, n_emails)
    log.info("HTML built (%d chars)", len(html))
    send_email(date_str, html, len(leads))
    log.info("DONE!")


if __name__ == "__main__":
    main()
