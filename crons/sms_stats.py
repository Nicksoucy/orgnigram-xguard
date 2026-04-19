"""
SMS Stats — Fetch and analyze JustCall SMS for a given date.
Detects unanswered inbound, cross-references with calls, classifies by intent.
"""

import json
import logging
import re
import time
from collections import defaultdict
from datetime import datetime

import requests

JUSTCALL_SMS_URL = "https://api.justcall.io/v2.1/texts"
JUSTCALL_API_KEY = "daf60d953694336f07c84c74205eb311dd85c996"
JUSTCALL_API_SECRET = "20612f8fcb80ef33845cbdc226bc8174853c82dd"

log = logging.getLogger("sms_stats")


def fetch_sms_for_date(date_str):
    """Fetch all SMS for a specific date from JustCall v2.1 API."""
    headers = {"Authorization": f"{JUSTCALL_API_KEY}:{JUSTCALL_API_SECRET}"}
    all_sms = []
    page = 1

    while page <= 20:
        try:
            resp = requests.get(
                f"{JUSTCALL_SMS_URL}?per_page=100&page={page}",
                headers=headers, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            sms_list = data.get("data", [])
            if not sms_list:
                break

            on_date = [s for s in sms_list if s.get("sms_date", "") == date_str]
            before_date = [s for s in sms_list if (s.get("sms_date", "") or "") < date_str]
            all_sms.extend(on_date)

            # Stop if we went past the target date
            if before_date:
                break
            if len(sms_list) < 100:
                break
            page += 1
            time.sleep(0.5)
        except Exception as e:
            log.warning("SMS fetch error (page %d): %s", page, e)
            break

    return all_sms


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

INTENT_PATTERNS = {
    "inscription": re.compile(
        r"(inscrire|inscription|formation|cours|m'inscrire|je veux faire|"
        r"je souhaite|je voudrais faire|commencer|s'inscrire)", re.I),
    "paiement": re.compile(
        r"(paiement|payer|payé|virement|interac|e-transfer|montant|facture|"
        r"reçu|350|400|450|147)", re.I),
    "info": re.compile(
        r"(information|renseignement|combien|prix|tarif|horaire|date|"
        r"quand|comment|adresse|où|coût)", re.I),
    "plainte": re.compile(
        r"(plainte|mécontent|insatisfait|rembours|annuler|annulation|problème|"
        r"déçu|erreur)", re.I),
    "suivi": re.compile(
        r"(confirmer|confirmation|reçu|envoyé|lien|email|courriel|mail|"
        r"certificat|document|attestation)", re.I),
    "contact_info": re.compile(
        r"(@gmail|@hotmail|@yahoo|@outlook|voici mon|mon numéro|mon mail|"
        r"mon email|mon adresse)", re.I),
}


def classify_sms(body):
    """Classify SMS by intent. Returns list of matching intents."""
    if not body:
        return ["autre"]
    intents = []
    for intent, pattern in INTENT_PATTERNS.items():
        if pattern.search(body):
            intents.append(intent)
    return intents if intents else ["autre"]


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_sms(sms_list, date_str, call_numbers=None):
    """Analyze SMS for a given date.
    call_numbers: set of contact numbers that also called today (for cross-ref).
    Returns comprehensive stats."""
    inbound = [s for s in sms_list if s.get("direction") == "Incoming"]
    outbound = [s for s in sms_list if s.get("direction") != "Incoming"]

    if call_numbers is None:
        call_numbers = set()

    # Group by contact
    by_contact = defaultdict(lambda: {"in": [], "out": [], "name": ""})
    for s in sms_list:
        num = s.get("contact_number", "")
        if not num:
            continue
        body = s.get("sms_info", {}).get("body", "") if isinstance(s.get("sms_info"), dict) else ""
        entry = {
            "time": s.get("sms_time", ""),
            "body": body,
            "direction": s.get("direction", ""),
            "delivered": s.get("delivery_status", ""),
        }
        if s.get("direction") == "Incoming":
            by_contact[num]["in"].append(entry)
        else:
            by_contact[num]["out"].append(entry)
        if s.get("contact_name"):
            by_contact[num]["name"] = s["contact_name"]

    # Find unanswered inbound (contacts who sent SMS but got no reply today)
    unanswered = []
    for num, data in by_contact.items():
        if data["in"] and not data["out"]:
            last_in = data["in"][-1]
            intents = classify_sms(last_in["body"])
            unanswered.append({
                "number": num,
                "name": data["name"],
                "count": len(data["in"]),
                "last_message": last_in["body"][:150],
                "last_time": last_in["time"],
                "intents": intents,
                "is_hot_lead": any(i in intents for i in ["inscription", "paiement"]),
            })

    # Sort: hot leads first, then by count
    unanswered.sort(key=lambda x: (-x["is_hot_lead"], -x["count"]))

    # Classify all inbound
    intent_counts = defaultdict(int)
    for s in inbound:
        body = s.get("sms_info", {}).get("body", "") if isinstance(s.get("sms_info"), dict) else ""
        for intent in classify_sms(body):
            intent_counts[intent] += 1

    # Hot leads (inbound mentioning inscription or paiement)
    hot_leads = []
    for s in inbound:
        body = s.get("sms_info", {}).get("body", "") if isinstance(s.get("sms_info"), dict) else ""
        intents = classify_sms(body)
        if any(i in intents for i in ["inscription", "paiement"]):
            hot_leads.append({
                "name": s.get("contact_name", s.get("contact_number", "")),
                "number": s.get("contact_number", ""),
                "time": s.get("sms_time", ""),
                "body": body[:150],
                "intents": intents,
            })

    # Response time: for contacts with both in and out, calculate avg response time
    response_times = []
    for num, data in by_contact.items():
        if data["in"] and data["out"]:
            for in_msg in data["in"]:
                # Find earliest outbound after this inbound
                in_time = in_msg["time"]
                for out_msg in data["out"]:
                    out_time = out_msg["time"]
                    if out_time > in_time:
                        try:
                            t_in = datetime.strptime(in_time, "%H:%M:%S")
                            t_out = datetime.strptime(out_time, "%H:%M:%S")
                            diff_min = (t_out - t_in).total_seconds() / 60
                            if diff_min > 0:
                                response_times.append(diff_min)
                        except Exception:
                            pass
                        break

    avg_response_min = round(sum(response_times) / len(response_times)) if response_times else None

    # Cross-reference with calls
    sms_and_called = []
    for num, data in by_contact.items():
        if num in call_numbers and data["in"]:
            sms_and_called.append({
                "number": num,
                "name": data["name"],
                "sms_count": len(data["in"]),
                "last_sms": data["in"][-1]["body"][:80],
            })

    return {
        "date": date_str,
        "total": len(sms_list),
        "inbound": len(inbound),
        "outbound": len(outbound),
        "unique_contacts": len(by_contact),
        "unanswered": unanswered,
        "unanswered_count": len(unanswered),
        "hot_leads": hot_leads,
        "hot_leads_count": len(hot_leads),
        "intent_breakdown": dict(sorted(intent_counts.items(), key=lambda x: -x[1])),
        "avg_response_min": avg_response_min,
        "sms_and_called": sms_and_called,
        "sms_and_called_count": len(sms_and_called),
    }


# ---------------------------------------------------------------------------
# HTML for email report
# ---------------------------------------------------------------------------

def sms_html_section(stats):
    """Generate HTML section for the daily email report."""
    if stats["total"] == 0:
        return ""

    # Unanswered rows
    unanswered_rows = ""
    for u in stats["unanswered"][:5]:
        hot = ' style="color:#C62828;font-weight:bold;"' if u["is_hot_lead"] else ""
        intents = ", ".join(u["intents"])
        unanswered_rows += f"""
        <tr>
          <td style="padding:5px;font-size:11px;"{' style="color:#C62828;"' if u['is_hot_lead'] else ''}>{u['name'] or u['number']}</td>
          <td style="padding:5px;text-align:center;font-size:11px;">{u['count']}</td>
          <td style="padding:5px;font-size:11px;color:#777;">{u['last_message'][:60]}</td>
          <td style="padding:5px;font-size:11px;">{intents}</td>
        </tr>"""

    # Hot leads rows
    hot_rows = ""
    for h in stats["hot_leads"][:5]:
        hot_rows += f"""
        <tr>
          <td style="padding:5px;font-size:11px;font-weight:bold;color:#C62828;">{h['name'] or h['number']}</td>
          <td style="padding:5px;font-size:11px;">{h['time'][:5]}</td>
          <td style="padding:5px;font-size:11px;">{h['body'][:80]}</td>
        </tr>"""

    resp_time_str = f"{stats['avg_response_min']} min" if stats.get('avg_response_min') else "N/A"
    resp_color = "#2E7D32" if stats.get('avg_response_min') and stats['avg_response_min'] <= 15 else "#E65100" if stats.get('avg_response_min') and stats['avg_response_min'] <= 60 else "#C62828"
    cross_count = stats.get("sms_and_called_count", 0)

    html = f"""
<h2 style="color:#1B3A5C;border-bottom:2px solid #1B3A5C;padding-bottom:5px;font-size:15px;">SMS ({stats['total']} total | {stats['inbound']} entrants | {stats['outbound']} sortants)</h2>

<table style="width:100%;border-collapse:collapse;margin:0 0 10px;font-size:12px;">
<tr>
  <td style="padding:10px;text-align:center;background:#E3F2FD;border:1px solid #eee;">
    <div style="font-size:22px;font-weight:bold;color:#1B3A5C;">{stats['inbound']}</div>
    <div style="font-size:10px;color:#777;">Entrants</div>
  </td>
  <td style="padding:10px;text-align:center;background:#E3F2FD;border:1px solid #eee;">
    <div style="font-size:22px;font-weight:bold;color:#1B3A5C;">{stats['outbound']}</div>
    <div style="font-size:10px;color:#777;">Sortants</div>
  </td>
  <td style="padding:10px;text-align:center;background:{'#FFEBEE' if stats['unanswered_count'] > 0 else '#E8F5E9'};border:1px solid #eee;">
    <div style="font-size:22px;font-weight:bold;color:{'#C62828' if stats['unanswered_count'] > 0 else '#2E7D32'};">{stats['unanswered_count']}</div>
    <div style="font-size:10px;color:#777;">Non-repondus</div>
  </td>
  <td style="padding:10px;text-align:center;background:{'#FFEBEE' if stats['hot_leads_count'] > 0 else '#f5f5f5'};border:1px solid #eee;">
    <div style="font-size:22px;font-weight:bold;color:{'#C62828' if stats['hot_leads_count'] > 0 else '#777'};">{stats['hot_leads_count']}</div>
    <div style="font-size:10px;color:#777;">Leads chauds</div>
  </td>
  <td style="padding:10px;text-align:center;background:#f5f5f5;border:1px solid #eee;">
    <div style="font-size:22px;font-weight:bold;color:{resp_color};">{resp_time_str}</div>
    <div style="font-size:10px;color:#777;">Temps rep. moy.</div>
  </td>
  <td style="padding:10px;text-align:center;background:#f5f5f5;border:1px solid #eee;">
    <div style="font-size:22px;font-weight:bold;color:#1B3A5C;">{cross_count}</div>
    <div style="font-size:10px;color:#777;">SMS + Appel</div>
  </td>
</tr></table>
"""

    if stats["hot_leads"]:
        html += f"""
<div style="background:#FFEBEE;border-left:4px solid #C62828;padding:8px 12px;margin:0 0 10px;font-size:12px;">
  <strong style="color:#C62828;">LEADS CHAUDS — a rappeler en priorite!</strong>
  <table style="margin-top:5px;width:100%;"><tr style="color:#777;font-size:11px;"><th style="text-align:left;padding:3px;">Client</th><th style="padding:3px;">Heure</th><th style="text-align:left;padding:3px;">Message</th></tr>
  {hot_rows}</table>
</div>"""

    if stats.get("sms_and_called"):
        cross_rows = ""
        for cr in stats["sms_and_called"][:5]:
            cross_rows += f"""
        <tr>
          <td style="padding:5px;font-size:11px;font-weight:bold;">{cr['name'] or cr['number']}</td>
          <td style="padding:5px;text-align:center;font-size:11px;">{cr['sms_count']}</td>
          <td style="padding:5px;font-size:11px;color:#777;">{cr['last_sms']}</td>
        </tr>"""
        html += f"""
<div style="background:#E3F2FD;border-left:4px solid #1565C0;padding:8px 12px;margin:0 0 10px;font-size:12px;">
  <strong style="color:#1565C0;">Clients qui ont SMS + appele ({stats['sms_and_called_count']})</strong>
  <div style="color:#777;font-size:11px;margin:2px 0 5px;">Ces clients essaient de vous joindre par tous les moyens — priorite haute!</div>
  <table style="width:100%;"><tr style="color:#777;font-size:11px;"><th style="text-align:left;padding:3px;">Client</th><th style="padding:3px;">SMS</th><th style="text-align:left;padding:3px;">Dernier message</th></tr>
  {cross_rows}</table>
</div>"""

    if stats["unanswered"]:
        html += f"""
<div style="background:#FFF8E1;border-left:4px solid #F57F17;padding:8px 12px;margin:0 0 10px;font-size:12px;">
  <strong>SMS entrants non-repondus ({stats['unanswered_count']})</strong>
  <table style="margin-top:5px;width:100%;"><tr style="color:#777;font-size:11px;"><th style="text-align:left;padding:3px;">Client</th><th style="padding:3px;">SMS</th><th style="text-align:left;padding:3px;">Message</th><th style="text-align:left;padding:3px;">Type</th></tr>
  {unanswered_rows}</table>
</div>"""

    return html


# ---------------------------------------------------------------------------
# Main (standalone test)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    log.info("Fetching SMS for %s...", date_str)

    sms_list = fetch_sms_for_date(date_str)
    log.info("Found %d SMS", len(sms_list))

    stats = analyze_sms(sms_list, date_str)

    print(f"\n{'='*60}")
    print(f"  SMS STATS — {date_str}")
    print(f"{'='*60}")
    print(f"Total: {stats['total']} | Entrants: {stats['inbound']} | Sortants: {stats['outbound']}")
    print(f"Contacts uniques: {stats['unique_contacts']}")
    print(f"Non-repondus: {stats['unanswered_count']}")
    print(f"Leads chauds: {stats['hot_leads_count']}")
    print(f"\nIntentions:")
    for intent, count in stats['intent_breakdown'].items():
        print(f"  {intent}: {count}")
    if stats['hot_leads']:
        print(f"\nLEADS CHAUDS:")
        for h in stats['hot_leads'][:5]:
            print(f"  {h['name']} ({h['time'][:5]}) — {h['body'][:80]}")
    if stats['unanswered']:
        print(f"\nNON-REPONDUS:")
        for u in stats['unanswered'][:5]:
            print(f"  {u['name'] or u['number']} ({u['count']}x) — {u['last_message'][:80]}")
