#!/usr/bin/env python3
"""
KB Approval Email — Daily cron (07h30) on Nitro.
Sends morning email to Nick with pending KB topics to review.
Includes link to admin page for approvals.
"""

import json
import logging
import os
import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_config import (
    GMAIL_USER, GMAIL_APP_PASSWORD, NICK_EMAIL,
    sb_get, sb_count,
)

LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / f"kb_approval_{datetime.now():%Y-%m-%d}.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger("kb_approval")

ADMIN_URL = "https://nicksoucy.github.io/orgnigram-xguard/kb_admin.html"

CATEGORY_LABELS = {
    "inscription": ("Inscription", "#2E7D32"),
    "paiement": ("Paiement", "#1565C0"),
    "annulation": ("Annulation", "#E65100"),
    "plainte": ("Plainte", "#C62828"),
    "certificat": ("Certificat", "#6A1B9A"),
    "emploi": ("Emploi", "#00695C"),
    "info": ("Information", "#37474F"),
    "changement_date": ("Changement de date", "#F57F17"),
    "technique": ("Technique", "#455A64"),
    "autre": ("Autre", "#777"),
}


def build_approval_html():
    """Build the morning approval email HTML."""
    # Fetch stats
    total_emails = sb_count("kb_emails")
    total_topics = sb_count("kb_topics")
    pending = sb_get("kb_topics?select=*&approval_status=eq.pending&order=frequency.desc")
    approved_count = sb_count("kb_topics", "approval_status=eq.approved") + sb_count("kb_topics", "approval_status=eq.corrected")
    rejected_count = sb_count("kb_topics", "approval_status=eq.rejected")

    # Latest run info
    latest_run = sb_get("kb_run_log?select=*&script=eq.kb_email_analyzer&order=started_at.desc&limit=1")
    run_info = ""
    if latest_run:
        r = latest_run[0]
        run_info = f'{r.get("emails_analyzed", 0)} emails analyses | Batch: {r.get("batch_id", "?")}'

    # Group pending by category
    by_cat = {}
    for t in pending:
        cat = t.get("category", "autre")
        if cat not in by_cat:
            by_cat[cat] = []
        by_cat[cat].append(t)

    # Build topic rows grouped by category
    topics_html = ""
    for cat in sorted(by_cat.keys(), key=lambda c: -len(by_cat[c])):
        cat_label, cat_color = CATEGORY_LABELS.get(cat, (cat.capitalize(), "#777"))
        cat_topics = by_cat[cat]

        topics_html += f"""
        <div style="margin:15px 0 5px;">
          <span style="background:{cat_color};color:white;padding:4px 12px;border-radius:12px;font-size:12px;font-weight:bold;">
            {cat_label} ({len(cat_topics)})
          </span>
        </div>
        """

        for t in cat_topics:
            freq = t.get("frequency", 0)
            label = t.get("topic_label", "?")
            question = t.get("question_pattern", "")
            response = t.get("suggested_response", "")
            examples = t.get("example_subjects") or []

            # Frequency badge
            freq_color = "#C62828" if freq >= 20 else "#E65100" if freq >= 5 else "#777"

            examples_html = ""
            for ex in examples[:3]:
                examples_html += f'<li style="color:#555;font-size:11px;">{ex[:70]}</li>'

            topics_html += f"""
            <div style="background:white;border:1px solid #e0e0e0;border-left:4px solid {cat_color};border-radius:4px;padding:12px;margin:6px 0;">
              <div style="display:flex;justify-content:space-between;align-items:center;">
                <strong style="font-size:13px;">{label}</strong>
                <span style="background:#f5f5f5;color:{freq_color};padding:2px 8px;border-radius:10px;font-size:11px;font-weight:bold;">{freq}x</span>
              </div>
              {f'<p style="color:#1565C0;font-size:12px;margin:6px 0 4px;font-style:italic;">"{question}"</p>' if question else ''}
              {f'<div style="background:#F5F5F5;border-radius:4px;padding:8px;margin:6px 0;font-size:12px;color:#333;">{response[:200]}</div>' if response else ''}
              {f'<ul style="margin:4px 0;padding-left:20px;">{examples_html}</ul>' if examples_html else ''}
            </div>
            """

    if not pending:
        topics_html = """
        <div style="background:#E8F5E9;border-left:4px solid #2E7D32;padding:15px;margin:10px 0;border-radius:4px;">
          <strong style="color:#2E7D32;">Aucun topic en attente!</strong>
          <p style="color:#555;font-size:12px;margin:5px 0 0;">Tous les topics ont ete traites.</p>
        </div>
        """

    html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:0 auto;background:#f9f9f9;">

