#!/usr/bin/env python3
"""
Sprint 15 — Smart Hot Leads SMS (v2 of hot_leads.py)

Runs daily at 14h on Nitro. Key differences from the old hot_leads.py:

1. Cross-check GHL tag 'gard paid' for each lead:
   - Already paid? SKIP (don't harass existing customers)
   - Not paid? Generate personalized SMS based on their history

2. Personalized SMS via Haiku:
   - Analyzes: inbound SMS content, email subject, missed call transcript
   - Generates a contextual French SMS tailored to what they're interested in
   - Goal: bring them back to the funnel

3. Safety rails:
   - Max 10 SMS per day (priority: URGENT > HIGH > MEDIUM > LOW)
   - Max 1 SMS per contact per 7 days (throttle via Supabase)
   - --dry-run flag: generate SMS + send preview email to Nick, don't send
   - Skip lead if Haiku fails (no generic fallback — don't spam)

4. Track everything in Supabase hot_sms_sent table.

Flags:
  --dry-run    Generate SMS but don't send. Email Nick with previews.
  --limit N    Max SMS to send (default: 10)
"""

import argparse
import json
import logging
import os
import smtplib
import sys
import time
from collections import defaultdict
from datetime import datetime, date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

from smart_stats import fetch_all_raw
from sms_stats import fetch_sms_for_date
from email_stats import fetch_email_stats
from phone_utils import normalize_number

from kb_config import (
    sb_upsert, sb_get,
    GMAIL_USER, GMAIL_APP_PASSWORD, NICK_EMAIL,
    XGUARD_PAID_TAG,  # 'gard paid'
)
from ghl_helpers import ghl_find_contact_by_phone, ghl_has_tag, ghl_log_action
from prospects_helpers import get_prospect_full_context
from sms_validator import validate_sms
from claude_scoring import call_claude

# JustCall SMS send config
JUSTCALL_API_KEY = "daf60d953694336f07c84c74205eb311dd85c996"
JUSTCALL_API_SECRET = "20612f8fcb80ef33845cbdc226bc8174853c82dd"
JUSTCALL_FROM = "14388020475"  # Formation XGuard main number

HAMZA_EMAIL = "hmaghraoui65@gmail.com"

# Throttle: don't SMS same contact more than once per 7 days
THROTTLE_DAYS = 7
MAX_SMS_PER_RUN = 10

LOG_DIR = Path(r"C:\Users\user\sac_logs")
_handlers = [logging.StreamHandler()]
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(
        str(LOG_DIR / f"smart_hot_leads_{datetime.now():%Y-%m-%d}.log"),
        encoding="utf-8",
    ))
except (PermissionError, OSError):
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_handlers,
)
log = logging.getLogger("smart_hot_leads")

DAYS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi",
           4: "Vendredi", 5: "Samedi", 6: "Dimanche"}


# ---------------------------------------------------------------------------
# Fetch leads (reuses logic from hot_leads.py)
# ---------------------------------------------------------------------------

def get_missed_calls(date_str):
    """Get today's missed calls (inbound, duration=0, work hours 8-18).
    Returns dict[normalized_number] -> {name, count, times, transcript_snippet}.
    """
    raw_calls = fetch_all_raw(date_str)
    missed = {}

    for c in raw_calls:
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
            missed[num]["times"].append(c.get("time", "")[-8:-3])
            missed[num]["last_time"] = c.get("time", "")

        if name and not missed[num]["name"]:
            missed[num]["name"] = name

    # Only keep truly missed (never answered today)
    return {k: v for k, v in missed.items() if v["missed_count"] > 0 and not v["answered"]}


def get_unanswered_sms(date_str):
    """Get today's unanswered inbound SMS."""
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
            # Collect last 3 inbound messages for context
            last_3 = [(s.get("sms_info", {}) or {}).get("body", "") or ""
                      for s in data["inbound"][-3:]]

            unanswered[num] = {
                "number": num,
                "name": name,
                "sms_count": len(data["inbound"]),
                "last_message": body[:500],
                "last_3_messages": last_3,
            }

    return unanswered


