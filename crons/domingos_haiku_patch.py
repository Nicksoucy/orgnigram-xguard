"""Domingos Haiku scoring + email — runs after nitro_dom_daily.py."""
import json, logging, os, smtplib, sys, time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from claude_scoring import score_domingos_call
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

import requests

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
GMAIL_USER = "nick@darkhorseads.com"
GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"
TRANSCRIPT_DIR = Path(r"C:\Users\user\xguard_transcripts\domingos")
LOG_DIR = Path(r"C:\Users\user\sac_logs")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("domingos_haiku")
fh = logging.FileHandler(str(LOG_DIR / "domingos_haiku.log"), encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(fh)

def sb_patch(call_id, data):
    url = f"{SUPABASE_URL}/rest/v1/calls?call_id=eq.{call_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}", "Content-Type": "application/json"}
    try: requests.patch(url, json=data, headers=headers, timeout=30)
    except: pass

def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    log.info("DOMINGOS HAIKU — %s", date_str)

    calls = []
    for fp in TRANSCRIPT_DIR.glob("*.json"):
        if fp.name.endswith(".tmp"): continue
        try:
            with open(fp, "r", encoding="utf-8") as f: t = json.load(f)
            ct = t.get("call_time", "")
            if ct and ct[:10] == date_str and not t.get("ai_scores"):
                t["_file"] = str(fp)
                calls.append(t)
        except: continue

    log.info("Calls to score: %d", len(calls))
    if not calls: return

    scored, results = 0, []
    for i, call in enumerate(calls):
        result = score_domingos_call(call)
        if result and result.get("ai_scores"):
            call_id = str(call.get("id", ""))
            try:
                with open(call["_file"], "r", encoding="utf-8") as f: data = json.load(f)
                data.update({"ai_scores": result["ai_scores"], "ai_global_score": result["ai_global_score"],
                            "coaching_note": result.get("coaching_note",""), "classification": result.get("classification","")})
                with open(call["_file"], "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
            except: pass
            if call_id: sb_patch(call_id, {"ai_scores": result["ai_scores"], "ai_global_score": result["ai_global_score"],
                                           "coaching_note": result.get("coaching_note","")})
            scored += 1
            results.append((call, result))
            log.info("  [%d/%d] %s: %.1f/10 [%s] — %s", i+1, len(calls), call_id,
                     result["ai_global_score"], result.get("classification","?"), (result.get("coaching_note",""))[:60])

    log.info("Scored: %d/%d", scored, len(calls))

    if scored > 0:
        avg = round(sum(r["ai_global_score"] for _,r in results) / len(results), 1)
        sc = "#2E7D32" if avg >= 6 else "#E65100" if avg >= 4 else "#C62828"
        drone = sum(1 for _,r in results if r.get("classification") == "drone")
        elite = sum(1 for _,r in results if r.get("classification") == "elite")

        rows = ""
        for call, r in sorted(results, key=lambda x: x[1]["ai_global_score"], reverse=True)[:5]:
            cls = r.get("classification","?")
            rows += f'<tr><td style="padding:5px;font-weight:bold;">{r["ai_global_score"]}/10</td><td style="padding:5px;">{cls}</td><td style="padding:5px;">{(call.get("contact_name","?"))[:20]}</td><td style="padding:5px;font-size:11px;color:#555;">{(r.get("coaching_note",""))[:80]}</td></tr>'

        html = f"""<html><body style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
<div style="background:#1B3A5C;padding:15px;border-radius:8px 8px 0 0;text-align:center;">
<h1 style="color:white;margin:0;font-size:20px;">Domingos — Ventes Drone/Elite</h1>
<p style="color:#ccc;margin:5px 0;">{date_str} | {scored} appels | Score: <span style="color:{sc};">{avg}/10</span> | Drone:{drone} Elite:{elite}</p>
</div><div style="padding:15px;border:1px solid #ddd;border-top:none;">
<table style="width:100%;font-size:12px;"><tr style="background:#f0f0f0;"><th style="padding:5px;">Score</th><th>Type</th><th>Contact</th><th>Coaching</th></tr>{rows}</table>
</div><div style="background:#f5f5f5;padding:8px;text-align:center;border-radius:0 0 8px 8px;border:1px solid #ddd;border-top:none;">
<p style="color:#999;font-size:11px;margin:0;">XGuard — Coaching IA Ventes</p></div></body></html>"""

        msg = MIMEMultipart("alternative")
        msg["From"], msg["To"] = GMAIL_USER, "nick@darkhorseads.com"
        msg["Subject"] = f"Domingos {date_str} — {scored} appels, score {avg}/10 (D:{drone} E:{elite})"
        msg.attach(MIMEText(html, "html", "utf-8"))
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
                s.login(GMAIL_USER, GMAIL_APP_PASSWORD)
                s.sendmail(GMAIL_USER, ["nick@darkhorseads.com"], msg.as_string())
            log.info("Email SENT!")
        except Exception as e: log.error("Email failed: %s", e)

if __name__ == "__main__": main()
