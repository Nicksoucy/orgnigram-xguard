"""
Daily SAC Email Report v3 — Uses smart_stats for real metrics.
All stats filtered to work hours (8h-18h), deduped, agent-busy excluded.
"""

import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
from smart_stats import compute_smart_stats
from sms_stats import fetch_sms_for_date, analyze_sms, sms_html_section
from email_stats import fetch_email_stats, email_html_section
from conversion_metrics import get_conversion_stats, conversion_html_section
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GMAIL_USER = "nick@darkhorseads.com"
GMAIL_APP_PASSWORD = "kjaqmxuewwzkxcif"

os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

SUPABASE_URL = "https://ctjsdpfegpsfpwjgusyi.supabase.co"
SUPABASE_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwi"
    "cm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0."
    "Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo"
)

PERSON_NAMES = {"L3": "Hamza", "s2": "Lilia", "s3": "Sekou"}
DAYS_FR = {0: "Lundi", 1: "Mardi", 2: "Mercredi", 3: "Jeudi", 4: "Vendredi", 5: "Samedi", 6: "Dimanche"}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("daily_email")


def sb_get(path):
    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
        return resp.json() if resp.status_code == 200 else []
    except Exception:
        return []


def get_transcribed_calls(date_str):
    return sb_get(
        f"sac_calls?call_time=gte.{date_str}T00:00:00&call_time=lte.{date_str}T23:59:59"
        f"&select=call_id,person_id,call_time,duration_s,direction,classification,ai_global_score,coaching_note,contact_name"
        f"&order=call_time"
    )


