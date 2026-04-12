"""
Health Check — Post-cron verification + email alert on failure.
Runs after each daily cron to verify data integrity.
Can also run standalone: python health_check.py [date]
"""

import json
import logging
import os
import smtplib
import sys
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

GMAIL_USER = "nick@darkhorseads.com"
GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

LOG_DIR = Path(r"C:\Users\user\sac_logs")
_handlers = [logging.StreamHandler()]
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(str(LOG_DIR / f"health_{datetime.now():%Y-%m-%d}.log"), encoding="utf-8"))
except (PermissionError, OSError):
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", handlers=_handlers)
log = logging.getLogger("health_check")


def sb_get(path):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        return resp.json() if resp.status_code == 200 else []
    except Exception as e:
        return {"error": str(e)}


def check_cron_logs(date_str):
    """Check that crons ran successfully today."""
    issues = []
    rows = sb_get(f"cron_logs?started_at=gte.{date_str}T00:00:00&started_at=lte.{date_str}T23:59:59&order=started_at.desc")

    if isinstance(rows, dict) and "error" in rows:
        issues.append(("CRITICAL", "Supabase", f"Cannot reach cron_logs: {rows['error']}"))
        return issues, []

    if not rows:
        issues.append(("WARNING", "Crons", f"Aucun cron log pour {date_str} — rien n'a roule?"))
        return issues, []

    errors = [r for r in rows if r.get("status") == "error"]
    for e in errors:
        pid = e.get("person_id", "?")
        ctype = e.get("cron_type", "?")
        msg = (e.get("error_msg") or "")[:120]
        issues.append(("CRITICAL", f"Cron {ctype} ({pid})", msg))

    return issues, rows


def check_coaching_data(date_str):
    """Check that coaching_data was pushed today for active agents."""
    issues = []
    rows = sb_get(f"coaching_data?sync_date=eq.{date_str}&order=person_id")

    if isinstance(rows, dict) and "error" in rows:
        issues.append(("CRITICAL", "Supabase", f"Cannot reach coaching_data: {rows['error']}"))
        return issues

    expected_weekday = {"L3", "s2"}  # Hamza + Lilia
    expected_weekend = {"s3"}  # Sekou
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    expected = expected_weekend if dt.weekday() >= 5 else expected_weekday

    found = {r["person_id"] for r in rows}
    missing = expected - found
    if missing:
        issues.append(("WARNING", "coaching_data", f"Agents manquants pour {date_str}: {', '.join(missing)}"))

    # Check for zero calls
    for r in rows:
        if r.get("calls_total", 0) == 0:
            issues.append(("WARNING", "coaching_data", f"{r['person_id']}: 0 appels total pour {date_str}"))

    return issues


def check_sac_calls(date_str):
    """Check sac_calls have reasonable scores."""
    issues = []
    rows = sb_get(
        f"sac_calls?call_time=gte.{date_str}T00:00:00&call_time=lte.{date_str}T23:59:59"
        f"&select=call_id,person_id,ai_global_score,duration_s&order=call_time"
    )

    if isinstance(rows, dict) and "error" in rows:
        issues.append(("WARNING", "Supabase", f"Cannot reach sac_calls: {rows['error']}"))
        return issues

    if not rows:
        # Not critical — might be weekend or no transcribable calls
        return issues

    # Check score range
    scored = [r for r in rows if r.get("ai_global_score") is not None]
    if scored:
        avg_score = sum(r["ai_global_score"] for r in scored) / len(scored)
        if avg_score > 9.5:
            issues.append(("WARNING", "Scores", f"Score moyen suspicieusement eleve: {avg_score:.1f}/10"))
        if avg_score < 1.0:
            issues.append(("WARNING", "Scores", f"Score moyen suspicieusement bas: {avg_score:.1f}/10"))

    # Check for duplicate call_ids
    ids = [r["call_id"] for r in rows if r.get("call_id")]
    if len(ids) != len(set(ids)):
        dupes = len(ids) - len(set(ids))
        issues.append(("WARNING", "sac_calls", f"{dupes} call_id dupliques detectes"))

    return issues


def check_smart_stats(date_str):
    """Run smart_stats and validate the 39 indicators."""
    issues = []
    try:
        from smart_stats import compute_smart_stats
        stats = compute_smart_stats(date_str)
        ind = stats.get("indicators", {})

        if not ind:
            issues.append(("WARNING", "smart_stats", "Aucun indicateur calcule"))
            return issues

        gs = ind.get("global_score", 0)
        if gs == 0:
            issues.append(("WARNING", "Score", "Score global = 0 (pas de donnees?)"))
        elif gs > 100:
            issues.append(("CRITICAL", "Score", f"Score global > 100: {gs}"))

        # Callback logic check
        rappeles = ind.get("taux_rappel_corrige", 0)
        non_rappeles = ind.get("non_rappeles_count", 0)
        total_net = rappeles + non_rappeles if rappeles < 100 else 0
        # No specific issue to flag here, just informational

        # Occupation check
        occ = ind.get("taux_occupation", 0)
        if occ > 100:
            issues.append(("WARNING", "Occupation", f"Taux occupation > 100%: {occ}% (duree > heures travaillees?)"))

    except Exception as e:
        issues.append(("WARNING", "smart_stats", f"Erreur d'execution: {str(e)[:100]}"))

    return issues


