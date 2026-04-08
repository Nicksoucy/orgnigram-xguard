#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heidys Daily Morning Email — runs at 7h30 AM on Nitro.
Sends an email to Heidys with:
1. Contacts to call back today (from GHL tasks)
2. Stale "En discussion" contacts (>3 days without activity)
3. Yesterday's call summary + scores
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

import requests

log = logging.getLogger("heidys_email")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

# ── Config ──
PERSON_ID = "v1"
GHL_TOKEN = "pit-7de455ab-c46e-47a4-af9e-0b07a6c3a1ee"
GHL_LOCATION = "dfkLurZY2ADWAUZl4zYc"
GHL_BASE = "https://services.leadconnectorhq.com"
PIPELINE_ID = "7vru0wO6zRcDJsfQGdFI"
HEIDYS_USER_ID = "FqpS2HfIklBPAiAoANBB"

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"

EMAIL_TO = "garheidys@gmail.com"
EMAIL_CC = "nick@darkhorseads.com"
GMAIL_USER = "nick@darkhorseads.com"
GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"
REPORT_DIR = r"C:\Users\user\heidys_reports"

GHL_HEADERS = {
    "Authorization": f"Bearer {GHL_TOKEN}",
    "Version": "2021-07-28",
}

STAGE_NAMES = {
    "9daa83bb-9d5f-45f2-8680-c051f004504d": "New Lead",
    "060af548-de56-4ba8-94f1-6f0678853da7": "Premier Appel",
    "17eaccbf-33f3-44e2-896d-68a6724af217": "2ieme appel",
    "06fff6c8-b951-446b-abfb-ce6be126028f": "En discussion",
    "038708d0-9e77-4595-b5c0-46a2f98bcdc2": "Entente Envoyé",
    "f32a33ea-c7be-4faa-8a6e-43ef52256f74": "Gagné",
    "cb0ae9bc-0f6e-4f28-93a1-482b905aa65a": "Lost",
}


def get_ghl_callbacks_today():
    """Get all GHL opportunities with tasks due today or overdue."""
    today = datetime.now().strftime("%Y-%m-%d")
    callbacks = []

    # Get all opportunities in active stages
    all_opps = []
    for page in range(1, 10):
        r = requests.get(f"{GHL_BASE}/opportunities/search",
            params={"location_id": GHL_LOCATION, "pipeline_id": PIPELINE_ID, "limit": 100, "page": page},
            headers=GHL_HEADERS, timeout=30)
        if r.status_code != 200:
            break
        opps = r.json().get("opportunities", [])
        if not opps:
            break
        all_opps.extend(opps)
        if len(opps) < 100:
            break
        time.sleep(0.3)

    # Check tasks for each contact + enrich with call history
    for opp in all_opps:
        cid = opp.get("contactId")
        stage = STAGE_NAMES.get(opp.get("pipelineStageId", ""), "?")
        if stage in ("Gagné", "Lost"):
            continue

        try:
            r = requests.get(f"{GHL_BASE}/contacts/{cid}/tasks", headers=GHL_HEADERS, timeout=10)
            if r.status_code != 200:
                continue
            tasks = r.json().get("tasks", [])
            if not isinstance(tasks, list):
                continue

            # Only show tasks due within last 7 days (avoid 688+ accumulated overdue)
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            pending_tasks = []
            for t in tasks:
                if not isinstance(t, dict):
                    continue
                if t.get("completed") or t.get("status") == "completed":
                    continue
                due = str(t.get("dueDate", ""))[:10]
                if due and due <= today and due >= week_ago:
                    pending_tasks.append(t)

            if not pending_tasks:
                continue

            # Enrich: get call history for this contact
            last_call_date = None
            last_call_dur = 0
            total_calls = 0
            last_call_summary = ""
            last_objections = ""
            last_score = None

            try:
                r2 = requests.get(f"{GHL_BASE}/conversations/search",
                    params={"locationId": GHL_LOCATION, "contactId": cid, "limit": 1},
                    headers=GHL_HEADERS, timeout=10)
                if r2.status_code == 200:
                    convs = r2.json().get("conversations", [])
                    if convs:
                        conv_id = convs[0]["id"]
                        r3 = requests.get(f"{GHL_BASE}/conversations/{conv_id}/messages",
                            params={"locationId": GHL_LOCATION, "limit": 30},
                            headers=GHL_HEADERS, timeout=10)
                        if r3.status_code == 200:
                            raw = r3.json().get("messages", {})
                            if isinstance(raw, dict): raw = raw.get("messages", [])
                            for msg in raw:
                                if not isinstance(msg, dict): continue
                                if msg.get("messageType") == "TYPE_CALL":
                                    meta_call = msg.get("meta", {}).get("call", {}) if isinstance(msg.get("meta"), dict) else {}
                                    dur = meta_call.get("duration") or 0
                                    if dur > 0:
                                        total_calls += 1
                                        call_date = msg.get("dateAdded", "")[:16]
                                        if not last_call_date or call_date > last_call_date:
                                            last_call_date = call_date
                                            last_call_dur = dur
            except Exception:
                pass

            # Check Supabase for AI scores on this contact's calls
            phone = opp.get("contact", {}).get("phone", "")
            if phone:
                try:
                    sb_headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
                    r4 = requests.get(f"{SUPABASE_URL}/rest/v1/call_registry",
                        params={"contact_phone": f"eq.{phone}", "person_id": f"eq.{PERSON_ID}",
                                "order": "call_time.desc", "limit": "1"},
                        headers=sb_headers, timeout=10)
                    if r4.status_code == 200:
                        rows = r4.json()
                        if rows:
                            last_score = rows[0].get("ai_global_score")
                            last_call_summary = rows[0].get("call_summary", "")
                except Exception:
                    pass

            for t in pending_tasks:
                due = str(t.get("dueDate", ""))[:10]
                callbacks.append({
                    "name": opp.get("name", "?"),
                    "phone": phone,
                    "stage": stage,
                    "task": t.get("title", ""),
                    "due": due,
                    "overdue": due < today,
                    # Enriched context
                    "total_calls": total_calls,
                    "last_call_date": last_call_date,
                    "last_call_dur": last_call_dur,
                    "last_score": last_score,
                    "last_summary": last_call_summary[:150] if last_call_summary else "",
                })
        except Exception:
            continue
        time.sleep(0.12)

    return sorted(callbacks, key=lambda x: (not x["overdue"], x["due"]))