<div style="background:#1565C0;padding:20px;border-radius:8px 8px 0 0;text-align:center;">
  <h1 style="color:white;margin:0;font-size:20px;">Knowledge Base — Validation</h1>
  <p style="color:#BBDEFB;margin:5px 0 0;font-size:12px;">{datetime.now().strftime('%A %d %B %Y')} | {run_info}</p>
</div>

<div style="padding:20px;background:white;border:1px solid #ddd;border-top:none;">

<!-- Stats -->
<table style="width:100%;border-collapse:collapse;margin:0 0 15px;">
  <tr>
    <td style="padding:10px;text-align:center;background:#E3F2FD;border:1px solid #BBDEFB;">
      <div style="font-size:22px;font-weight:bold;color:#1565C0;">{total_emails}</div>
      <div style="font-size:10px;color:#777;">Emails analyses</div>
    </td>
    <td style="padding:10px;text-align:center;background:#E3F2FD;border:1px solid #BBDEFB;">
      <div style="font-size:22px;font-weight:bold;color:#1565C0;">{total_topics}</div>
      <div style="font-size:10px;color:#777;">Topics FAQ</div>
    </td>
    <td style="padding:10px;text-align:center;background:#FFF8E1;border:1px solid #FFF176;">
      <div style="font-size:22px;font-weight:bold;color:#F57F17;">{len(pending)}</div>
      <div style="font-size:10px;color:#777;">En attente</div>
    </td>
    <td style="padding:10px;text-align:center;background:#E8F5E9;border:1px solid #C8E6C9;">
      <div style="font-size:22px;font-weight:bold;color:#2E7D32;">{approved_count}</div>
      <div style="font-size:10px;color:#777;">Approuves</div>
    </td>
    <td style="padding:10px;text-align:center;background:#FFEBEE;border:1px solid #FFCDD2;">
      <div style="font-size:22px;font-weight:bold;color:#C62828;">{rejected_count}</div>
      <div style="font-size:10px;color:#777;">Rejetes</div>
    </td>
  </tr>
</table>

<!-- Action button -->
<div style="text-align:center;margin:15px 0;">
  <a href="{ADMIN_URL}" style="background:#1565C0;color:white;padding:12px 30px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:14px;">
    Ouvrir la page d'approbation
  </a>
</div>

<!-- Topics by category -->
<h2 style="color:#1565C0;border-bottom:2px solid #1565C0;padding-bottom:5px;font-size:15px;margin-top:20px;">
  Topics en attente ({len(pending)})
</h2>

{topics_html}

</div>

<div style="background:#f5f5f5;padding:10px;border-radius:0 0 8px 8px;text-align:center;border:1px solid #ddd;border-top:none;">
  <p style="color:#999;font-size:11px;margin:0;">
    Academie XGuard — Knowledge Base IA |
    <a href="{ADMIN_URL}" style="color:#1565C0;">Page d'approbation</a>
  </p>
</div>

</body></html>"""
    return html, len(pending)


def send_email(html):
    """Send email via Gmail SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_USER
    msg["To"] = NICK_EMAIL
    msg["Subject"] = f"KB XGuard — Topics a valider ({datetime.now():%Y-%m-%d})"
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, [NICK_EMAIL], msg.as_string())
        log.info("Approval email sent to %s", NICK_EMAIL)
    except Exception as e:
        log.error("Email send failed: %s", e)


def main():
    log.info("=" * 60)
    log.info("KB APPROVAL EMAIL — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 60)

    html, pending_count = build_approval_html()
    log.info("HTML built (%d chars), %d pending topics", len(html), pending_count)

    if pending_count == 0:
        log.info("No pending topics — skipping email.")
        return

    send_email(html)
    log.info("DONE!")


if __name__ == "__main__":
    main()