def build_leads(date_str):
    """Build list of leads from today's missed calls + unanswered SMS."""
    missed = get_missed_calls(date_str)
    sms = get_unanswered_sms(date_str)
    email_stats = fetch_email_stats(date_str)

    leads = {}

    # Missed calls
    for num, data in missed.items():
        leads[num] = {
            "number": num,
            "name": data["name"],
            "missed_count": data["missed_count"],
            "call_times": data["times"],
            "sms_count": 0,
            "sms_messages": [],
            "email_subject": "",
            "email_from": "",
            "channels": ["appel"],
            "priority": "MEDIUM",
        }

    # Merge SMS
    for num, data in sms.items():
        if num in leads:
            leads[num]["sms_count"] = data["sms_count"]
            leads[num]["sms_messages"] = data["last_3_messages"]
            leads[num]["channels"].append("SMS")
            leads[num]["priority"] = "URGENT"
            if not leads[num]["name"] and data["name"]:
                leads[num]["name"] = data["name"]
        else:
            leads[num] = {
                "number": num,
                "name": data["name"],
                "missed_count": 0,
                "call_times": [],
                "sms_count": data["sms_count"],
                "sms_messages": data["last_3_messages"],
                "email_subject": "",
                "email_from": "",
                "channels": ["SMS"],
                "priority": "HIGH",
            }

    # Sort by priority
    priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_leads = sorted(
        leads.values(),
        key=lambda l: (priority_order.get(l["priority"], 9), -l["missed_count"], -l["sms_count"]),
    )

    log.info("Leads built: %d total (missed=%d, sms=%d)",
             len(sorted_leads), len(missed), len(sms))
    return sorted_leads


# ---------------------------------------------------------------------------
# Throttle check
# ---------------------------------------------------------------------------

def recently_sms_sent(phone):
    """Check if we SMS'd this number in the last THROTTLE_DAYS days.
    Returns True if yes (should skip).
    Uses prospects_intelligence (which is aggregated nightly) for speed.
    """
    # Primary check: prospects_intelligence.last_our_sms_at
    try:
        from prospects_helpers import get_prospect
        p = get_prospect(phone=phone)
        if p and p.get("last_our_sms_at"):
            last_sms = datetime.fromisoformat(p["last_our_sms_at"].replace("Z", "+00:00"))
            if last_sms.tzinfo:
                now = datetime.now(last_sms.tzinfo)
            else:
                now = datetime.now()
            if (now - last_sms).days < THROTTLE_DAYS:
                return True
    except Exception as e:
        log.debug("prospects_intelligence check failed: %s — falling back", e)

    # Fallback: direct query on hot_sms_sent
    since = (datetime.now() - timedelta(days=THROTTLE_DAYS)).isoformat()
    rows = sb_get(
        f"hot_sms_sent?phone_number=eq.{phone}&status=in.(sent,would_send)"
        f"&sent_at=gte.{since}&select=id&limit=1"
    )
    return bool(rows) and not isinstance(rows, dict)


# ---------------------------------------------------------------------------
# Personalized SMS via Haiku
# ---------------------------------------------------------------------------