def get_stale_discussions(days=3):
    """Get 'En discussion' contacts with no recent activity."""
    stale = []
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    r = requests.get(f"{GHL_BASE}/opportunities/search",
        params={"location_id": GHL_LOCATION, "pipeline_id": PIPELINE_ID,
                "pipeline_stage_id": "06fff6c8-b951-446b-abfb-ce6be126028f", "limit": 100},
        headers=GHL_HEADERS, timeout=30)
    if r.status_code != 200:
        return []

    opps = r.json().get("opportunities", [])
    for opp in opps:
        updated = opp.get("updatedAt", "")
        if updated:
            try:
                up_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                if up_dt < cutoff:
                    days_stale = (now - up_dt).days
                    phone = opp.get("contact", {}).get("phone", "")

                    # Enrich with last call from call_registry
                    last_summary = ""
                    last_score = None
                    if phone:
                        try:
                            sb_headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
                            r5 = requests.get(f"{SUPABASE_URL}/rest/v1/call_registry",
                                params={"contact_phone": f"eq.{phone}", "person_id": f"eq.{PERSON_ID}",
                                        "order": "call_time.desc", "limit": "1"},
                                headers=sb_headers, timeout=10)
                            if r5.status_code == 200 and r5.json():
                                last_summary = r5.json()[0].get("call_summary", "")[:120]
                                last_score = r5.json()[0].get("ai_global_score")
                        except Exception:
                            pass

                    stale.append({
                        "name": opp.get("name", "?"),
                        "phone": phone,
                        "days_stale": days_stale,
                        "last_summary": last_summary,
                        "last_score": last_score,
                    })
            except Exception:
                continue

    return sorted(stale, key=lambda x: x["days_stale"], reverse=True)


def get_yesterday_scores():
    """Get yesterday's call scores from Supabase."""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    sb_headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

    r = requests.get(f"{SUPABASE_URL}/rest/v1/calls",
        params={"person_id": f"eq.{PERSON_ID}", "call_time": f"like.{yesterday}%", "order": "ai_global_score.desc.nullslast"},
        headers=sb_headers, timeout=15)

    if r.status_code == 200:
        return r.json()
    return []


def build_email_html(callbacks, stale, scores, yesterday_str):
    """Build the daily coaching email HTML."""
    day_names = {0:"Lundi",1:"Mardi",2:"Mercredi",3:"Jeudi",4:"Vendredi",5:"Samedi",6:"Dimanche"}
    today = datetime.now()
    day_name = day_names.get(today.weekday(), "")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
