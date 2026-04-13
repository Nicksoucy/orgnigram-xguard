#!/usr/bin/env python3
"""
SAC Weekly Report v3 — AI-powered coaching with Haiku + Opus.

Monday 07:00 on Nitro. Flow:
1. Load week's transcripts
2. Score each call with Haiku (if not already scored)
3. Generate coaching report with Opus
4. Generate DOCX reports
5. Push to Supabase (metrics, actions, objections)
6. Copy DOCX to Google Drive via SCP
7. Send email via Claude CLI + Gmail MCP
"""

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from sac_scoring import (
    score_call as score_call_regex, global_score as calc_global_regex,
    classify_call, detect_agent_from_transcript, SAC_DIMENSIONS, DIM_LABELS,
    COACHING_RESPONSES, OBJECTION_CATEGORIES, detect_objections_normalized,
    generate_recommendations,
)
from claude_scoring import score_call_haiku, generate_opus_report, call_claude

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

PERSON_IDS = {"hamza": "L3", "lilia": "s2", "sekou": "s3"}
PERSON_NAMES = {"L3": "Hamza", "s2": "Lilia", "s3": "Sekou"}
TRANSCRIPT_BASE = Path(r"C:\Users\user\xguard_transcripts")
REPORT_DIR = Path(r"C:\Users\user\sac_reports")
LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOCK_FILE = Path(r"C:\Users\user\sac_weekly.lock")
DOCX_SCRIPT = Path(r"C:\Users\user\sac_analysis\generate_reports_docx.js")
DOCX_DATA_DIR = Path(r"C:\Users\user\sac_analysis")

# SCP to local PC for Google Drive sync
LOCAL_PC_IP = "100.125.184.52"
LOCAL_DRIVE_PATH = r"G:\Mon Drive\SAC Rapports Coaching"
LOCAL_SSH_KEY = None  # Will use default key if available

HAIKU_BATCH_SIZE = 20
HAIKU_PAUSE = 5  # seconds between batches

RUN_ID = str(uuid.uuid4())[:8]
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOG_DIR.mkdir(parents=True, exist_ok=True)
today_str = datetime.now().strftime("%Y-%m-%d")
log = logging.getLogger("sac_weekly_v3")
log.setLevel(logging.INFO)
_fmt = logging.Formatter(f"%(asctime)s [{RUN_ID}] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
_ch = logging.StreamHandler(); _ch.setFormatter(_fmt); log.addHandler(_ch)
_fh = logging.FileHandler(str(LOG_DIR / f"weekly_{today_str}.log"), encoding="utf-8")
_fh.setFormatter(_fmt); log.addHandler(_fh)

# ---------------------------------------------------------------------------
# Lock
# ---------------------------------------------------------------------------

def acquire_lock():
    if LOCK_FILE.exists():
        age = (datetime.now() - datetime.fromtimestamp(LOCK_FILE.stat().st_mtime)).total_seconds() / 3600
        if age > 4:
            LOCK_FILE.unlink()
        else:
            log.error("Lock exists (%.1fh) — exiting", age); sys.exit(1)
    LOCK_FILE.write_text(f"{RUN_ID}", encoding="utf-8")

def release_lock():
    LOCK_FILE.unlink(missing_ok=True)

# ---------------------------------------------------------------------------
# Supabase
# ---------------------------------------------------------------------------

def sb_upsert(table, data, on_conflict=""):
    oc = f"?on_conflict={on_conflict}" if on_conflict else ""
    url = f"{SUPABASE_URL}/rest/v1/{table}{oc}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}
    try:
        resp = requests.post(url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            log.warning("Supabase %s (%d): %s", table, resp.status_code, resp.text[:150])
        return resp
    except Exception as e:
        log.warning("Supabase %s error: %s", table, e)

def sb_patch(call_id, data):
    """PATCH existing sac_calls row by call_id."""
    url = f"{SUPABASE_URL}/rest/v1/sac_calls?call_id=eq.{call_id}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json"}
    try:
        resp = requests.patch(url, json=data, headers=headers, timeout=30)
        if resp.status_code >= 400:
            log.warning("Supabase PATCH sac_calls (%d): %s", resp.status_code, resp.text[:150])
    except Exception as e:
        log.warning("Supabase PATCH error: %s", e)

def sb_insert(table, data):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}",
               "Content-Type": "application/json", "Prefer": "return=minimal"}
    try:
        return requests.post(url, json=data, headers=headers, timeout=30)
    except Exception as e:
        log.warning("Supabase insert %s: %s", table, e)