def build_context_prompt(lead):
    """Build a context-rich prompt for Haiku to generate a personalized SMS.
    Uses the full prospect history from prospects_intelligence if available.
    Falls back to today's data only if prospect not in the intelligence base.
    """
    name = lead.get("name") or ""
    first_name = name.split()[0] if name else ""
    phone = lead["number"]

    # Try to get full prospect history from prospects_intelligence
    full_context = None
    try:
        full_context = get_prospect_full_context(phone=phone, timeline_limit=10)
    except Exception as e:
        log.warning("  Could not fetch prospect intelligence: %s", e)

    # Build context
    context_parts = []

    # Today's activity (always include)
    today_parts = []
    if lead["missed_count"] > 0:
        times_str = ", ".join(lead["call_times"][:3])
        today_parts.append(
            f"- A appele {lead['missed_count']} fois AUJOURD'HUI a {times_str}, sans reponse."
        )
    if lead["sms_count"] > 0 and lead["sms_messages"]:
        sms_text = "\n".join(f'  "{m[:250]}"' for m in lead["sms_messages"] if m)
        today_parts.append(
            f"- A envoye {lead['sms_count']} SMS AUJOURD'HUI sans reponse. Messages:\n{sms_text}"
        )

    if today_parts:
        context_parts.append("CE QUI S'EST PASSE AUJOURD'HUI:")
        context_parts.extend(today_parts)

    # Full history from prospects_intelligence
    if full_context:
        p = full_context["prospect"]
        timeline = full_context.get("timeline", [])

        context_parts.append("")
        context_parts.append("HISTORIQUE COMPLET DE CE PROSPECT:")

        # Interested programs
        if p.get("program_interested"):
            context_parts.append(f"- Interesse par: {p['program_interested']}")
        elif p.get("programs_mentioned"):
            context_parts.append(f"- Programmes mentionnes: {', '.join(p['programs_mentioned'][:3])}")

        # Prior activity
        prior_calls = (p.get("total_calls", 0) or 0) - (lead["missed_count"] or 0)
        prior_sms = (p.get("total_sms_received", 0) or 0) - (lead["sms_count"] or 0)
        prior_emails = p.get("total_emails_received", 0) or 0

        if prior_calls > 0:
            answered = p.get("answered_calls", 0) or 0
            context_parts.append(f"- Historique appels (avant aujourd'hui): {prior_calls} appels ({answered} repondus)")
        if prior_sms > 0:
            context_parts.append(f"- Historique SMS: {prior_sms} SMS envoyes par lui avant aujourd'hui")
        if prior_emails > 0:
            context_parts.append(f"- Historique emails: {prior_emails} emails envoyes par lui")

        # Our prior outreach (to avoid repeating ourselves)
        times_we = p.get("times_we_contacted", 0) or 0
        if times_we > 0:
            last_sms_at = p.get("last_our_sms_at", "")[:10]
            last_body = (p.get("last_our_sms_body") or "")[:150]
            context_parts.append(
                f"- ATTENTION: on lui a DEJA envoye {times_we} SMS (dernier: {last_sms_at}). "
                f"Son dernier message de notre part etait: \"{last_body}\". "
                f"NE PAS repeter la meme chose."
            )

        # Last few timeline events (for context on what they asked)
        relevant_events = [e for e in timeline if e.get("event_type") in (
            "sms_inbound", "email_inbound", "call_inbound"
        )][:3]
        if relevant_events:
            context_parts.append("")
            context_parts.append("DERNIERES INTERACTIONS (inbound):")
            for ev in relevant_events:
                etype = ev.get("event_type", "").replace("_", " ")
                dt = (ev.get("event_date") or "")[:10]
                content = (ev.get("content_excerpt") or "").strip()[:200]
                if content:
                    context_parts.append(f"  [{dt}] {etype}: {content}")

    context = "\n".join(context_parts) if context_parts else "Aucun contexte disponible."

    prompt = f"""Tu rediges un SMS personnalise pour un PROSPECT (pas encore inscrit a la formation XGuard Academie).

CONTEXTE SUR {name or 'ce prospect'}:
{context}

OBJECTIF: Redige un SMS court (max 320 caracteres, idealement 160) qui:
1. Commence par "Bonjour {first_name or '[prenom]'}," (ou juste "Bonjour," si pas de nom)
2. Fait reference a CE QU'IL A DEMANDE specifiquement (si on sait — utilise le contexte ci-dessus)
3. Offre de l'aide ou une reponse a son interet precis
4. Termine par "Appelez-nous au (438) 802-0475 — Academie XGuard"

RULES STRICTES:
- Francais du Quebec, naturel, pas trop formel
- Ne pas dire "vous n'avez pas repondu" ou "on vous a manque" — ton positif
- Ne pas mentionner qu'il n'a pas paye, que c'est urgent, etc.
- Pas d'emojis
- Pas de guillemets dans le SMS
- Mentionne seulement des faits qu'on sait vraiment
- Si on lui a deja envoye un SMS, DIFFERENCIE (pas la meme chose 2 fois)
- Si aucun contexte utile: message generique mais chaleureux

Retourne UNIQUEMENT le texte du SMS (aucune explication, aucune markup)."""

    return prompt