body {{ font-family: -apple-system, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 16px; background: #f5f5f5; color: #1a1a1a; }}
.card {{ background: #fff; border-radius: 12px; padding: 16px; margin: 12px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
.header {{ background: linear-gradient(135deg, #667eea, #764ba2); color: #fff; border-radius: 12px; padding: 20px; text-align: center; }}
h2 {{ margin: 0 0 8px; font-size: 18px; }}
h3 {{ margin: 0 0 12px; font-size: 15px; color: #333; }}
.stat {{ display: inline-block; text-align: center; padding: 8px 16px; }}
.stat-num {{ font-size: 24px; font-weight: 700; }}
.stat-label {{ font-size: 11px; color: #888; }}
.callback {{ padding: 8px 0; border-bottom: 1px solid #eee; }}
.overdue {{ color: #e53e3e; font-weight: 600; }}
.stale {{ color: #dd6b20; }}
.score-good {{ color: #38a169; }}
.score-mid {{ color: #d69e2e; }}
.score-bad {{ color: #e53e3e; }}
.tip {{ background: #ebf8ff; border-left: 4px solid #3182ce; padding: 12px; border-radius: 0 8px 8px 0; margin: 8px 0; }}
</style></head><body>

<div class="header">
    <h2>☀️ Bonjour Heidys!</h2>
    <p>{day_name} {today.strftime('%d %B %Y')}</p>
</div>
"""

    # Section 1: Callbacks
    html += '<div class="card">'
    html += f'<h3>📞 Contacts a rappeler aujourd\'hui ({len(callbacks)})</h3>'
    if callbacks:
        for cb in callbacks[:15]:
            overdue_tag = ' <span class="overdue">(EN RETARD)</span>' if cb["overdue"] else ""
            html += f'<div class="callback">'
            html += f'<strong>{cb["name"]}</strong>{overdue_tag}<br>'
            html += f'<span style="color:#666;">{cb["stage"]} — {cb["task"]}</span><br>'
            # Enriched context
            ctx_parts = []
            if cb.get("total_calls"):
                ctx_parts.append(f'{cb["total_calls"]} appels')
            if cb.get("last_call_date"):
                dur = cb.get("last_call_dur", 0)
                ctx_parts.append(f'Dernier: {cb["last_call_date"][:10]} ({dur//60}m{dur%60:02d}s)')
            if cb.get("last_score"):
                sc = cb["last_score"]
                sc_color = "#38a169" if sc >= 6 else "#d69e2e" if sc >= 4 else "#e53e3e"
                ctx_parts.append(f'<span style="color:{sc_color}">Score: {sc}/10</span>')
            if ctx_parts:
                html += f'<div style="font-size:11px;color:#888;margin-top:2px;">{"  ·  ".join(ctx_parts)}</div>'
            if cb.get("last_summary"):
                html += f'<div style="font-size:11px;color:#667;margin-top:2px;font-style:italic;">💬 {cb["last_summary"]}</div>'
            html += f'<span style="color:#aaa;font-size:11px;">{cb["phone"]}</span>'
            html += '</div>'
    else:
        html += '<p style="color:#888;">Aucun rappel prevu pour aujourd\'hui.</p>'
    html += '</div>'

    # Section 2: Stale discussions
    if stale:
        html += '<div class="card">'
        html += f'<h3>⚠️ En discussion sans suivi ({len(stale)})</h3>'
        for s in stale[:10]:
            html += f'<div class="callback"><span class="stale">{s["name"]}</span> — {s["days_stale"]} jours sans activite'
            if s.get("last_score"):
                sc = s["last_score"]
                sc_color = "#38a169" if sc >= 6 else "#d69e2e" if sc >= 4 else "#e53e3e"
                html += f' · <span style="color:{sc_color}">Score: {sc}/10</span>'
            html += '<br>'
            if s.get("last_summary"):
                html += f'<div style="font-size:11px;color:#667;font-style:italic;">💬 {s["last_summary"]}</div>'
            html += f'<span style="color:#aaa;font-size:11px;">{s["phone"]}</span></div>'
        html += '</div>'

    # Section 3: Yesterday scores
    if scores:
        scored = [s for s in scores if s.get("ai_global_score")]
        total = len(scores)
        avg_score = sum(s.get("ai_global_score", 0) for s in scored) / len(scored) if scored else 0

        html += '<div class="card">'
        html += f'<h3>📊 Résumé d\'hier ({yesterday_str})</h3>'
        html += '<div style="text-align:center;">'
        html += f'<div class="stat"><div class="stat-num">{total}</div><div class="stat-label">Appels</div></div>'
        html += f'<div class="stat"><div class="stat-num">{len(scored)}</div><div class="stat-label">Scores</div></div>'
        score_class = "score-good" if avg_score >= 6 else "score-mid" if avg_score >= 4 else "score-bad"
        html += f'<div class="stat"><div class="stat-num {score_class}">{avg_score:.1f}/10</div><div class="stat-label">Score moy.</div></div>'
        html += '</div>'

        # All calls list with scores
        html += '<table style="width:100%;border-collapse:collapse;margin-top:10px;font-size:12px;">'
        html += '<tr style="background:#f5f5f5;"><th style="padding:5px;text-align:left;">Contact</th><th style="padding:5px;">Score</th><th style="padding:5px;">Duree</th><th style="padding:5px;text-align:left;">Coaching</th></tr>'
        for s in scored[:10]:
            sc = s.get("ai_global_score", 0)
            sc_class = "score-good" if sc >= 6 else "score-mid" if sc >= 4 else "score-bad"
            dur = s.get("duration_s", 0) or 0
            dur_str = f"{dur // 60}m{dur % 60:02d}s" if dur > 0 else "?"
            name = (s.get("contact_name") or "Inconnu")[:20]
            note = (s.get("coaching_note") or "")[:80]
            html += f'<tr style="border-bottom:1px solid #eee;">'
            html += f'<td style="padding:4px;">{name}</td>'
            html += f'<td style="padding:4px;text-align:center;" class="{sc_class}"><strong>{sc}/10</strong></td>'
            html += f'<td style="padding:4px;text-align:center;">{dur_str}</td>'
            html += f'<td style="padding:4px;font-size:11px;color:#666;font-style:italic;">{note}</td>'
            html += '</tr>'
        html += '</table>'

        # Best & worst highlights
        if len(scored) >= 2:
            best = scored[0]
            worst = scored[-1]
            html += f'<div style="margin-top:12px;font-size:13px;">'
            html += f'<div class="score-good">✅ Meilleur: {best.get("contact_name","?")} — {best.get("ai_global_score",0)}/10</div>'
            if best.get("coaching_note"):
                html += f'<div style="color:#666;margin-left:16px;font-size:11px;">{best["coaching_note"][:120]}</div>'
            html += f'<div class="score-bad" style="margin-top:6px;">⚠️ A travailler: {worst.get("contact_name","?")} — {worst.get("ai_global_score",0)}/10</div>'
            if worst.get("coaching_note"):
                html += f'<div style="color:#666;margin-left:16px;font-size:11px;">{worst["coaching_note"][:120]}</div>'
            html += '</div>'

        # Weakest dimension
        if scored:
            dim_totals = {}
            dim_counts = {}
            for s in scored:
                ai = s.get("ai_scores", {})
                if isinstance(ai, str):
                    try: ai = json.loads(ai)
                    except: ai = {}
                for dim, val in ai.items():
                    if isinstance(val, (int, float)):
                        dim_totals[dim] = dim_totals.get(dim, 0) + val
                        dim_counts[dim] = dim_counts.get(dim, 0) + 1
            if dim_totals:
                dim_avgs = {d: dim_totals[d] / dim_counts[d] for d in dim_totals}
                weakest = min(dim_avgs, key=dim_avgs.get)
                weakest_val = dim_avgs[weakest]
                html += f'<div class="tip">💡 <strong>Focus du jour:</strong> Travailler sur <strong>{weakest}</strong> (score moy: {weakest_val:.1f}/10)</div>'

        html += '</div>'

    html += """
<div style="text-align:center;margin-top:20px;color:#aaa;font-size:11px;">
    🤖 Généré automatiquement par le système coaching XGuard
</div>
</body></html>"""
    return html


def send_email(date_str, html_body):
    """Send email via Gmail SMTP directly."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    html_path = os.path.join(REPORT_DIR, "daily_email.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_body)

    day_names = {0:"Lundi",1:"Mardi",2:"Mercredi",3:"Jeudi",4:"Vendredi",5:"Samedi",6:"Dimanche"}
    day_name = day_names.get(datetime.now().weekday(), "")

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Cc"] = EMAIL_CC
    msg["Subject"] = f"Coaching Heidys {day_name} {date_str} — Rappels et Resume"
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [EMAIL_TO, EMAIL_CC], msg.as_string())
        log.info("Email sent successfully via SMTP")
    except Exception as e:
        log.error("Email sending failed: %s", e)


def main():
    log.info("=== Heidys Daily Email ===")
    today_str = datetime.now().strftime("%Y-%m-%d")
    yesterday_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # 1. Get callbacks due today
    log.info("Fetching callbacks...")
    callbacks = get_ghl_callbacks_today()
    log.info("  %d callbacks due today", len(callbacks))

    # 2. Get stale discussions
    log.info("Fetching stale discussions...")
    stale = get_stale_discussions(days=3)
    log.info("  %d stale discussions", len(stale))

    # 3. Get yesterday's scores
    log.info("Fetching yesterday's scores...")
    scores = get_yesterday_scores()
    log.info("  %d scored calls yesterday", len(scores))

    # 4. Build and send email
    html = build_email_html(callbacks, stale, scores, yesterday_str)
    log.info("Email HTML built (%d chars)", len(html))

    send_email(today_str, html)
    log.info("=== Done ===")


if __name__ == "__main__":
    main()