def sb_get(table, params):
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        return requests.get(url, params=params, headers=headers, timeout=30)
    except Exception as e:
        log.warning("Supabase get %s: %s", table, e)

# ---------------------------------------------------------------------------
# First-name detection
# ---------------------------------------------------------------------------

AGENT_NAMES = {
    "lilia": re.compile(r"\b(lilia|lilya|lilea)\b", re.I),
    "hamza": re.compile(r"\b(hamza|hamzah)\b", re.I),
    "sekou": re.compile(r"\b(sekou|sékou|secou|sécou|sécoudé|secoudé|sékou de|secou de|sekou de)\b", re.I),
}

def detect_agent(text):
    intro = " ".join(text.split()[:150]).lower()
    for agent, pat in AGENT_NAMES.items():
        if pat.search(intro):
            return agent
    return None

# ---------------------------------------------------------------------------
# Load transcripts
# ---------------------------------------------------------------------------

def get_week_range():
    today = datetime.now()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return last_monday.replace(hour=0, minute=0, second=0, microsecond=0), last_sunday

def load_transcripts(week_start, week_end):
    buckets = {"hamza": [], "lilia": [], "sekou": []}
    total = 0

    for person in ["hamza", "lilia", "sekou"]:
        tdir = TRANSCRIPT_BASE / person
        if not tdir.exists(): continue
        for fp in tdir.glob("*.json"):
            if fp.name.endswith(".tmp"): continue
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    t = json.load(f)
            except Exception:
                continue

            ct_str = t.get("call_time", "")
            ct = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                        "%Y-%m-%d %H:%M:%S.%f"):
                try:
                    ct = datetime.strptime(ct_str, fmt); break
                except ValueError:
                    continue
            if ct is None: continue
            if not (week_start <= ct <= week_end): continue

            total += 1
            detected = detect_agent(t.get("transcript", ""))
            notes = (t.get("notes", "") or "").lower()
            if detected: assigned = detected
            elif "lilia" in notes: assigned = "lilia"
            elif "hamza" in notes: assigned = "hamza"
            elif "sekou" in notes or notes.strip() == "sk": assigned = "sekou"
            else: assigned = person

            t["_assigned"] = assigned
            t["_file"] = str(fp)
            buckets[assigned].append(t)

    log.info("Loaded %d transcripts for the week", total)
    return buckets

# ---------------------------------------------------------------------------
# Phase 1: Haiku scoring
# ---------------------------------------------------------------------------

def score_with_haiku(buckets):
    """Score all calls with Haiku. Updates transcripts in-place."""
    total = sum(len(v) for v in buckets.values())
    log.info("Phase 1: Haiku scoring %d calls...", total)

    scored = 0
    failed = 0

    for person, calls in buckets.items():
        for i in range(0, len(calls), HAIKU_BATCH_SIZE):
            batch = calls[i:i + HAIKU_BATCH_SIZE]
            for j, call in enumerate(batch):
                result = score_call_haiku(call)
                if result and result.get("ai_scores"):
                    call["_ai_scores"] = result["ai_scores"]
                    call["_ai_global"] = result["ai_global_score"]
                    call["_coaching_note"] = result.get("coaching_note", "")
                    scored += 1

                    # Also push to Supabase via PATCH (existing rows)
                    call_id = str(call.get("id", ""))
                    if call_id:
                        sb_patch(call_id, {
                            "ai_scores": result["ai_scores"],
                            "ai_global_score": result["ai_global_score"],
                            "coaching_note": result.get("coaching_note", ""),
                        })
                else:
                    # Fallback to regex
                    text = call.get("transcript", "")
                    dur = call.get("duration_s", 0)
                    regex = score_call_regex(text, dur)
                    call["_ai_scores"] = regex
                    call["_ai_global"] = calc_global_regex(regex)
                    call["_coaching_note"] = ""
                    failed += 1

                if (scored + failed) % 20 == 0:
                    log.info("  Haiku: %d/%d scored, %d failed", scored, total, failed)

            if i + HAIKU_BATCH_SIZE < len(calls):
                time.sleep(HAIKU_PAUSE)

    log.info("Haiku done: %d scored, %d fallback to regex", scored, failed)

