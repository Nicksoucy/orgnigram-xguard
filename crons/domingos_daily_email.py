#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Domingos Daily Morning Email — runs at 7h45 AM on Nitro.
Sends an email to Domingos + Nick with:
1. Contacts to call back today (from GHL tasks)
2. Stale pipeline contacts (Contacted/Entente >5 days without activity)
3. Yesterday's call summary + scores (drone vs elite breakdown)
4. Quick coaching tip
"""

import json
import logging
import os
import smtplib
import sys
import time
from datetime import datetime, timedelta, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from collections import Counter

import requests

log = logging.getLogger("dom_email")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Config ──
PERSON_ID = "t11"
GHL_TOKEN = "pit-7de455ab-c46e-47a4-af9e-0b07a6c3a1ee"
GHL_LOCATION = "dfkLurZY2ADWAUZl4zYc"
GHL_BASE = "https://services.leadconnectorhq.com"
DRONE_PIPELINE = "W08jXuPPrQDM0EFcCgAR"

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"

# Domingos email TBD — for now send to Nick only
EMAIL_TO = "nick@darkhorseads.com"
EMAIL_CC = ""
GMAIL_USER = "nick@darkhorseads.com"
GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"

GHL_HEADERS = {"Authorization": f"Bearer {GHL_TOKEN}", "Version": "2021-07-28"}

STAGES = {
    "549aefdf-3c35-477d-a75c-15b7f5f77e27": "New Lead",
    "1b0180bc-30b0-46b1-a680-7d9e7538f3cb": "First Call",
    "49ec08d3-74d9-49ee-bc6d-c55b9312ff1c": "Contacted",
    "f4310447-c612-4c4b-be62-bfc818e6fcc7": "Entente",
    "bc4ebcda-f447-41e0-beb9-e0fb3fafc4bb": "Closed",
    "af6bc38a-91fa-4fca-9e6f-4bad82cbbee9": "Lost",
}


def get_callbacks_today():
    """Get GHL opportunities with tasks due today or overdue."""
    today = datetime.now().strftime("%Y-%m-%d")
    callbacks = []

    all_opps = []
    for page in range(1, 20):
        r = requests.get(f"{GHL_BASE}/opportunities/search",
            params={"location_id": GHL_LOCATION, "pipeline_id": DRONE_PIPELINE, "limit": 100, "page": page},
            headers=GHL_HEADERS, timeout=30)
        if r.status_code != 200: break
        opps = r.json().get("opportunities", [])
        if not opps: break
        all_opps.extend(opps)
        if len(opps) < 100: break
        time.sleep(0.3)

    for opp in all_opps:
        cid = opp.get("contactId")
        stage = STAGES.get(opp.get("pipelineStageId", ""), "?")
        if stage in ("Closed", "Lost", "New Lead"): continue

        try:
            r = requests.get(f"{GHL_BASE}/contacts/{cid}/tasks", headers=GHL_HEADERS, timeout=10)
            if r.status_code != 200: continue
            tasks = r.json().get("tasks", [])
            if not isinstance(tasks, list): continue
            for t in tasks:
                if not isinstance(t, dict): continue
                if t.get("completed"): continue
                due = str(t.get("dueDate", ""))[:10]
                if due and due <= today:
                    callbacks.append({
                        "name": opp.get("name", "?"),
                        "phone": opp.get("contact", {}).get("phone", ""),
                        "stage": stage,
                        "task": t.get("title", ""),
                        "due": due,
                        "overdue": due < today,
                    })
        except: continue
        time.sleep(0.1)

    return sorted(callbacks, key=lambda x: (not x["overdue"], x["due"]))


def get_stale_pipeline(days=5):
    """Get Contacted/Entente contacts with no recent activity."""
    stale = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    for stage_id in ["49ec08d3-74d9-49ee-bc6d-c55b9312ff1c", "f4310447-c612-4c4b-be62-bfc818e6fcc7"]:
        r = requests.get(f"{GHL_BASE}/opportunities/search",
            params={"location_id": GHL_LOCATION, "pipeline_id": DRONE_PIPELINE,
                    "pipeline_stage_id": stage_id, "limit": 100},
            headers=GHL_HEADERS, timeout=30)
        if r.status_code != 200: continue
        for opp in r.json().get("opportunities", []):
            updated = opp.get("updatedAt", "")
            if updated:
                try:
                    up_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if up_dt < cutoff:
                        stale.append({
                            "name": opp.get("name", "?"),
                            "phone": opp.get("contact", {}).get("phone", ""),
                            "stage": STAGES.get(opp.get("pipelineStageId",""), "?"),
                            "days_stale": (now - up_dt).days,
                        })
                except: continue
        time.sleep(0.3)

    return sorted(stale, key=lambda x: x["days_stale"], reverse=True)


def get_yesterday_scores():
    """Get yesterday's call scores from Supabase."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    r = requests.get(f"{SUPABASE_URL}/rest/v1/calls",
        params={"person_id": f"eq.{PERSON_ID}", "call_time": f"like.{yesterday}%",
                "order": "ai_global_score.desc.nullslast"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}, timeout=15)
    return r.json() if r.status_code == 200 else []