def score_html_section(indicators):
    """Build the 7-dimension score card + non-rappeles list HTML."""
    if not indicators:
        return ""

    global_score = indicators.get("global_score", 0)
    dims = indicators.get("dimensions", {})

    # Score color
    if global_score >= 75:
        score_color = "#2E7D32"
        score_bg = "#E8F5E9"
    elif global_score >= 50:
        score_color = "#E65100"
        score_bg = "#FFF3E0"
    else:
        score_color = "#C62828"
        score_bg = "#FFEBEE"

    # Dimension rows
    DIM_LABELS = [
        ("reponse_disponibilite", "Reponse & Disponibilite", "25%"),
        ("taux_rappel", "Taux de Rappel", "25%"),
        ("qualite_traitement", "Qualite de Traitement", "20%"),
        ("file_attente_saturation", "File d'Attente", "8%"),
        ("conformite_tracabilite", "Conformite", "10%"),
        ("efficacite_charge", "Efficacite & Charge", "12%"),
    ]

    dim_rows = ""
    for dim_key, label, pct in DIM_LABELS:
        v = dims.get(dim_key)
        if v is None:
            dim_rows += f"""
            <tr>
              <td style="padding:6px 8px;font-size:12px;">{label}</td>
              <td style="padding:6px;text-align:center;color:#999;">N/A</td>
              <td style="padding:6px;"><div style="background:#eee;height:14px;border-radius:7px;overflow:hidden;"></div></td>
              <td style="padding:6px;text-align:center;font-size:11px;color:#999;">x{pct}</td>
            </tr>"""
            continue

        bar_pct = min(100, max(0, v * 10))
        if v >= 7:
            bar_color = "#2E7D32"
        elif v >= 4:
            bar_color = "#E65100"
        else:
            bar_color = "#C62828"

        dim_rows += f"""
        <tr>
          <td style="padding:6px 8px;font-size:12px;font-weight:bold;">{label}</td>
          <td style="padding:6px;text-align:center;color:{bar_color};font-weight:bold;font-size:13px;">{v}/10</td>
          <td style="padding:6px;"><div style="background:#eee;height:14px;border-radius:7px;overflow:hidden;"><div style="background:{bar_color};height:100%;width:{bar_pct}%;border-radius:7px;"></div></div></td>
          <td style="padding:6px;text-align:center;font-size:11px;color:#777;">x{pct}</td>
        </tr>"""

    # Key indicators summary
    ind = indicators
    key_stats = f"""
    <table style="width:100%;border-collapse:collapse;margin:8px 0;font-size:11px;">
      <tr>
        <td style="padding:4px 8px;">Taux rappel:</td>
        <td style="padding:4px;font-weight:bold;">{ind.get('taux_rappel_corrige', 0)}%</td>
        <td style="padding:4px 8px;">Delai rappel:</td>
        <td style="padding:4px;font-weight:bold;">{ind.get('delai_moyen_min', 0)} min</td>
      </tr>
      <tr>
        <td style="padding:4px 8px;">Conformite signature:</td>
        <td style="padding:4px;font-weight:bold;">{ind.get('conformite_signature', 0)}%</td>
        <td style="padding:4px 8px;">Occupation:</td>
        <td style="padding:4px;font-weight:bold;">{ind.get('taux_occupation', 0)}%</td>
      </tr>
      <tr>
        <td style="padding:4px 8px;">Duree dans cible:</td>
        <td style="padding:4px;font-weight:bold;">{ind.get('duree_dans_cible_pct', 0)}%</td>
        <td style="padding:4px 8px;">Rush horaire:</td>
        <td style="padding:4px;font-weight:bold;">{ind.get('facteur_rush', 0)}x</td>
      </tr>
    </table>"""

    # Non-rappeles section
    nr_section = ""
    non_rappeles = ind.get("non_rappeles", [])
    if non_rappeles:
        nr_rows = ""
        for nr in non_rappeles[:10]:
            name = nr.get("name") or nr.get("number", "?")
            miss_time = nr.get("miss_time", "")[-8:] if nr.get("miss_time") else "?"
            att = nr.get("attempts", 0)
            att_txt = f"{att} tentative(s)" if att > 0 else "aucune tentative"
            nr_rows += f"""
            <tr>
              <td style="padding:4px 8px;font-size:11px;">{name}</td>
              <td style="padding:4px;text-align:center;font-size:11px;">{miss_time}</td>
              <td style="padding:4px;font-size:11px;color:#777;">{att_txt}</td>
            </tr>"""
        nr_section = f"""
        <div style="background:#FFEBEE;border-left:4px solid #C62828;padding:8px 12px;margin:8px 0;">
          <strong style="color:#C62828;font-size:12px;">Non rappeles: {len(non_rappeles)} contact(s)</strong>
          <table style="width:100%;margin-top:4px;">
            <tr style="font-size:10px;color:#999;"><th style="text-align:left;padding:2px 8px;">Contact</th><th>Heure manque</th><th style="text-align:left;">Tentatives</th></tr>
            {nr_rows}
          </table>
        </div>"""

    return f"""
    <div style="background:{score_bg};border:2px solid {score_color};border-radius:8px;padding:15px;margin:0 0 15px;">
      <div style="text-align:center;margin-bottom:10px;">
        <div style="font-size:11px;color:#777;text-transform:uppercase;letter-spacing:1px;">Score Qualite SAC</div>
        <div style="font-size:42px;font-weight:bold;color:{score_color};">{global_score}<span style="font-size:18px;color:#999;">/100</span></div>
      </div>
      <table style="width:100%;border-collapse:collapse;">
        <tr style="font-size:10px;color:#999;">
          <th style="text-align:left;padding:3px 8px;">Dimension</th>
          <th style="width:50px;">Score</th>
          <th style="width:40%;">Barre</th>
          <th style="width:40px;">Poids</th>
        </tr>
        {dim_rows}
      </table>
      {key_stats}
      {nr_section}
    </div>"""


def build_alerts_html(smart):
    """Build alert sections for frustrated clients and bad hours."""
    sections = ""

    # Frustrated clients (5+ calls)
    frustrated = smart.get("frustrated_clients", [])
    if frustrated:
        rows = ""
        for fc in frustrated[:5]:
            name = fc.get("name") or fc.get("number", "?")
            rows += f'<tr><td style="padding:4px 8px;font-size:12px;">{name}</td>'
            rows += f'<td style="padding:4px;text-align:center;font-weight:bold;color:#C62828;">{fc["calls"]}x</td>'
            rows += f'<td style="padding:4px;text-align:center;">{fc["missed"]} manques</td></tr>'
        sections += f"""
        <div style="background:#FFEBEE;border-left:4px solid #C62828;padding:10px 15px;margin:0 0 10px;font-size:12px;">
          <strong style="color:#C62828;">Clients frustres ({len(frustrated)} contacts avec 5+ appels)</strong>
          <table style="margin-top:5px;width:100%;">
            <tr style="font-size:10px;color:#999;"><th style="text-align:left;padding:3px 8px;">Contact</th><th>Appels</th><th>Manques</th></tr>
            {rows}
          </table>
        </div>"""

    # Hourly miss alerts
    alerts = smart.get("alert_hours", [])
    if alerts:
        items = ", ".join(f"{a['hour']}h ({a['missed']}/{a['total_in']} = {a['miss_rate']}%)" for a in alerts[:3])
        sections += f"""
        <div style="background:#FFF3E0;border-left:4px solid #E65100;padding:8px 15px;margin:0 0 10px;font-size:12px;">
          <strong style="color:#E65100;">Heures critiques (>70% manques):</strong> {items}
        </div>"""

    return sections


