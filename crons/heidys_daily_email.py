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
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

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
REPORT_DIR = r"C:\Users\user\heidys_reports"

CLAUDE_EXE = r"C:\Users\User\AppData\Local\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude\claude-code\2.1.63\claude.exe"
GIT_BASH = r"C:\Program Files\Git\bin\bash.exe"

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

    # Check tasks for each contact
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

            for t in tasks:
                if not isinstance(t, dict):
                    continue
                if t.get("completed") or t.get("status") == "completed":
                    continue
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
        except Exception:
            continue
        time.sleep(0.1)

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
                    stale.append({
                        "name": opp.get("name", "?"),
                        "phone": opp.get("contact", {}).get("phone", ""),
                        "days_stale": days_stale,
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
            html += f'<span style="color:#888;">{cb["phone"]}</span>'
            html += '</div>'
    else:
        html += '<p style="color:#888;">Aucun rappel prevu pour aujourd\'hui.</p>'
    html += '</div>'

    # Section 2: Stale discussions
    if stale:
        html += '<div class="card">'
        html += f'<h3>⚠️ En discussion sans suivi ({len(stale)})</h3>'
        for s in stale[:10]:
            html += f'<div class="callback"><span class="stale">{s["name"]}</span> — {s["days_stale"]} jours sans activite<br>'
            html += f'<span style="color:#888;">{s["phone"]}</span></div>'
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

        # Best & worst
        if len(scored) >= 2:
            best = scored[0]
            worst = scored[-1]
            html += f'<div style="margin-top:12px;font-size:13px;">'
            html += f'<div class="score-good">✅ Meilleur: {best.get("contact_name","?")} — {best.get("ai_global_score",0)}/10</div>'
            if best.get("coaching_note"):
                html += f'<div style="color:#666;margin-left:16px;">{best["coaching_note"]}</div>'
            html += f'<div class="score-bad" style="margin-top:6px;">⚠️ A travailler: {worst.get("contact_name","?")} — {worst.get("ai_global_score",0)}/10</div>'
            if worst.get("coaching_note"):
                html += f'<div style="color:#666;margin-left:16px;">{worst["coaching_note"]}</div>'
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
    """Send email via Claude CLI gmail_create_draft."""
    os.makedirs(REPORT_DIR, exist_ok=True)
    html_path = os.path.join(REPORT_DIR, "daily_email.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_body)

    day_names = {0:"Lundi",1:"Mardi",2:"Mercredi",3:"Jeudi",4:"Vendredi",5:"Samedi",6:"Dimanche"}
    day_name = day_names.get(datetime.now().weekday(), "")

    prompt = f"""Use the gmail_create_draft tool to create an email draft with these EXACT parameters:
To: {EMAIL_TO}
CC: {EMAIL_CC}
Subject: Coaching Heidys {day_name} {date_str} — Rappels et Resume
Content type: text/html
Body: Read the HTML content from the file at {html_path} and use it as the email body.
Create the draft now."""

    env = os.environ.copy()
    env["CLAUDE_CODE_GIT_BASH_PATH"] = GIT_BASH

    try:
        result = subprocess.run(
            [CLAUDE_EXE, "-p", "--model", "haiku", "--max-turns", "3"],
            input=prompt, capture_output=True, text=True, env=env, timeout=120,
            cwd=r"C:\Users\user",
        )
        if result.returncode == 0:
            log.info("Email draft created successfully")
        else:
            log.warning("Email draft failed: %s", result.stderr[:200])
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