# ---------------------------------------------------------------------------
# Phase 2: Opus report
# ---------------------------------------------------------------------------

def prepare_opus_data(buckets, week_start, sms_data=None):
    """Prepare data for Opus: per-agent summaries + best/worst transcripts + SMS."""
    data = {"week_start": week_start.strftime("%Y-%m-%d"), "agents": {}}

    for person in ["hamza", "lilia", "sekou"]:
        calls = buckets[person]
        if not calls:
            continue

        pid = PERSON_IDS[person]
        name = person.capitalize()

        # Average AI scores
        avg = {}
        for d in SAC_DIMENSIONS:
            vals = [c.get("_ai_scores", {}).get(d, 0) for c in calls]
            avg[d] = round(sum(vals) / len(vals), 1) if vals else 0

        global_avg = round(sum(avg.values()) / len(SAC_DIMENSIONS), 1)

        # Sort by global score
        sorted_calls = sorted(calls, key=lambda c: c.get("_ai_global", 0), reverse=True)

        # Best 5 with transcripts
        best = []
        for c in sorted_calls[:5]:
            best.append({
                "score": c.get("_ai_global", 0),
                "contact": c.get("contact_name", ""),
                "duration_s": c.get("duration_s", 0),
                "coaching_note": c.get("_coaching_note", ""),
                "transcript_excerpt": (c.get("transcript", "") or "")[:500],
            })

        # Worst 5
        worst = []
        for c in sorted_calls[-5:]:
            worst.append({
                "score": c.get("_ai_global", 0),
                "contact": c.get("contact_name", ""),
                "duration_s": c.get("duration_s", 0),
                "coaching_note": c.get("_coaching_note", ""),
                "transcript_excerpt": (c.get("transcript", "") or "")[:500],
            })

        # Categories
        cats = defaultdict(int)
        for c in calls:
            cats[classify_call(c.get("transcript", ""))] += 1

        # Objections
        obj_counts = defaultdict(int)
        for c in calls:
            for cat, raw in detect_objections_normalized(c.get("transcript", "")):
                obj_counts[cat] += 1

        data["agents"][name] = {
            "person_id": pid,
            "total_calls": len(calls),
            "avg_scores": avg,
            "global_score": global_avg,
            "best_calls": best,
            "worst_calls": worst,
            "categories": dict(cats),
            "objections": dict(obj_counts),
            "avg_duration_min": round(sum(c.get("duration_s", 0) for c in calls) / len(calls) / 60, 1),
        }

    # Add SMS data if available
    if sms_data and sms_data.get("total", 0) > 0:
        data["sms"] = {
            "total": sms_data["total"],
            "inbound": sms_data["inbound"],
            "outbound": sms_data["outbound"],
            "unanswered": sms_data["unanswered_total"],
            "hot_leads": sms_data["hot_leads_total"],
            "avg_response_min": sms_data.get("avg_response_min"),
            "intent_breakdown": sms_data.get("intent_totals", {}),
            "top_unanswered": [{"name": u["name"], "message": u["last_message"][:100], "intents": u["intents"]}
                               for u in sms_data.get("all_unanswered", [])[:10]],
            "top_hot_leads": [{"name": h["name"], "message": h["body"][:100], "time": h.get("time", "")}
                              for h in sms_data.get("all_hot_leads", [])[:10]],
            "by_day": sms_data.get("by_day", {}),
        }

    return data