def build_email_html(date_str, smart, transcribed_calls, sms_stats=None, email_stats=None, conv_stats=None):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = DAYS_FR.get(dt.weekday(), "")
    s = smart["summary"]
    raw = smart["raw"]
    dedup = smart["dedup"]
    is_weekend = smart.get("is_weekend", False)
    agent_du_jour = smart.get("agent_du_jour", "SAC")

    # Score section (39 indicators)
    ind = smart.get("indicators", {})
    score_section = score_html_section(ind) if ind else ""

    # Alerts section
    alerts_section = build_alerts_html(smart)

    # SMS section
    sms_section = sms_html_section(sms_stats) if sms_stats and sms_stats.get("total", 0) > 0 else ""

    # Email section
    email_section = email_html_section(email_stats) if email_stats and email_stats.get("total_received", 0) > 0 else ""

    # Conversion section
    conv_section = conversion_html_section(conv_stats) if conv_stats and conv_stats.get("total", 0) > 0 else ""

    # Colors
    real_rate = s["taux_reel"]
    real_color = "#2E7D32" if real_rate >= 70 else "#E65100" if real_rate >= 40 else "#C62828"
    brut_rate = s["taux_brut"]
    brut_color = "#2E7D32" if brut_rate >= 70 else "#E65100" if brut_rate >= 40 else "#C62828"

    # Account rows
    acct_rows = ""
    acct_labels = {"academie": "Academie", "formateur": "Formateur"}
    for acct_name, a in raw["by_account"].items():
        rc = "#2E7D32" if a["response_rate"] >= 70 else "#E65100" if a["response_rate"] >= 40 else "#C62828"
        acct_rows += f"""
        <tr>
          <td style="padding:8px;font-weight:bold;">{acct_labels.get(acct_name, acct_name)}</td>
          <td style="padding:8px;text-align:center;">{a['total']}</td>
          <td style="padding:8px;text-align:center;">{a['in']}</td>
          <td style="padding:8px;text-align:center;color:#2E7D32;">{a['in_answered']}</td>
          <td style="padding:8px;text-align:center;color:#C62828;">{a['in_missed']}</td>
          <td style="padding:8px;text-align:center;">{a['out']}</td>
          <td style="padding:8px;text-align:center;color:{rc};font-weight:bold;">{a['response_rate']}%</td>
        </tr>"""

    # Hourly distribution
    hour_rows = ""
    for h in range(8, 18):
        hd = raw["by_hour"].get(h, {"total": 0, "answered": 0, "missed": 0, "outbound": 0})
        if hd["total"] == 0:
            continue
        mc = "#C62828" if hd["missed"] > 5 else "#E65100" if hd["missed"] > 2 else "#333"
        hour_rows += f"""
        <tr>
          <td style="padding:6px;text-align:center;font-weight:bold;">{h}h</td>
          <td style="padding:6px;text-align:center;">{hd['total']}</td>
          <td style="padding:6px;text-align:center;color:#2E7D32;">{hd['answered']}</td>
          <td style="padding:6px;text-align:center;color:{mc};font-weight:bold;">{hd['missed']}</td>
          <td style="padding:6px;text-align:center;">{hd['outbound']}</td>
        </tr>"""

    # Agent stats from transcribed calls
    agent_rows = ""
    for pid, name in PERSON_NAMES.items():
        pc = [c for c in transcribed_calls if c["person_id"] == pid]
        if not pc:
            continue
        inb = len([c for c in pc if c.get("direction") == "inbound"])
        outb = len([c for c in pc if c.get("direction") == "outbound"])
        durs = [c.get("duration_s", 0) for c in pc if c.get("duration_s", 0) > 0]
        avg_dur = round(sum(durs) / len(durs) / 60, 1) if durs else 0
        total_min = round(sum(durs) / 60)
        ai = [c for c in pc if c.get("ai_global_score") is not None]
        avg_score = round(sum(c["ai_global_score"] for c in ai) / len(ai), 1) if ai else 0
        sc = "#C62828" if avg_score < 4 else "#E65100" if avg_score < 5.5 else "#2E7D32"
        cats = defaultdict(int)
        for c in pc:
            cats[c.get("classification", "autre")] += 1
        cat_str = ", ".join(f"{k}:{v}" for k, v in sorted(cats.items(), key=lambda x: -x[1]))
        agent_rows += f"""
        <tr>
          <td style="padding:8px;font-weight:bold;">{name}</td>
          <td style="padding:8px;text-align:center;">{len(pc)}</td>
          <td style="padding:8px;text-align:center;">{inb}/{outb}</td>
          <td style="padding:8px;text-align:center;color:{sc};font-weight:bold;">{avg_score}/10</td>
          <td style="padding:8px;text-align:center;">{avg_dur}min</td>
          <td style="padding:8px;text-align:center;">{total_min}min</td>
          <td style="padding:8px;font-size:11px;">{cat_str}</td>
        </tr>"""

    # Duration stats per agent
    duration_rows = ""
    for pid, name in PERSON_NAMES.items():
        pc = [c for c in transcribed_calls if c["person_id"] == pid]
        if not pc:
            continue
        durs = [c.get("duration_s", 0) for c in pc if c.get("duration_s", 0) > 0]
        if not durs:
            continue
        avg_d = round(sum(durs) / len(durs) / 60, 1)
        sorted_d = sorted(durs)
        med_d = round(sorted_d[len(sorted_d) // 2] / 60, 1)
        max_d = round(max(durs) / 60, 1)
        total_d = round(sum(durs) / 60)
        total_h = f"{total_d // 60}h{total_d % 60:02d}" if total_d >= 60 else f"{total_d} min"
        duration_rows += f"""
        <tr>
          <td style="padding:8px;font-weight:bold;">{name}</td>
          <td style="padding:8px;text-align:center;">{len(pc)}</td>
          <td style="padding:8px;text-align:center;font-weight:bold;">{avg_d} min</td>
          <td style="padding:8px;text-align:center;">{med_d} min</td>
          <td style="padding:8px;text-align:center;">{max_d} min</td>
          <td style="padding:8px;text-align:center;">{total_h}</td>
        </tr>"""

    # Best / worst
    ai_calls = [c for c in transcribed_calls if c.get("ai_global_score") is not None]
    sorted_calls = sorted(ai_calls, key=lambda c: c["ai_global_score"], reverse=True)

    best_rows = ""
    for c in sorted_calls[:3]:
        t = (c.get("call_time") or "").split("T")[1][:5] if "T" in (c.get("call_time") or "") else "?"
        note = (c.get("coaching_note") or "")[:120]
        best_rows += f"""
        <tr>
          <td style="padding:6px;color:#2E7D32;font-weight:bold;">{c['ai_global_score']}/10</td>
          <td style="padding:6px;">{PERSON_NAMES.get(c['person_id'],'?')}</td>
          <td style="padding:6px;">{t}</td>
          <td style="padding:6px;">{(c.get('contact_name') or 'Inconnu')[:20]}</td>
          <td style="padding:6px;font-style:italic;color:#555;font-size:11px;">{note}</td>
        </tr>"""

    worst_rows = ""
    for c in sorted_calls[-3:] if len(sorted_calls) >= 3 else []:
        t = (c.get("call_time") or "").split("T")[1][:5] if "T" in (c.get("call_time") or "") else "?"
        note = (c.get("coaching_note") or "")[:120]
        worst_rows += f"""
        <tr>
          <td style="padding:6px;color:#C62828;font-weight:bold;">{c['ai_global_score']}/10</td>
          <td style="padding:6px;">{PERSON_NAMES.get(c['person_id'],'?')}</td>
          <td style="padding:6px;">{t}</td>
          <td style="padding:6px;">{(c.get('contact_name') or 'Inconnu')[:20]}</td>
          <td style="padding:6px;font-style:italic;color:#555;font-size:11px;">{note}</td>
        </tr>"""

    # Quality distribution
    dist = {"excellent": 0, "bon": 0, "moyen": 0, "faible": 0}
    for c in ai_calls:
        v = c["ai_global_score"]
        if v >= 7: dist["excellent"] += 1
        elif v >= 5: dist["bon"] += 1
        elif v >= 3: dist["moyen"] += 1
        else: dist["faible"] += 1

    # Shift split (matin vs apres-midi)
    shift_html = ""
    shifts = smart.get("shifts", {})
    if shifts:
        shift_html = '<h2 style="color:#1B3A5C;border-bottom:2px solid #1B3A5C;padding-bottom:5px;font-size:15px;">Performance par plage horaire</h2>\n'
        shift_html += '<table style="width:100%;border-collapse:collapse;margin:10px 0 15px;font-size:12px;">\n'
        shift_html += '<tr style="background:#1B3A5C;color:white;"><th style="padding:7px;text-align:left;">Plage</th><th style="padding:7px;">Appels</th><th style="padding:7px;">Entrants</th><th style="padding:7px;">Repondus</th><th style="padding:7px;">Manques brut</th><th style="padding:7px;">Vrais manques</th><th style="padding:7px;">Taux brut</th><th style="padding:7px;">Taux reel</th></tr>\n'
        for i, (sn, sh) in enumerate(shifts.items()):
            bg = 'background:#f9f9f9;' if i % 2 else ''
            rc = "#2E7D32" if sh["taux_reel"] >= 70 else "#E65100" if sh["taux_reel"] >= 40 else "#C62828"
            shift_html += f'<tr style="{bg}"><td style="padding:7px;font-weight:bold;">{sh["label"]}</td>'
            shift_html += f'<td style="padding:7px;text-align:center;">{sh["total"]}</td>'
            shift_html += f'<td style="padding:7px;text-align:center;">{sh["in_total"]}</td>'
            shift_html += f'<td style="padding:7px;text-align:center;color:#2E7D32;">{sh["in_answered"]}</td>'
            shift_html += f'<td style="padding:7px;text-align:center;color:#C62828;">{sh["in_missed"]}</td>'
            shift_html += f'<td style="padding:7px;text-align:center;color:#C62828;font-weight:bold;">{sh["vrais_manques"]}</td>'
            shift_html += f'<td style="padding:7px;text-align:center;">{sh["response_rate_brut"]}%</td>'
            shift_html += f'<td style="padding:7px;text-align:center;color:{rc};font-weight:bold;">{sh["taux_reel"]}%</td></tr>\n'
            # Sub-rows per account
            for an, av in sh["by_account"].items():
                al = acct_labels.get(an, an)
                arc = "#2E7D32" if av["response_rate"] >= 70 else "#E65100" if av["response_rate"] >= 40 else "#C62828"
                shift_html += f'<tr style="font-size:11px;color:#777;"><td style="padding:3px 7px 3px 20px;" colspan="2">{al}</td>'
                shift_html += f'<td style="padding:3px;text-align:center;">{av["in"]}</td>'
                shift_html += f'<td style="padding:3px;text-align:center;">{av["in_answered"]}</td>'
                shift_html += f'<td style="padding:3px;text-align:center;">{av["in_missed"]}</td>'
                shift_html += f'<td></td><td style="padding:3px;text-align:center;color:{arc};">{av["response_rate"]}%</td><td></td></tr>\n'
        shift_html += '</table>\n'

    # Dedup details rows
    dedup_rows = ""
    for d in dedup.get("details", [])[:5]:
        dedup_rows += f"""
        <tr>
          <td style="padding:4px;font-size:11px;">{d.get('name') or d.get('number','?')}</td>
          <td style="padding:4px;text-align:center;font-size:11px;">{d['removed']}</td>
          <td style="padding:4px;font-size:11px;color:#777;">{d['reason']}</td>
        </tr>"""

    html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:750px;margin:0 auto;">

<div style="background:#1B3A5C;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="color:white;margin:0;font-size:22px;">Rapport Quotidien SAC — {agent_du_jour}</h1>
  <p style="color:#ccc;margin:5px 0 0;">{day_name} {date_str} | {'8h-17h (weekend, formateur@ exclu)' if is_weekend else 'Heures de travail (8h-18h)'}</p>
</div>

<div style="padding:20px;border:1px solid #ddd;border-top:none;">

<!-- KPI Cards -->
<table style="width:100%;border-collapse:collapse;margin:0 0 15px;">
  <tr>
    <td style="padding:12px;text-align:center;background:#f5f5f5;border:1px solid #eee;">
      <div style="font-size:26px;font-weight:bold;color:#1B3A5C;">{s['total_calls']}</div>
      <div style="font-size:10px;color:#777;">Appels (8h-18h)</div>
    </td>
    <td style="padding:12px;text-align:center;background:#f5f5f5;border:1px solid #eee;">
      <div style="font-size:26px;font-weight:bold;color:#2E7D32;">{s['answered']}</div>
      <div style="font-size:10px;color:#777;">Repondus</div>
    </td>
    <td style="padding:12px;text-align:center;background:#f5f5f5;border:1px solid #eee;">
      <div style="font-size:26px;font-weight:bold;color:#C62828;">{s['vrais_manques']}</div>
      <div style="font-size:10px;color:#777;">Vrais manques</div>
    </td>
    <td style="padding:12px;text-align:center;background:#f5f5f5;border:1px solid #eee;">
      <div style="font-size:26px;font-weight:bold;color:{real_color};">{real_rate}%</div>
      <div style="font-size:10px;color:#777;">Taux REEL</div>
    </td>
    <td style="padding:12px;text-align:center;background:#f5f5f5;border:1px solid #eee;">
      <div style="font-size:26px;font-weight:bold;color:#1B3A5C;">{len(transcribed_calls)}</div>
      <div style="font-size:10px;color:#777;">Transcrits</div>
    </td>
  </tr>
</table>

{score_section}

{alerts_section}

<!-- Analyse des manques -->
<div style="background:#FFF8E1;border-left:4px solid #F57F17;padding:12px 15px;margin:0 0 15px;font-size:12px;">
  <strong>Analyse des {s['missed_brut']} appels manques (8h-18h):</strong><br>
  <table style="margin-top:5px;font-size:12px;">
    <tr><td style="padding:2px 10px 2px 0;">Rappels du meme client:</td><td style="font-weight:bold;">{s['missed_doublons']} retires</td></tr>
    <tr><td style="padding:2px 10px 2px 0;">Agent deja en appel:</td><td style="font-weight:bold;">{s['missed_agent_occupe']} justifies</td></tr>
    <tr><td style="padding:2px 10px 2px 0;color:#C62828;font-weight:bold;">VRAIS manques:</td><td style="color:#C62828;font-weight:bold;">{s['vrais_manques']}</td></tr>
  </table>
  <div style="margin-top:5px;color:#777;">Taux brut: {brut_rate}% → Deduplique: {s['taux_deduplique']}% → <strong style="color:{real_color};">Reel: {real_rate}%</strong></div>
  {f'<div style="margin-top:3px;color:#777;font-size:11px;">{s["after_hours_excluded"]} appels hors heures exclus (avant 8h / apres 18h)</div>' if s.get('after_hours_excluded', 0) > 0 else ''}
</div>

{f'''<div style="background:#FFF3E0;border-left:4px solid #E65100;padding:8px 15px;margin:0 0 15px;font-size:11px;">
  <strong>Top rappeleurs (doublons retires):</strong>
  <table style="margin-top:4px;"><tr style="color:#777;"><th style="padding:3px;text-align:left;">Client</th><th style="padding:3px;">Retires</th><th style="padding:3px;">Raison</th></tr>{dedup_rows}</table>
</div>''' if dedup_rows else ''}

{shift_html}

<!-- Volume par compte -->
<h2 style="color:#1B3A5C;border-bottom:2px solid #1B3A5C;padding-bottom:5px;font-size:15px;">Volume par compte (8h-18h)</h2>
<table style="width:100%;border-collapse:collapse;margin:10px 0 15px;font-size:12px;">
  <tr style="background:#1B3A5C;color:white;">
    <th style="padding:7px;text-align:left;">Compte</th><th style="padding:7px;">Total</th><th style="padding:7px;">Entrants</th>
    <th style="padding:7px;">Repondus</th><th style="padding:7px;">Manques</th><th style="padding:7px;">Sortants</th><th style="padding:7px;">Taux</th>
  </tr>
  {acct_rows}
</table>

<!-- Distribution horaire -->
<h2 style="color:#1B3A5C;border-bottom:2px solid #1B3A5C;padding-bottom:5px;font-size:15px;">Distribution horaire</h2>
<table style="width:100%;border-collapse:collapse;margin:10px 0 15px;font-size:12px;">
  <tr style="background:#1B3A5C;color:white;">
    <th style="padding:6px;">Heure</th><th style="padding:6px;">Total</th><th style="padding:6px;">Repondus</th><th style="padding:6px;">Manques</th><th style="padding:6px;">Sortants</th>
  </tr>
  {hour_rows}
</table>

<!-- Appels transcrits -->
<h2 style="color:#1B3A5C;border-bottom:2px solid #1B3A5C;padding-bottom:5px;font-size:15px;">Appels transcrits + Score IA ({len(transcribed_calls)})</h2>
<table style="width:100%;border-collapse:collapse;margin:10px 0 15px;font-size:12px;">
  <tr style="background:#1B3A5C;color:white;">
    <th style="padding:7px;text-align:left;">Agent</th><th style="padding:7px;">Trans.</th><th style="padding:7px;">IN/OUT</th>
    <th style="padding:7px;">Score IA</th><th style="padding:7px;">Dur. moy.</th><th style="padding:7px;">Total</th><th style="padding:7px;text-align:left;">Cat.</th>
  </tr>
  {agent_rows}
</table>

<!-- Duree des appels -->
<h2 style="color:#1B3A5C;border-bottom:2px solid #1B3A5C;padding-bottom:5px;font-size:15px;">Duree des appels</h2>
<table style="width:100%;border-collapse:collapse;margin:10px 0 15px;font-size:12px;">
  <tr style="background:#1B3A5C;color:white;">
    <th style="padding:7px;text-align:left;">Agent</th><th style="padding:7px;">Appels</th><th style="padding:7px;">Moy.</th>
    <th style="padding:7px;">Mediane</th><th style="padding:7px;">Max</th><th style="padding:7px;">Total</th>
  </tr>
  {duration_rows}
</table>

<!-- Meilleurs appels -->
<h2 style="color:#2E7D32;border-bottom:2px solid #2E7D32;padding-bottom:5px;font-size:15px;">Meilleurs appels</h2>
<table style="width:100%;border-collapse:collapse;margin:10px 0 15px;font-size:12px;">
  <tr style="background:#E8F5E9;"><th style="padding:6px;">Score</th><th style="padding:6px;">Agent</th><th style="padding:6px;">Heure</th><th style="padding:6px;">Contact</th><th style="padding:6px;text-align:left;">Coaching</th></tr>
  {best_rows}
</table>

<!-- Appels a ameliorer -->
<h2 style="color:#C62828;border-bottom:2px solid #C62828;padding-bottom:5px;font-size:15px;">Appels a ameliorer</h2>
<table style="width:100%;border-collapse:collapse;margin:10px 0 15px;font-size:12px;">
  <tr style="background:#FFEBEE;"><th style="padding:6px;">Score</th><th style="padding:6px;">Agent</th><th style="padding:6px;">Heure</th><th style="padding:6px;">Contact</th><th style="padding:6px;text-align:left;">Coaching</th></tr>
  {worst_rows}
</table>

<!-- Qualite -->
<table style="width:100%;border-collapse:collapse;margin:10px 0;">
  <tr>
    <td style="padding:10px;text-align:center;background:#E8F5E9;border:1px solid #eee;"><strong style="color:#2E7D32;font-size:18px;">{dist['excellent']}</strong><br><small>Excellent (7+)</small></td>
    <td style="padding:10px;text-align:center;background:#FFF3E0;border:1px solid #eee;"><strong style="color:#E65100;font-size:18px;">{dist['bon']}</strong><br><small>Bon (5-7)</small></td>
    <td style="padding:10px;text-align:center;background:#FFF8E1;border:1px solid #eee;"><strong style="color:#F57F17;font-size:18px;">{dist['moyen']}</strong><br><small>Moyen (3-5)</small></td>
    <td style="padding:10px;text-align:center;background:#FFEBEE;border:1px solid #eee;"><strong style="color:#C62828;font-size:18px;">{dist['faible']}</strong><br><small>Faible (&lt;3)</small></td>
  </tr>
</table>

{sms_section}

{email_section}

{conv_section}

</div>

<div style="background:#f5f5f5;padding:10px;border-radius:0 0 8px 8px;text-align:center;border:1px solid #ddd;border-top:none;">
  <p style="color:#999;font-size:11px;margin:0;">Academie XGuard — Coaching IA automatise |
  <a href="https://drive.google.com/drive/folders/18AYzF7-FrWx8wfXC_wM3CGl1uM_t_Xx6" style="color:#1B3A5C;">Google Drive</a></p>
</div>

</body></html>"""

    return html


def send_email_smtp(date_str, html_body, global_score=None):
    """Send email directly via Gmail SMTP — no Claude CLI needed."""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = DAYS_FR.get(dt.weekday(), "")

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = "hmaghraoui65@gmail.com"
    msg["Cc"] = "nick@darkhorseads.com"
    if global_score is not None:
        msg["Subject"] = f"SAC {day_name} {date_str} — {global_score}/100 — Rapport Quotidien"
    else:
        msg["Subject"] = f"SAC {day_name} {date_str} — Rapport Quotidien"

    msg.attach(MIMEText(html_body, "html", "utf-8"))

    recipients = ["hmaghraoui65@gmail.com", "nick@darkhorseads.com"]

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, recipients, msg.as_string())
        log.info("Email SENT to %s", ", ".join(recipients))
    except Exception as e:
        log.error("Email send failed: %s", e)


def main():
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")

    log.info("=" * 60)
    log.info("DAILY EMAIL REPORT v3 — %s", date_str)
    log.info("=" * 60)

    # Smart stats (work hours, deduped, agent-busy)
    log.info("Computing smart stats...")
    smart = compute_smart_stats(date_str)
    s = smart["summary"]
    log.info("  Calls (8h-18h): %d | Answered: %d | Real missed: %d | Rate: %d%%",
             s["total_calls"], s["answered"], s["vrais_manques"], s["taux_reel"])

    if s["total_calls"] == 0:
        log.info("No calls — skipping")
        return

    # Transcribed calls from Supabase
    log.info("Fetching transcribed calls...")
    transcribed = get_transcribed_calls(date_str)
    log.info("  Transcribed: %d", len(transcribed))

    # SMS stats — cross-reference with call numbers from smart stats
    log.info("Fetching SMS stats...")
    sms_list = fetch_sms_for_date(date_str)
    # Get call numbers from raw stats for cross-ref
    call_numbers = set()
    for acct_data in smart.get("raw", {}).get("by_account", {}).values():
        pass  # by_account doesn't have numbers
    # Use a quick fetch from JustCall for numbers
    try:
        from smart_stats import fetch_all_raw
        for rc in fetch_all_raw(date_str):
            num = (rc.get("contact_number") or "").strip()
            if num and len(num) >= 7:
                call_numbers.add(num)
    except Exception:
        pass
    log.info("  Call numbers for cross-ref: %d", len(call_numbers))
    sms = analyze_sms(sms_list, date_str, call_numbers=call_numbers) if sms_list else None
    if sms:
        log.info("  SMS: %d total (%d in, %d out) | %d unanswered | %d hot leads",
                 sms["total"], sms["inbound"], sms["outbound"],
                 sms["unanswered_count"], sms["hot_leads_count"])

    # Email stats (IMAP)
    log.info("Fetching email stats (IMAP)...")
    try:
        em_stats = fetch_email_stats(date_str)
        log.info("  Emails: %d received, %d sent, %d unanswered",
                 em_stats["total_received"], em_stats["total_sent"], em_stats["unanswered_count"])
    except Exception as em_err:
        log.warning("Email stats failed (non-critical): %s", em_err)
        em_stats = None

    # Conversion stats (30 days)
    log.info("Fetching conversion stats...")
    try:
        conv_stats = get_conversion_stats(days=30)
        log.info("  Conversions (30d): %d | Rate: %s%% | Avg days: %s",
                 conv_stats["total"], conv_stats["call_to_conversion_rate"], conv_stats["avg_days"])
    except Exception as conv_err:
        log.warning("Conversion stats failed (non-critical): %s", conv_err)
        conv_stats = None

    # Build + send
    html = build_email_html(date_str, smart, transcribed, sms_stats=sms, email_stats=em_stats, conv_stats=conv_stats)
    log.info("HTML built (%d chars)", len(html))

    # Extract global score for subject line
    global_score = None
    ind = smart.get("indicators", {})
    if ind:
        global_score = ind.get("global_score")
        log.info("  Score global: %s/100", global_score)

    send_email_smtp(date_str, html, global_score=global_score)
    log.info("DONE!")


if __name__ == "__main__":
    main()