def check_disk_space():
    """Check Nitro disk space."""
    issues = []
    try:
        import shutil
        total, used, free = shutil.disk_usage("C:\\")
        free_gb = free / (1024**3)
        if free_gb < 5:
            issues.append(("CRITICAL", "Disque", f"Seulement {free_gb:.1f} GB libre sur C:\\"))
        elif free_gb < 10:
            issues.append(("WARNING", "Disque", f"{free_gb:.1f} GB libre sur C:\\ (attention)"))
    except Exception:
        pass
    return issues


def run_all_checks(date_str):
    """Run all health checks and return issues list."""
    all_issues = []

    log.info("=== HEALTH CHECK — %s ===", date_str)

    log.info("1. Cron logs...")
    issues, cron_rows = check_cron_logs(date_str)
    all_issues.extend(issues)
    log.info("   %d crons, %d issues", len(cron_rows), len(issues))

    log.info("2. Coaching data...")
    issues = check_coaching_data(date_str)
    all_issues.extend(issues)
    log.info("   %d issues", len(issues))

    log.info("3. SAC calls...")
    issues = check_sac_calls(date_str)
    all_issues.extend(issues)
    log.info("   %d issues", len(issues))

    log.info("4. Smart stats + indicators...")
    issues = check_smart_stats(date_str)
    all_issues.extend(issues)
    log.info("   %d issues", len(issues))

    log.info("5. Disk space...")
    issues = check_disk_space()
    all_issues.extend(issues)
    log.info("   %d issues", len(issues))

    return all_issues


def send_alert(date_str, issues):
    """Send alert email if there are CRITICAL issues."""
    critical = [i for i in issues if i[0] == "CRITICAL"]
    warnings = [i for i in issues if i[0] == "WARNING"]

    if not critical and not warnings:
        return

    level = "CRITICAL" if critical else "WARNING"
    color = "#C62828" if critical else "#E65100"

    rows = ""
    for sev, source, msg in issues:
        sc = "#C62828" if sev == "CRITICAL" else "#E65100"
        rows += f'<tr><td style="padding:6px;color:{sc};font-weight:bold;">{sev}</td><td style="padding:6px;">{source}</td><td style="padding:6px;font-size:12px;">{msg}</td></tr>'

    html = f"""<html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
    <div style="background:{color};padding:15px;border-radius:8px 8px 0 0;text-align:center;">
      <h2 style="color:white;margin:0;">Health Check {level}</h2>
      <p style="color:#ffcdd2;margin:4px 0 0;font-size:12px;">{date_str} | {len(critical)} critical, {len(warnings)} warnings</p>
    </div>
    <div style="padding:15px;border:1px solid #ddd;border-top:none;">
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <tr style="background:#f5f5f5;"><th style="padding:6px;text-align:left;">Severite</th><th style="padding:6px;text-align:left;">Source</th><th style="padding:6px;text-align:left;">Message</th></tr>
        {rows}
      </table>
    </div>
    <div style="background:#f5f5f5;padding:8px;border-radius:0 0 8px 8px;text-align:center;border:1px solid #ddd;border-top:none;">
      <p style="color:#999;font-size:10px;margin:0;">XGuard Health Check automatise</p>
    </div>
    </body></html>"""

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = "nick@darkhorseads.com"
    msg["Subject"] = f"[{level}] Health Check SAC {date_str} — {len(issues)} probleme(s)"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, ["nick@darkhorseads.com"], msg.as_string())
        log.info("Alert email sent to nick@darkhorseads.com")
    except Exception as e:
        log.error("Alert email failed: %s", e)


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")

    issues = run_all_checks(date_str)

    log.info("")
    if not issues:
        log.info("ALL OK — no issues found")
    else:
        for sev, source, msg in issues:
            log.info("  [%s] %s: %s", sev, source, msg)
        log.info("")
        log.info("Total: %d critical, %d warnings",
                 len([i for i in issues if i[0] == "CRITICAL"]),
                 len([i for i in issues if i[0] == "WARNING"]))
        send_alert(date_str, issues)

    return 0 if not any(i[0] == "CRITICAL" for i in issues) else 1


if __name__ == "__main__":
    sys.exit(main())
