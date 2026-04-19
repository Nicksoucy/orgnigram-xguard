"""
prospects_helpers.py — Query helpers for prospects_intelligence.

Gives smart_hot_leads.py (and any other script) a unified view of a prospect:
  - All calls (with transcripts excerpts)
  - All SMS (inbound + outbound)
  - All emails (subjects + categories)
  - Payment status
  - Programs mentioned
  - Our last outreach

Use this INSTEAD of hitting sac_calls/kb_emails/GHL separately.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from kb_config import sb_get
from phone_utils import normalize_number

log = logging.getLogger("prospects_helpers")


def get_prospect(phone=None, email=None, ghl_id=None):
    """Fetch a prospect by any identifier. Returns dict or None."""
    filters = []
    if phone:
        p = normalize_number(phone)
        if p and len(p) == 10:
            filters.append(f"phone_normalized=eq.{p}")
    if email:
        e = str(email).lower().strip()
        if e:
            filters.append(f"email_normalized=eq.{e}")
    if ghl_id:
        filters.append(f"ghl_contact_id=eq.{ghl_id}")

    if not filters:
        return None

    # Try each filter
    for f in filters:
        rows = sb_get(f"prospects_intelligence?{f}&limit=1")
        if rows and not isinstance(rows, dict):
            return rows[0]
    return None


def get_prospect_timeline(prospect_id, limit=30):
    """Fetch recent timeline events for a prospect."""
    rows = sb_get(
        f"prospects_intelligence/timeline?prospect_id=eq.{prospect_id}"
        f"&order=event_date.desc&limit={limit}"
    )
    return rows if isinstance(rows, list) else []


def get_prospect_full_context(phone=None, email=None, ghl_id=None, timeline_limit=20):
    """Get everything we know about a prospect — identity, stats, and recent events.
    Returns a dict ready to inject into a Haiku prompt.
    """
    p = get_prospect(phone=phone, email=email, ghl_id=ghl_id)
    if not p:
        return None

    timeline = sb_get(
        f"prospects_timeline?prospect_id=eq.{p['id']}"
        f"&order=event_date.desc&limit={timeline_limit}"
    )
    if not isinstance(timeline, list):
        timeline = []

    return {
        "prospect": p,
        "timeline": timeline,
        "summary_parts": _build_summary_parts(p, timeline),
    }


def _build_summary_parts(prospect, timeline):
    """Build human-readable bullet points for a prompt."""
    parts = []

    name = prospect.get("full_name") or prospect.get("first_name") or "(nom inconnu)"
    parts.append(f"Prospect: {name}")

    if prospect.get("has_gard_paid_tag"):
        parts.append(f"STATUS: DEJA PAYE (tag 'gard paid' le {prospect.get('paid_date')})")
    else:
        parts.append("STATUS: PAS ENCORE PAYE")

    if prospect.get("program_interested"):
        parts.append(f"Programme d'interet: {prospect['program_interested']}")
    if prospect.get("programs_mentioned"):
        parts.append(f"Programmes mentionnes: {', '.join(prospect['programs_mentioned'])}")

    # Volume summary
    calls = prospect.get("total_calls", 0)
    missed = prospect.get("missed_calls", 0)
    answered = prospect.get("answered_calls", 0)
    sms_in = prospect.get("total_sms_received", 0)
    sms_out = prospect.get("total_sms_sent", 0)
    emails_in = prospect.get("total_emails_received", 0)

    activity = []
    if calls:
        activity.append(f"{calls} appels ({answered} repondus, {missed} manques)")
    if sms_in or sms_out:
        activity.append(f"{sms_in} SMS recus, {sms_out} envoyes par nous")
    if emails_in:
        activity.append(f"{emails_in} emails envoyes par lui")

    if activity:
        parts.append("Historique: " + " | ".join(activity))

    # Last contact
    if prospect.get("last_inbound_date"):
        parts.append(f"Dernier contact inbound: {prospect['last_inbound_date']}")
    if prospect.get("days_since_last_inbound"):
        parts.append(f"Il y a {prospect['days_since_last_inbound']} jours")

    # Our outreach
    if prospect.get("times_we_contacted"):
        last = prospect.get("last_our_sms_at", "")
        parts.append(f"On lui a envoye {prospect['times_we_contacted']} SMS (dernier: {last})")

    # Recent events (last 5 most informative)
    if timeline:
        parts.append("")
        parts.append("Derniers evenements:")
        for ev in timeline[:8]:
            etype = ev.get("event_type", "")
            dt = ev.get("event_date", "")[:16]
            content = (ev.get("content_excerpt") or "").strip()[:200]
            parts.append(f"  [{dt}] {etype}: {content}")

    return parts


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    import sys as _sys
    if len(_sys.argv) < 2:
        print("Usage: python prospects_helpers.py <phone_or_email>")
        _sys.exit(1)

    arg = _sys.argv[1]
    if "@" in arg:
        ctx = get_prospect_full_context(email=arg)
    else:
        ctx = get_prospect_full_context(phone=arg)

    if not ctx:
        print(f"No prospect found for: {arg}")
        _sys.exit(1)

    print("\n".join(ctx["summary_parts"]))