def run_opus(buckets, week_start, sms_data=None):
    """Generate Opus coaching report."""
    log.info("Phase 2: Opus report generation...")
    data = prepare_opus_data(buckets, week_start, sms_data=sms_data)
    report_text = generate_opus_report(data)

    # Save report text
    report_path = REPORT_DIR / "opus_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    log.info("Opus report saved: %s (%d chars)", report_path, len(report_text))
    return report_text

# ---------------------------------------------------------------------------
# Phase 3: Reports + DOCX
# ---------------------------------------------------------------------------

def generate_reports(buckets, week_start, week_end, opus_text):
    """Generate report JSONs and DOCX files."""
    log.info("Phase 3: Generating reports...")

    week_start_str = week_start.strftime("%Y-%m-%d")

    for person in ["hamza", "lilia", "sekou"]:
        calls = buckets[person]
        pid = PERSON_IDS[person]
        name = person.capitalize()

        if not calls:
            continue

        # Average AI scores
        avg = {}
        for d in SAC_DIMENSIONS:
            vals = [c.get("_ai_scores", {}).get(d, 0) for c in calls]
            avg[d] = round(sum(vals) / len(vals), 1) if vals else 0

        gl = round(sum(avg.values()) / len(SAC_DIMENSIONS), 1)
        durs = [c.get("duration_s", 0) for c in calls]
        avg_dur = round(sum(durs) / len(durs)) if durs else 0

        # Sorted dims
        sd = sorted(avg.items(), key=lambda x: -x[1])
        strengths = [f"{DIM_LABELS.get(d, d)}: {s}/10" for d, s in sd[:3] if s >= 4.0]
        improvements = [f"{DIM_LABELS.get(d, d)}: {s}/10" for d, s in sd[-3:] if s < 7.0]

        # Coaching examples (from AI scores)
        sorted_calls = sorted(calls, key=lambda c: c.get("_ai_global", 0), reverse=True)
        examples = {}
        for dim in SAC_DIMENSIONS:
            by_dim = sorted(calls, key=lambda c: c.get("_ai_scores", {}).get(dim, 0))
            worst = by_dim[:3]
            best = by_dim[-3:][::-1]
            de = {"best": [], "worst": []}
            for item in best:
                text = item.get("transcript", "")
                words = text.split()
                excerpt = " ".join(words[:100]) + ("..." if len(words) > 100 else "")
                de["best"].append({
                    "score": item.get("_ai_scores", {}).get(dim, 0),
                    "contact": item.get("contact_name", ""),
                    "duration": item.get("duration_s", 0),
                    "date": item.get("call_time", ""),
                    "excerpt": excerpt,
                    "coaching_note": item.get("_coaching_note", ""),
                })
            for item in worst:
                text = item.get("transcript", "")
                words = text.split()
                excerpt = " ".join(words[:100]) + ("..." if len(words) > 100 else "")
                de["worst"].append({
                    "score": item.get("_ai_scores", {}).get(dim, 0),
                    "contact": item.get("contact_name", ""),
                    "duration": item.get("duration_s", 0),
                    "date": item.get("call_time", ""),
                    "excerpt": excerpt,
                    "coaching_note": item.get("_coaching_note", ""),
                })
            examples[dim] = de

        # Categories
        cats = defaultdict(int)
        for c in calls:
            cats[classify_call(c.get("transcript", ""))] += 1

        # Build report
        report = {
            "person_id": pid, "person_name": name,
            "week_start": week_start_str, "report_type": "sac",
            "calls_analyzed": len(calls), "scores": avg, "global_score": gl,
            "strengths": strengths, "improvements": improvements,
            "recommendations": [r["recommendation"] for r in generate_recommendations(avg)],
            "top_objections": [],
            "call_breakdown": dict(cats),
            "duration_stats": {
                "avg_sec": avg_dur, "avg_min": round(avg_dur / 60, 1),
                "median_sec": sorted(durs)[len(durs) // 2] if durs else 0,
                "median_min": round(sorted(durs)[len(durs) // 2] / 60, 1) if durs else 0,
                "max_sec": max(durs) if durs else 0,
                "max_min": round(max(durs) / 60, 1) if durs else 0,
                "min_sec": min(durs) if durs else 0,
            },
            "call_stats": {},
            "coaching_examples": examples,
            "opus_coaching": opus_text,  # Full Opus narrative
            "raw_summary": f"{len(calls)} appels analyses par IA. Score global: {gl}/10.",
        }

        # Save report JSON
        json_path = DOCX_DATA_DIR / person / "report_v2.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        log.info("  %s report saved: %s", name, json_path)

        # Push to Supabase
        sb_upsert("coaching_reports", {
            "person_id": pid, "week_start": week_start_str,
            "week_end": week_end.strftime("%Y-%m-%d"),
            "report_type": "sac", "calls_analyzed": len(calls),
            "scores": avg, "global_score": gl,
            "strengths": strengths, "improvements": improvements,
            "recommendations": report["recommendations"],
            "call_breakdown": dict(cats),
            "raw_summary": report["raw_summary"],
        }, on_conflict="person_id,week_start")

        # Push weekly metrics
        sb_upsert("sac_coaching_metrics", {
            "person_id": pid, "period_type": "week",
            "period_start": week_start_str,
            "period_end": week_end.strftime("%Y-%m-%d"),
            "calls_analyzed": len(calls), "avg_duration_s": avg_dur,
            "scores": avg, "global_score": gl,
            "call_breakdown": dict(cats),
        }, on_conflict="person_id,period_type,period_start")

    # Generate DOCX
    log.info("Generating DOCX reports...")
    try:
        result = subprocess.run(["node", str(DOCX_SCRIPT)],
                               capture_output=True, text=True, timeout=120,
                               cwd=str(DOCX_DATA_DIR))
        if result.returncode == 0:
            log.info("DOCX generated successfully")
            # Move to reports dir
            for person in ["hamza", "lilia", "sekou"]:
                name = person.capitalize()
                src = DOCX_DATA_DIR / f"Rapport_Coaching_{name}_SAC.docx"
                if src.exists():
                    dest_dir = REPORT_DIR / person
                    dest_dir.mkdir(parents=True, exist_ok=True)
                    dest = dest_dir / f"rapport_semaine_{week_start_str}.docx"
                    shutil.copy2(str(src), str(dest))
        else:
            log.error("DOCX failed: %s", result.stderr[:200])
    except Exception as e:
        log.error("DOCX error: %s", e)

# ---------------------------------------------------------------------------
# Phase 4: Email via Claude CLI
# ---------------------------------------------------------------------------

def send_email(opus_text, week_start_str, buckets, sms_data=None):
    """Send weekly report email via SMTP."""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    log.info("Phase 4: Sending email via SMTP...")

    GMAIL_USER = "nick@darkhorseads.com"
    GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"

    # Build summary
    summary_parts = []
    for person in ["hamza", "lilia", "sekou"]:
        calls = buckets[person]
        if not calls:
            continue
        avg_global = round(sum(c.get("_ai_global", 0) for c in calls) / len(calls), 1)
        summary_parts.append(f"{person.capitalize()}: {avg_global}/10 ({len(calls)} appels)")
    summary = " | ".join(summary_parts)

    # SMS summary
    sms_summary = ""
    if sms_data and sms_data.get("total", 0) > 0:
        sms_summary = f"""
        <tr><td style="padding:5px;font-weight:bold;">SMS</td><td style="padding:5px;">{sms_data['total']} total ({sms_data['inbound']} entrants)</td></tr>
        <tr><td style="padding:5px;font-weight:bold;">SMS non-repondus</td><td style="padding:5px;color:#C62828;">{sms_data['unanswered_total']}</td></tr>
        <tr><td style="padding:5px;font-weight:bold;">Leads chauds SMS</td><td style="padding:5px;color:#C62828;">{sms_data['hot_leads_total']}</td></tr>
        """

    # Convert opus text (markdown) to basic HTML
    import re as _re
    def _md_to_html(text):
        lines = text.split("\n")
        html_lines = []
        for line in lines:
            stripped = line.strip()
            # Headings (## before # to avoid premature match)
            if stripped.startswith("### "):
                html_lines.append(f'<h4 style="color:#1B3A5C;margin:15px 0 5px;font-size:13px;">{stripped[4:]}</h4>')
            elif stripped.startswith("## "):
                html_lines.append(f'<h3 style="color:#1B3A5C;margin:18px 0 8px;font-size:14px;">{stripped[3:]}</h3>')
            elif stripped.startswith("# "):
                html_lines.append(f'<h2 style="color:#1B3A5C;margin:20px 0 10px;font-size:16px;border-bottom:1px solid #ddd;padding-bottom:5px;">{stripped[2:]}</h2>')
            elif stripped.startswith("> "):
                html_lines.append(f'<blockquote style="border-left:3px solid #1B3A5C;padding:5px 10px;margin:8px 0;color:#555;font-style:italic;font-size:12px;">{stripped[2:]}</blockquote>')
            elif stripped.startswith("- ") or stripped.startswith("* "):
                html_lines.append(f'<div style="padding-left:15px;margin:2px 0;">&#8226; {stripped[2:]}</div>')
            elif stripped == "":
                html_lines.append("<br>")
            else:
                html_lines.append(f'<p style="margin:4px 0;">{stripped}</p>')
        result = "\n".join(html_lines)
        # Bold: **text** -> <strong>text</strong>
        result = _re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', result)
        # Italic: *text* -> <em>text</em>
        result = _re.sub(r'\*(.+?)\*', r'<em>\1</em>', result)
        return result
    opus_html = _md_to_html(opus_text)

    html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:750px;margin:0 auto;">
<div style="background:#1B3A5C;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="color:white;margin:0;font-size:22px;">Rapport Coaching SAC — Hebdomadaire</h1>
  <p style="color:#ccc;margin:5px 0 0;">Semaine du {week_start_str}</p>
</div>
<div style="padding:20px;border:1px solid #ddd;border-top:none;">
  <h2 style="color:#1B3A5C;">Scores</h2>
  <p style="font-size:16px;font-weight:bold;">{summary}</p>
  <table style="font-size:13px;margin:10px 0;">
    {sms_summary}
  </table>
  <p><a href="https://drive.google.com/drive/folders/18AYzF7-FrWx8wfXC_wM3CGl1uM_t_Xx6"
     style="display:inline-block;background:#1B3A5C;color:white;padding:12px 24px;border-radius:5px;text-decoration:none;font-weight:bold;">
     Ouvrir les rapports dans Google Drive</a></p>
  <hr style="border:1px solid #eee;margin:20px 0;">
  <div style="font-size:13px;line-height:1.6;">{opus_html}</div>
</div>
<div style="background:#f5f5f5;padding:10px;border-radius:0 0 8px 8px;text-align:center;border:1px solid #ddd;border-top:none;">
  <p style="color:#999;font-size:11px;margin:0;">Academie XGuard — Coaching IA automatise</p>
</div></body></html>"""

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = "hmaghraoui65@gmail.com"
    msg["Cc"] = "nick@darkhorseads.com"
    msg["Subject"] = f"Rapport Coaching SAC — Semaine du {week_start_str}"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, ["hmaghraoui65@gmail.com", "nick@darkhorseads.com"], msg.as_string())
        log.info("Weekly email SENT!")
    except Exception as e:
        log.error("Weekly email failed: %s", e)

    # Also save opus report for reference
    log.info("Phase 4 done")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    start_time = time.time()
    log.info("=" * 60)
    log.info("SAC Weekly Report v3 (AI-powered) — %s", today_str)
    log.info("Run ID: %s", RUN_ID)
    log.info("=" * 60)

    acquire_lock()

    try:
        week_start, week_end = get_week_range()
        week_start_str = week_start.strftime("%Y-%m-%d")
        log.info("Week: %s to %s", week_start_str, week_end.strftime("%Y-%m-%d"))

        # Load transcripts
        buckets = load_transcripts(week_start, week_end)
        total = sum(len(v) for v in buckets.values())
        if total == 0:
            log.info("No transcripts for this week. Exiting.")
            return

        for person in ["hamza", "lilia", "sekou"]:
            log.info("  %s: %d calls", person, len(buckets[person]))

        # Phase 0.5: SMS weekly stats
        log.info("")
        log.info("--- Fetching SMS for the week ---")
        from sms_stats import fetch_sms_for_date, analyze_sms
        weekly_sms = {"total": 0, "inbound": 0, "outbound": 0,
                      "unanswered_total": 0, "hot_leads_total": 0,
                      "by_day": {}, "all_unanswered": [], "all_hot_leads": [],
                      "intent_totals": {}, "response_times": []}
        from datetime import timedelta as _td
        current_day = week_start
        while current_day <= week_end:
            ds = current_day.strftime("%Y-%m-%d")
            try:
                day_sms = fetch_sms_for_date(ds)
                if day_sms:
                    day_stats = analyze_sms(day_sms, ds)
                    weekly_sms["total"] += day_stats["total"]
                    weekly_sms["inbound"] += day_stats["inbound"]
                    weekly_sms["outbound"] += day_stats["outbound"]
                    weekly_sms["unanswered_total"] += day_stats["unanswered_count"]
                    weekly_sms["hot_leads_total"] += day_stats["hot_leads_count"]
                    weekly_sms["all_unanswered"].extend(day_stats["unanswered"])
                    weekly_sms["all_hot_leads"].extend(day_stats["hot_leads"])
                    if day_stats.get("avg_response_min"):
                        weekly_sms["response_times"].append(day_stats["avg_response_min"])
                    for intent, count in day_stats.get("intent_breakdown", {}).items():
                        weekly_sms["intent_totals"][intent] = weekly_sms["intent_totals"].get(intent, 0) + count
                    weekly_sms["by_day"][ds] = {
                        "total": day_stats["total"], "in": day_stats["inbound"],
                        "out": day_stats["outbound"], "unanswered": day_stats["unanswered_count"],
                        "hot": day_stats["hot_leads_count"],
                    }
                    log.info("  %s: %d SMS (%d in, %d out) | %d unanswered | %d hot",
                             ds, day_stats["total"], day_stats["inbound"], day_stats["outbound"],
                             day_stats["unanswered_count"], day_stats["hot_leads_count"])
            except Exception as e:
                log.warning("  %s SMS fetch failed: %s", ds, e)
            current_day += _td(days=1)
            time.sleep(0.5)

        avg_resp = round(sum(weekly_sms["response_times"]) / len(weekly_sms["response_times"])) if weekly_sms["response_times"] else None
        weekly_sms["avg_response_min"] = avg_resp
        log.info("  WEEK TOTAL: %d SMS (%d in, %d out) | %d unanswered | %d hot leads | resp: %s min",
                 weekly_sms["total"], weekly_sms["inbound"], weekly_sms["outbound"],
                 weekly_sms["unanswered_total"], weekly_sms["hot_leads_total"],
                 avg_resp or "N/A")

        # Phase 1: Haiku scoring
        score_with_haiku(buckets)

        # Phase 2: Opus report (now with SMS data)
        opus_text = run_opus(buckets, week_start, sms_data=weekly_sms)

        # Phase 3: Reports + DOCX
        generate_reports(buckets, week_start, week_end, opus_text)

        # Phase 4: Email (with SMS data)
        send_email(opus_text, week_start_str, buckets, sms_data=weekly_sms)

        # Cron log
        elapsed = round(time.time() - start_time)
        for person in ["hamza", "lilia", "sekou"]:
            sb_insert("cron_logs", {
                "person_id": PERSON_IDS[person],
                "cron_type": "weekly_report_v3",
                "status": "success",
                "calls_processed": len(buckets[person]),
                "duration_sec": elapsed,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "finished_at": datetime.now(timezone.utc).isoformat(),
            })

        log.info("")
        log.info("=" * 60)
        log.info("ALL DONE in %d seconds (%.1f min)", elapsed, elapsed / 60)
        log.info("=" * 60)

    except Exception as e:
        log.exception("FATAL: %s", e)
    finally:
        release_lock()


if __name__ == "__main__":
    main()
