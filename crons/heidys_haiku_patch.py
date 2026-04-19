"""
Patch to add to nitro_heidys_daily.py — adds Haiku scoring + SMTP email after transcription.
This runs as a subprocess called at the end of the daily sync.
Usage: python heidys_haiku_patch.py [date_str]
"""

import json
import logging
import os
import smtplib
import sys
import time
from collections import defaultdict
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from claude_scoring import score_heidys_call

os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

import requests

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

GMAIL_USER = "nick@darkhorseads.com"
GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"

TRANSCRIPT_DIR = Path(r"C:\Users\user\xguard_transcripts\heidys")
LOG_DIR = Path(r"C:\Users\user\sac_logs")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("heidys_haiku")
fh = logging.FileHandler(str(LOG_DIR / "heidys_haiku.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(fh)


def sb_patch(call_id, data):
    url = f"{SUPABASE_URL}/rest/v1/calls?call_id=eq.{call_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json"}
    try:
        requests.patch(url, json=data, headers=headers, timeout=30)
    except Exception:
        pass


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")

    log.info("=" * 50)
    log.info("HEIDYS HAIKU SCORING — %s", date_str)
    log.info("=" * 50)

    # Load today's transcripts
    calls = []
    for fp in TRANSCRIPT_DIR.glob("*.json"):
        if fp.name.endswith(".tmp"):
            continue
        try:
            with open(fp, "r", encoding="utf-8") as f:
                t = json.load(f)
            # Check if it's from today
            ct = t.get("call_time", "")
            if ct and ct[:10] == date_str:
                # Skip if already scored
                if t.get("ai_scores"):
                    continue
                t["_file"] = str(fp)
                calls.append(t)
        except Exception:
            continue

    log.info("Calls to score: %d", len(calls))

    if not calls:
        log.info("Nothing to score")
        return

    # Score with Haiku
    scored = 0
    results = []
    for i, call in enumerate(calls):
        result = score_heidys_call(call)
        if result and result.get("ai_scores"):
            call_id = str(call.get("id", ""))

            # Save to file
            try:
                with open(call["_file"], "r", encoding="utf-8") as f:
                    data = json.load(f)
                data["ai_scores"] = result["ai_scores"]
                data["ai_global_score"] = result["ai_global_score"]
                data["coaching_note"] = result.get("coaching_note", "")
                with open(call["_file"], "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

            # Patch Supabase
            if call_id:
                sb_patch(call_id, {
                    "ai_scores": result["ai_scores"],
                    "ai_global_score": result["ai_global_score"],
                    "coaching_note": result.get("coaching_note", ""),
                })

            scored += 1
            log.info("  [%d/%d] %s: %.1f/10 — %s", i+1, len(calls), call_id,
                     result["ai_global_score"], (result.get("coaching_note",""))[:80])
            results.append(result)
        else:
            log.warning("  [%d/%d] FAILED", i+1, len(calls))

    log.info("Scored: %d/%d", scored, len(calls))

    # Build and send email
    if scored > 0:
        avg_score = round(sum(r["ai_global_score"] for r in results) / len(results), 1)
        sc = "#2E7D32" if avg_score >= 6 else "#E65100" if avg_score >= 4 else "#C62828"

        # Best / worst
        sorted_r = sorted(zip(calls, results), key=lambda x: x[1]["ai_global_score"], reverse=True)
        best_rows = ""
        for call, r in sorted_r[:3]:
            best_rows += f'<tr><td style="padding:5px;color:#2E7D32;font-weight:bold;">{r["ai_global_score"]}/10</td><td style="padding:5px;">{(call.get("contact_name","Inconnu"))[:25]}</td><td style="padding:5px;font-size:11px;color:#555;">{(r.get("coaching_note",""))[:100]}</td></tr>'

        worst_rows = ""
        for call, r in sorted_r[-3:]:
            worst_rows += f'<tr><td style="padding:5px;color:#C62828;font-weight:bold;">{r["ai_global_score"]}/10</td><td style="padding:5px;">{(call.get("contact_name","Inconnu"))[:25]}</td><td style="padding:5px;font-size:11px;color:#555;">{(r.get("coaching_note",""))[:100]}</td></tr>'

        html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:0 auto;">
<div style="background:#1B3A5C;padding:15px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="color:white;margin:0;font-size:20px;">Rapport Quotidien — Heidys (Ventes)</h1>
  <p style="color:#ccc;margin:5px 0 0;">{date_str} | {scored} appels scores | Score moyen: <span style="color:{sc};">{avg_score}/10</span></p>
</div>
<div style="padding:15px;border:1px solid #ddd;border-top:none;">
<h2 style="color:#2E7D32;font-size:15px;">Meilleurs appels</h2>
<table style="width:100%;font-size:12px;">{best_rows}</table>
<h2 style="color:#C62828;font-size:15px;">Appels a ameliorer</h2>
<table style="width:100%;font-size:12px;">{worst_rows}</table>
</div>
<div style="background:#f5f5f5;padding:8px;text-align:center;border-radius:0 0 8px 8px;border:1px solid #ddd;border-top:none;">
<p style="color:#999;font-size:11px;margin:0;">Academie XGuard — Coaching IA Ventes</p>
</div></body></html>"""

        # Send email
        msg = MIMEMultipart("alternative")
        msg["From"] = GMAIL_USER
        msg["To"] = "nick@darkhorseads.com"
        msg["Subject"] = f"Heidys Ventes {date_str} — {scored} appels, score {avg_score}/10"
        msg.attach(MIMEText(html, "html", "utf-8"))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                server.sendmail(GMAIL_USER, ["nick@darkhorseads.com"], msg.as_string())
            log.info("Email SENT!")
        except Exception as e:
            log.error("Email failed: %s", e)

    log.info("DONE!")


if __name__ == "__main__":
    main()