def generate_personalized_sms(lead):
    """Generate a personalized SMS via Haiku. Returns the SMS body or None."""
    prompt = build_context_prompt(lead)
    try:
        sms_body = call_claude(prompt, model="haiku", timeout=45)
        if not sms_body:
            return None
        # Strip quotes if Haiku wrapped the response
        sms_body = sms_body.strip().strip('"').strip("'").strip()
        # Sanity check: reasonable length
        if len(sms_body) < 30 or len(sms_body) > 500:
            log.warning("SMS body suspicious length (%d): %s", len(sms_body), sms_body[:100])
            return None
        return sms_body
    except Exception as e:
        log.warning("Haiku SMS generation failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Send SMS via JustCall
# ---------------------------------------------------------------------------

def send_sms(phone, body):
    """Send SMS via JustCall API. Returns (success, response_text)."""
    url = "https://api.justcall.io/v1/texts/new"
    headers = {
        "Authorization": f"{JUSTCALL_API_KEY}:{JUSTCALL_API_SECRET}",
        "Content-Type": "application/json",
    }
    # phone should be 10 digits — JustCall handles +1 prefix
    to_number = phone if phone.startswith("1") else f"1{phone}"
    payload = {
        "from": JUSTCALL_FROM,
        "to": to_number,
        "body": body,
    }
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=30)
        ok = r.status_code in (200, 201)
        return ok, r.text[:500]
    except Exception as e:
        return False, f"Exception: {e}"


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

def track(phone, name, ghl_id, sms_body, context_summary, priority, status, error=None):
    try:
        sb_upsert("hot_sms_sent", {
            "phone_number": phone,
            "contact_name": name,
            "ghl_contact_id": ghl_id,
            "sms_body": sms_body,
            "context_summary": context_summary,
            "priority": priority,
            "status": status,
            "error": error[:500] if error else None,
            "sent_at": datetime.now().isoformat(),
            "run_date": date.today().isoformat(),
        })
    except Exception as e:
        log.warning("Track failed: %s", e)


# ---------------------------------------------------------------------------
# Email Nick with preview/summary
# ---------------------------------------------------------------------------

def send_summary_email(date_str, sent, dry_run):
    """Send summary email with SMS previews."""
    day_name = DAYS_FR.get(datetime.strptime(date_str, "%Y-%m-%d").weekday(), "")
    mode = "DRY RUN (preview only)" if dry_run else "PRODUCTION (SMS sent)"

    rows = ""
    for item in sent:
        sc = {"sent": "#2E7D32", "would_send": "#1565C0", "skipped_paid": "#777",
              "skipped_throttle": "#E65100", "skipped_limit": "#999", "error": "#C62828"}.get(item["status"], "#555")
        name = item.get("name") or "?"
        phone = f"+1{item['phone']}" if len(item['phone']) == 10 else item['phone']
        context = item.get("context_summary", "")
        sms = item.get("sms_body") or ""
        rows += f"""
        <tr style="border-bottom:1px solid #eee;">
          <td style="padding:8px;color:{sc};font-weight:bold;font-size:11px;">{item['status']}</td>
          <td style="padding:8px;"><strong style="font-size:12px;">{name}</strong><br><span style="font-size:11px;color:#1565C0;">{phone}</span><br><span style="font-size:10px;color:#999;">{item.get('priority', '')} | {context[:60]}</span></td>
          <td style="padding:8px;font-size:11px;color:#333;max-width:400px;">{sms[:500]}</td>
        </tr>"""

    # Summary counts
    counts = defaultdict(int)
    for item in sent:
        counts[item["status"]] += 1

    summary_rows = "".join(
        f'<td style="padding:8px;text-align:center;background:#f5f5f5;border:1px solid #eee;"><strong style="font-size:20px;">{v}</strong><br><small style="font-size:10px;color:#777;">{k}</small></td>'
        for k, v in sorted(counts.items(), key=lambda x: -x[1])
    )

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:900px;margin:0 auto;">
<div style="background:linear-gradient(135deg,#1B3A5C,#E65100);padding:20px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="color:white;margin:0;font-size:20px;">Smart Hot Leads SMS — {mode}</h1>
  <p style="color:#ffcdd2;margin:4px 0 0;font-size:12px;">{day_name} {date_str} | {len(sent)} leads traites</p>