def build_html(callbacks, stale, scores, yesterday_str):
    today = datetime.now()
    day_names = {0:"Lundi",1:"Mardi",2:"Mercredi",3:"Jeudi",4:"Vendredi",5:"Samedi",6:"Dimanche"}
    day_name = day_names.get(today.weekday(), "")

    def sc(s):
        if s >= 6: return "#38a169"
        if s >= 4: return "#d69e2e"
        return "#e53e3e"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body {{ font-family: -apple-system, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 16px; background: #f5f5f5; color: #1a1a1a; }}
.card {{ background: #fff; border-radius: 12px; padding: 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.header {{ background: linear-gradient(135deg, #2d3748, #4a5568); color: #fff; border-radius: 12px; padding: 20px; text-align: center; }}
h3 {{ margin: 0 0 12px; font-size: 15px; color: #333; }}
.stat {{ display: inline-block; text-align: center; padding: 8px 16px; }}
.stat-num {{ font-size: 24px; font-weight: 700; }}
.stat-label {{ font-size: 11px; color: #888; }}
.row {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
.overdue {{ color: #e53e3e; font-weight: 600; }}
.tip {{ background: #ebf8ff; border-left: 4px solid #3182ce; padding: 12px; border-radius: 0 8px 8px 0; margin: 8px 0; }}
.drone {{ color: #3182ce; }} .elite {{ color: #805ad5; }}
</style></head><body>

<div class="header">
    <h2 style="margin:0;">🚁 Bonjour Domingos!</h2>
    <p style="margin:8px 0 0;opacity:0.9;">{day_name} {today.strftime('%d %B %Y')} — Drone & Elite</p>
</div>"""

    # Callbacks
    html += f'<div class="card"><h3>📞 Rappels aujourd\'hui ({len(callbacks)})</h3>'
    if callbacks:
        for cb in callbacks[:15]:
            od = ' <span class="overdue">(EN RETARD)</span>' if cb["overdue"] else ""
            html += f'<div class="row"><strong>{cb["name"]}</strong>{od}<br>'
            html += f'<span style="color:#666;">{cb["stage"]} — {cb["task"]}</span><br>'
            html += f'<span style="color:#888;">{cb["phone"]}</span></div>'
    else:
        html += '<p style="color:#888;">Aucun rappel prevu.</p>'
    html += '</div>'

    # Stale
    if stale:
        html += f'<div class="card"><h3>⚠️ Pipeline sans suivi ({len(stale[:15])})</h3>'
        for s in stale[:15]:
            html += f'<div class="row"><strong>{s["name"]}</strong> — {s["stage"]} — {s["days_stale"]}j sans activite<br>'
            html += f'<span style="color:#888;">{s["phone"]}</span></div>'
        html += '</div>'

    # Yesterday scores
    if scores:
        scored = [s for s in scores if s.get("ai_global_score")]
        avg = sum(s.get("ai_global_score",0) for s in scored) / len(scored) if scored else 0
        # Classification breakdown
        cls = Counter(s.get("classification","?") for s in scored)

        html += f'<div class="card"><h3>📊 Hier ({yesterday_str})</h3>'
        html += '<div style="text-align:center;">'
        html += f'<div class="stat"><div class="stat-num">{len(scores)}</div><div class="stat-label">Appels</div></div>'
        html += f'<div class="stat"><div class="stat-num" style="color:{sc(avg)}">{avg:.1f}</div><div class="stat-label">Score /10</div></div>'
        if cls.get("drone"): html += f'<div class="stat"><div class="stat-num drone">{cls["drone"]}</div><div class="stat-label">Drone</div></div>'
        if cls.get("elite"): html += f'<div class="stat"><div class="stat-num elite">{cls["elite"]}</div><div class="stat-label">Elite</div></div>'
        html += '</div></div>'

    html += """<div style="text-align:center;margin:20px 0;color:#aaa;font-size:11px;">
    🤖 Coaching XGuard — Drone & Elite
</div></body></html>"""
    return html


def main():
    log.info("=== Domingos Daily Email ===")
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    log.info("Fetching callbacks...")
    callbacks = get_callbacks_today()
    log.info("  %d callbacks", len(callbacks))

    log.info("Fetching stale pipeline...")
    stale = get_stale_pipeline(5)
    log.info("  %d stale", len(stale))

    log.info("Fetching yesterday scores...")
    scores = get_yesterday_scores()
    log.info("  %d scores", len(scores))

    html = build_html(callbacks, stale, scores, yesterday_str)

    day_names = {0:"Lundi",1:"Mardi",2:"Mercredi",3:"Jeudi",4:"Vendredi",5:"Samedi",6:"Dimanche"}
    day_name = day_names.get(datetime.now().weekday(), "")

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = f"🚁 Coaching Domingos {day_name} {today_str}"
    msg.attach(MIMEText(html, "html", "utf-8"))

    recipients = [EMAIL_TO]
    if EMAIL_CC:
        msg["Cc"] = EMAIL_CC
        recipients.append(EMAIL_CC)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        log.info("Email sent!")
    except Exception as e:
        log.error("Email failed: %s", e)


if __name__ == "__main__":
    main()