</div>
<div style="padding:15px;border:1px solid #ddd;border-top:none;">
  <table style="width:100%;border-collapse:collapse;margin:0 0 15px;">
    <tr>{summary_rows}</tr>
  </table>
  <table style="width:100%;border-collapse:collapse;font-size:12px;">
    <tr style="background:#1B3A5C;color:white;">
      <th style="padding:8px;text-align:left;">Status</th>
      <th style="padding:8px;text-align:left;">Contact</th>
      <th style="padding:8px;text-align:left;">SMS redige</th>
    </tr>
    {rows}
  </table>
  <p style="margin-top:15px;font-size:11px;color:#777;">
    <strong>Regles:</strong> Max {MAX_SMS_PER_RUN} SMS/jour, 1 SMS par contact par {THROTTLE_DAYS} jours,
    skip si tag "{XGUARD_PAID_TAG}" dans GHL, skip si Haiku ne genere pas de texte.
  </p>
</div>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = NICK_EMAIL
    msg["Cc"] = HAMZA_EMAIL
    sent_count = counts.get("sent", 0) + counts.get("would_send", 0)
    msg["Subject"] = f"[Smart Hot Leads {'DRY' if dry_run else 'SENT'}] {date_str} — {sent_count} SMS"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [NICK_EMAIL, HAMZA_EMAIL], msg.as_string())
        log.info("Summary email sent to Nick + Hamza")
    except Exception as e:
        log.warning("Summary email failed: %s", e)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Generate SMS but don't send")
    parser.add_argument("--limit", type=int, default=MAX_SMS_PER_RUN, help="Max SMS to send")
    args = parser.parse_args()

    date_str = datetime.now().strftime("%Y-%m-%d")

    log.info("=" * 60)
    log.info("SMART HOT LEADS — %s — %s", date_str, "DRY RUN" if args.dry_run else "PRODUCTION")
    log.info("=" * 60)

    # Fetch leads
    leads = build_leads(date_str)
    if not leads:
        log.info("No leads today — nothing to do")
        return

    results = []
    sent_count = 0

    for i, lead in enumerate(leads, start=1):
        phone = lead["number"]
        name = lead.get("name") or ""
        priority = lead["priority"]
        context_summary = f"{lead['missed_count']} appels, {lead['sms_count']} SMS, {'+'.join(lead['channels'])}"

        log.info("[%d/%d] %s (%s) — %s", i, len(leads), name or phone, priority, context_summary)

        # Check daily limit
        if sent_count >= args.limit:
            log.info("  Daily limit reached (%d), skipping rest", args.limit)
            track(phone, name, None, "", context_summary, priority, "skipped_limit")
            results.append({
                "phone": phone, "name": name, "priority": priority,
                "context_summary": context_summary, "sms_body": "",
                "status": "skipped_limit",
            })
            continue

        # Check throttle
        if recently_sms_sent(phone):
            log.info("  Throttle hit (SMS sent in last %d days)", THROTTLE_DAYS)
            track(phone, name, None, "", context_summary, priority, "skipped_throttle")
            results.append({
                "phone": phone, "name": name, "priority": priority,
                "context_summary": context_summary, "sms_body": "",
                "status": "skipped_throttle",
            })
            continue

        # Check GHL — is this contact already paid?
        try:
            contact = ghl_find_contact_by_phone(phone)
            ghl_id = contact.get("id") if contact else None
            if contact and ghl_has_tag(contact, XGUARD_PAID_TAG):
                log.info("  SKIP — contact has '%s' tag (already paid)", XGUARD_PAID_TAG)
                track(phone, name, ghl_id, "", context_summary, priority, "skipped_paid")
                results.append({
                    "phone": phone, "name": name, "priority": priority,
                    "context_summary": context_summary, "sms_body": "",
                    "status": "skipped_paid",
                })
                continue
        except Exception as e:
            log.warning("  GHL lookup failed (%s) — proceeding anyway", e)
            ghl_id = None

        # Generate personalized SMS
        log.info("  Generating SMS via Haiku...")
        sms_body = generate_personalized_sms(lead)
        if not sms_body:
            log.warning("  Haiku failed — skipping (no generic fallback)")
            track(phone, name, ghl_id, "", context_summary, priority, "error",
                  error="Haiku returned empty")
            results.append({
                "phone": phone, "name": name, "priority": priority,
                "context_summary": context_summary, "sms_body": "",
                "status": "error",
            })
            continue

        log.info("  Generated SMS: %s", sms_body[:100])

        # VALIDATE the SMS before any send/dry-run logging
        is_valid, reason = validate_sms(sms_body, recipient_name=name)
        if not is_valid:
            log.warning("  SMS REJECTED by validator: %s", reason)
            track(phone, name, ghl_id, sms_body, context_summary, priority, "error",
                  error=f"Validator rejected: {reason}")
            results.append({
                "phone": phone, "name": name, "priority": priority,
                "context_summary": context_summary, "sms_body": sms_body,
                "status": "error",
            })
            continue

        # Send or dry-run
        if args.dry_run:
            track(phone, name, ghl_id, sms_body, context_summary, priority, "would_send")
            results.append({
                "phone": phone, "name": name, "priority": priority,
                "context_summary": context_summary, "sms_body": sms_body,
                "status": "would_send",
            })
            sent_count += 1
            continue

        # Real send
        ok, resp = send_sms(phone, sms_body)
        if ok:
            log.info("  SMS SENT")
            track(phone, name, ghl_id, sms_body, context_summary, priority, "sent")

            # Log to GHL as a note (so Hamza sees it in contact profile)
            if ghl_id:
                try:
                    ghl_log_action(
                        ghl_id,
                        action=f"SMS envoye automatique — Smart Hot Leads ({priority})",
                        details=f"Contexte: {context_summary}\n\nMessage:\n{sms_body}",
                    )
                except Exception as e:
                    log.warning("  GHL note add failed (non-critical): %s", e)

            results.append({
                "phone": phone, "name": name, "priority": priority,
                "context_summary": context_summary, "sms_body": sms_body,
                "status": "sent",
            })
            sent_count += 1
            time.sleep(1.5)  # JustCall rate limit
        else:
            log.error("  SMS FAILED: %s", resp[:200])
            track(phone, name, ghl_id, sms_body, context_summary, priority, "error", error=resp)
            results.append({
                "phone": phone, "name": name, "priority": priority,
                "context_summary": context_summary, "sms_body": sms_body,
                "status": "error",
            })

    log.info("")
    log.info("=" * 60)
    log.info("DONE — %d SMS %s", sent_count, "would-be-sent (dry run)" if args.dry_run else "sent")
    log.info("=" * 60)

    if results:
        send_summary_email(date_str, results, args.dry_run)


if __name__ == "__main__":
    main()
