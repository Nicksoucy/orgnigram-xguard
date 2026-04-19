#!/usr/bin/env python3
"""
Sprint 16 — Prospects Intelligence Aggregator

Builds a unified view of every prospect by aggregating data from:
- sac_calls (all phone calls transcribed)
- kb_emails (all classified emails)
- google_sheets_sync_log (payment status from Jessica's sheet)
- hot_sms_sent (SMS we sent proactively)
- GHL contacts (tag 'gard paid')

Output:
- prospects_intelligence: one row per unique contact
- prospects_timeline: every event (call, SMS, email, our action)

DEDUP STRATEGY:
- Match on phone_normalized (10 digits)
- Match on email_normalized (lowercased, stripped)
- Match on ghl_contact_id
- Same phone OR same email OR same ghl_id = same prospect, merge.

RUN MODES:
  --full          Rebuild from scratch (slow, run monthly)
  --incremental   Only process new events since last run (default, fast)
  --limit N       Max prospects to process (testing)
  --dry-run       Don't write, just print stats
"""

import argparse
import logging
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))
os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

from kb_config import (
    SUPABASE_URL, SUPABASE_KEY,
    sb_upsert, sb_get,
    XGUARD_PAID_TAG,
)
from phone_utils import normalize_number

LOG_DIR = Path(r"C:\Users\user\sac_logs")
_handlers = [logging.StreamHandler()]
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _handlers.append(logging.FileHandler(
        str(LOG_DIR / f"prospects_agg_{datetime.now():%Y-%m-%d}.log"),
        encoding="utf-8",
    ))
except (PermissionError, OSError):
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=_handlers,
)
log = logging.getLogger("prospects_agg")


# ---------------------------------------------------------------------------
# Supabase helpers with pagination
# ---------------------------------------------------------------------------

def sb_select_all(path, batch_size=1000):
    """Fetch all rows with automatic pagination."""
    all_rows = []
    offset = 0
    while True:
        url = f"{SUPABASE_URL}/rest/v1/{path}"
        sep = "&" if "?" in path else "?"
        url += f"{sep}limit={batch_size}&offset={offset}"
        headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
        r = requests.get(url, headers=headers, timeout=60)
        if r.status_code != 200:
            log.warning("Fetch failed (%d): %s", r.status_code, r.text[:200])
            break
        batch = r.json()
        if not batch:
            break
        all_rows.extend(batch)
        if len(batch) < batch_size:
            break
        offset += batch_size
    return all_rows


def sb_exec_insert(table, rows):
    """Bulk insert rows (not upsert) — used for timeline."""
    if not rows:
        return
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal,resolution=ignore-duplicates",
    }
    # Chunks of 500
    for i in range(0, len(rows), 500):
        chunk = rows[i:i + 500]
        r = requests.post(url, headers=headers, json=chunk, timeout=60)
        if r.status_code not in (200, 201, 204):
            log.warning("Timeline insert failed (%d): %s", r.status_code, r.text[:300])


# ---------------------------------------------------------------------------
# Prospect dedup + merge
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$')


def _norm_email(email):
    if not email:
        return None
    e = str(email).lower().strip()
    return e if EMAIL_RE.match(e) else None


def _norm_phone(phone):
    if not phone:
        return None
    n = normalize_number(str(phone))
    return n if n and len(n) == 10 else None


class Prospect:
    """In-memory prospect object during aggregation."""

    def __init__(self):
        self.phone = None
        self.email = None
        self.ghl_id = None
        self.first_name = None
        self.last_name = None
        self.full_name = None

        self.has_paid = False
        self.paid_date = None
        self.paid_amount = None
        self.paid_source = None

        self.program = None
        self.programs = set()

        self.total_calls = 0
        self.missed_calls = 0
        self.answered_calls = 0
        self.total_call_seconds = 0
        self.total_sms_received = 0
        self.total_sms_sent = 0
        self.total_emails_received = 0
        self.total_emails_sent = 0

        self.first_contact = None
        self.last_contact = None
        self.last_inbound = None
        self.last_outbound = None

        self.last_our_sms_at = None
        self.last_our_sms_body = None
        self.times_we_contacted = 0

        self.events = []  # Timeline entries: dicts to insert later

    def update_name(self, name):
        """Set name if not already known."""
        if not name:
            return
        name = str(name).strip()
        if not name or name.lower() in ("inconnu", "unknown", "none"):
            return
        if not self.full_name:
            self.full_name = name
            parts = name.split()
            if len(parts) >= 2:
                self.first_name = parts[0]
                self.last_name = " ".join(parts[1:])
            else:
                self.first_name = parts[0]

    def touch_first_last(self, dt):
        """Update first_contact / last_contact based on dt."""
        if not dt:
            return
        if not self.first_contact or dt < self.first_contact:
            self.first_contact = dt
        if not self.last_contact or dt > self.last_contact:
            self.last_contact = dt

    def touch_inbound(self, dt):
        self.touch_first_last(dt)
        if dt and (not self.last_inbound or dt > self.last_inbound):
            self.last_inbound = dt

    def touch_outbound(self, dt):
        self.touch_first_last(dt)
        if dt and (not self.last_outbound or dt > self.last_outbound):
            self.last_outbound = dt

    def add_event(self, event_type, dt, content=None, direction=None,
                  duration=None, source_table=None, source_id=None, metadata=None):
        if not dt:
            return
        self.events.append({
            "event_type": event_type,
            "event_date": dt.isoformat() if hasattr(dt, "isoformat") else dt,
            "direction": direction,
            "content_excerpt": (content or "")[:500],
            "duration_sec": duration,
            "source_table": source_table,
            "source_id": str(source_id) if source_id else None,
            "metadata": metadata,
        })

    def to_dict(self):
        d = {}
        if self.phone:
            d["phone_normalized"] = self.phone
        if self.email:
            d["email_normalized"] = self.email
        if self.ghl_id:
            d["ghl_contact_id"] = self.ghl_id
        if self.first_name:
            d["first_name"] = self.first_name
        if self.last_name:
            d["last_name"] = self.last_name
        if self.full_name:
            d["full_name"] = self.full_name

        d["has_gard_paid_tag"] = self.has_paid
        if self.paid_date:
            d["paid_date"] = self.paid_date.isoformat() if hasattr(self.paid_date, "isoformat") else self.paid_date
        if self.paid_amount:
            d["paid_amount"] = float(self.paid_amount)
        if self.paid_source:
            d["paid_source"] = self.paid_source

        if self.program:
            d["program_interested"] = self.program
        if self.programs:
            d["programs_mentioned"] = list(self.programs)

        d["total_calls"] = self.total_calls
        d["missed_calls"] = self.missed_calls
        d["answered_calls"] = self.answered_calls
        d["total_call_seconds"] = self.total_call_seconds
        d["total_sms_received"] = self.total_sms_received
        d["total_sms_sent"] = self.total_sms_sent
        d["total_emails_received"] = self.total_emails_received
        d["total_emails_sent"] = self.total_emails_sent

        if self.first_contact:
            d["first_contact_date"] = self.first_contact.isoformat()
        if self.last_contact:
            d["last_contact_date"] = self.last_contact.isoformat()
            days_ago = (datetime.now(timezone.utc) - self.last_contact).days if self.last_contact.tzinfo else (datetime.now() - self.last_contact).days
            d["days_since_last_inbound"] = days_ago
        if self.last_inbound:
            d["last_inbound_date"] = self.last_inbound.isoformat()
        if self.last_outbound:
            d["last_outbound_date"] = self.last_outbound.isoformat()

        if self.last_our_sms_at:
            d["last_our_sms_at"] = self.last_our_sms_at.isoformat()
        if self.last_our_sms_body:
            d["last_our_sms_body"] = self.last_our_sms_body[:500]
        d["times_we_contacted"] = self.times_we_contacted

        # Determine stage
        if self.has_paid:
            d["stage"] = "paid"
        elif self.answered_calls > 0 or self.total_sms_received >= 2:
            d["stage"] = "engaged"
        else:
            d["stage"] = "prospect"

        d["updated_at"] = datetime.now().isoformat()
        return d


class ProspectRegistry:
    """Dedup + merge prospects as we aggregate data."""

    def __init__(self):
        self.by_phone = {}
        self.by_email = {}
        self.by_ghl = {}
        self.all = []

    def find_or_create(self, phone=None, email=None, ghl_id=None, name=None):
        phone = _norm_phone(phone)
        email = _norm_email(email)

        # Try to find existing
        existing = None
        if phone and phone in self.by_phone:
            existing = self.by_phone[phone]
        elif email and email in self.by_email:
            existing = self.by_email[email]
        elif ghl_id and ghl_id in self.by_ghl:
            existing = self.by_ghl[ghl_id]

        if existing is None:
            existing = Prospect()
            self.all.append(existing)

        # Merge identifiers
        if phone and not existing.phone:
            existing.phone = phone
            self.by_phone[phone] = existing
        if email and not existing.email:
            existing.email = email
            self.by_email[email] = existing
        if ghl_id and not existing.ghl_id:
            existing.ghl_id = ghl_id
            self.by_ghl[ghl_id] = existing

        if name:
            existing.update_name(name)

        return existing

    def stats(self):
        total = len(self.all)
        with_phone = sum(1 for p in self.all if p.phone)
        with_email = sum(1 for p in self.all if p.email)
        paid = sum(1 for p in self.all if p.has_paid)
        return dict(total=total, with_phone=with_phone, with_email=with_email, paid=paid)


# ---------------------------------------------------------------------------
# Data source ingesters
# ---------------------------------------------------------------------------

def _parse_dt(s):
    """Parse various datetime formats. Returns datetime or None."""
    if not s:
        return None
    if isinstance(s, datetime):
        return s
    s = str(s).strip()
    if not s:
        return None
    # Try ISO formats
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s.replace("Z", "+0000").replace("+00:00", "+0000"), fmt)
        except Exception:
            continue
    # Last resort: fromisoformat
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def ingest_sac_calls(registry):
    """Load all calls from sac_calls table."""
    log.info("Ingesting sac_calls...")
    rows = sb_select_all("sac_calls?select=call_id,call_time,duration_s,direction,contact_name,contact_number,classification,ai_global_score,coaching_note,transcript&order=call_time")
    log.info("  %d call records", len(rows))

    for r in rows:
        phone = r.get("contact_number")
        if not phone:
            continue
        name = r.get("contact_name") or ""
        p = registry.find_or_create(phone=phone, name=name)

        dt = _parse_dt(r.get("call_time"))
        dur = int(r.get("duration_s") or 0)
        is_inbound = (r.get("direction") or "").lower() in ("inbound", "1")
        classification = r.get("classification")

        p.total_calls += 1
        p.total_call_seconds += dur
        if is_inbound:
            if dur > 0:
                p.answered_calls += 1
                p.touch_inbound(dt)
            else:
                p.missed_calls += 1
                p.touch_inbound(dt)
        else:
            p.touch_outbound(dt)

        if classification:
            p.programs.add(classification)
            if not p.program:
                p.program = classification

        transcript = r.get("transcript") or ""
        excerpt = transcript[:300] if transcript else (r.get("coaching_note") or "")

        p.add_event(
            event_type="call_inbound" if is_inbound else "call_outbound",
            dt=dt,
            content=excerpt,
            direction="inbound" if is_inbound else "outbound",
            duration=dur,
            source_table="sac_calls",
            source_id=r.get("call_id"),
            metadata={"score": r.get("ai_global_score"), "category": classification},
        )


def ingest_kb_emails(registry):
    """Load all emails from kb_emails table."""
    log.info("Ingesting kb_emails...")
    rows = sb_select_all("kb_emails?select=email_msg_id,from_addr,subject,email_date,body_preview,category,intent&order=email_date.desc")
    log.info("  %d email records", len(rows))

    for r in rows:
        from_addr = r.get("from_addr") or ""
        # Extract email from "Name <email>"
        m = re.search(r'<([^>]+)>', from_addr)
        bare_email = m.group(1) if m else from_addr
        email = _norm_email(bare_email)
        if not email:
            continue

        # Extract name
        name = re.sub(r'<[^>]+>', '', from_addr).strip().strip('"') if '<' in from_addr else None

        p = registry.find_or_create(email=email, name=name)
        dt = _parse_dt(r.get("email_date"))

        # Inbound (we received from this person)
        p.total_emails_received += 1
        p.touch_inbound(dt)

        category = r.get("category")
        if category and category not in ("spam", "autre"):
            p.programs.add(category)

        p.add_event(
            event_type="email_inbound",
            dt=dt,
            content=f"{r.get('subject','')}: {r.get('body_preview','')}"[:500],
            direction="inbound",
            source_table="kb_emails",
            source_id=r.get("email_msg_id"),
            metadata={"category": category, "intent": r.get("intent")},
        )


def ingest_payments(registry):
    """Load payment info from google_sheets_sync_log."""
    log.info("Ingesting google_sheets_sync_log (payments)...")
    rows = sb_select_all("google_sheets_sync_log?select=email,name,source_tab,status,contact_id,tag_added_at,run_date&status=in.(tagged,already_tagged,created_and_tagged)&order=run_date.desc")
    log.info("  %d payment records", len(rows))

    for r in rows:
        email = _norm_email(r.get("email"))
        ghl_id = r.get("contact_id")
        if not email and not ghl_id:
            continue

        p = registry.find_or_create(email=email, ghl_id=ghl_id, name=r.get("name"))
        p.has_paid = True
        p.paid_source = "sheet_manual"

        dt = _parse_dt(r.get("tag_added_at"))
        run_dt = _parse_dt(r.get("run_date"))
        paid_dt = dt or run_dt
        if paid_dt and (not p.paid_date or paid_dt.date() < (p.paid_date if hasattr(p.paid_date, 'date') else p.paid_date)):
            p.paid_date = paid_dt.date() if hasattr(paid_dt, 'date') else paid_dt

        # Tag source_tab to program
        tab = r.get("source_tab", "")
        if "MTL" in tab or "QC" in tab:
            p.programs.add("gardiennage")
        if "Anglais" in tab:
            p.programs.add("gardiennage-en")

        if paid_dt:
            p.add_event(
                event_type="payment_confirmed",
                dt=paid_dt,
                content=f"Paid via {tab}",
                direction="internal",
                source_table="google_sheets_sync_log",
                source_id=f"{email}_{r.get('run_date')}",
                metadata={"source_tab": tab},
            )


def ingest_our_sms(registry):
    """Load SMS we sent from hot_sms_sent."""
    log.info("Ingesting hot_sms_sent (our outbound SMS)...")
    rows = sb_select_all("hot_sms_sent?select=phone_number,contact_name,ghl_contact_id,sms_body,status,sent_at&status=in.(sent,would_send)&order=sent_at.desc")
    log.info("  %d our-SMS records", len(rows))

    for r in rows:
        phone = r.get("phone_number")
        if not phone:
            continue
        p = registry.find_or_create(
            phone=phone,
            ghl_id=r.get("ghl_contact_id"),
            name=r.get("contact_name"),
        )
        p.total_sms_sent += 1
        p.times_we_contacted += 1
        dt = _parse_dt(r.get("sent_at"))
        p.touch_outbound(dt)

        if dt and (not p.last_our_sms_at or dt > p.last_our_sms_at):
            p.last_our_sms_at = dt
            p.last_our_sms_body = r.get("sms_body")

        p.add_event(
            event_type="our_sms_sent",
            dt=dt,
            content=r.get("sms_body"),
            direction="outbound",
            source_table="hot_sms_sent",
            source_id=f"{phone}_{dt.isoformat() if dt else ''}",
            metadata={"status": r.get("status")},
        )


# ---------------------------------------------------------------------------
# Write to Supabase
# ---------------------------------------------------------------------------

def upsert_prospects(registry, dry_run=False):
    """Upsert all prospects to the database."""
    log.info("Writing %d prospects...", len(registry.all))
    saved = 0
    for p in registry.all:
        if not (p.phone or p.email or p.ghl_id):
            continue
        d = p.to_dict()
        if dry_run:
            saved += 1
            continue
        # Upsert by the most specific key we have
        if p.phone:
            conflict = "phone_normalized"
        elif p.email:
            conflict = "email_normalized"
        else:
            conflict = "ghl_contact_id"
        try:
            sb_upsert("prospects_intelligence", d, on_conflict=conflict)
            saved += 1
            if saved % 100 == 0:
                log.info("  Saved %d prospects...", saved)
        except Exception as e:
            log.warning("Upsert failed (%s): %s", p.phone or p.email, e)
    log.info("Saved %d prospects total", saved)
    return saved


def insert_timeline(registry, dry_run=False):
    """Insert all timeline events. Needs prospect IDs from DB first."""
    if dry_run:
        total = sum(len(p.events) for p in registry.all)
        log.info("DRY RUN: would insert %d timeline events", total)
        return 0

    log.info("Fetching prospect IDs for timeline linkage...")
    # Map from phone/email to prospect_id
    id_map = {}
    all_rows = sb_select_all("prospects_intelligence?select=id,phone_normalized,email_normalized,ghl_contact_id")
    for r in all_rows:
        pid = r["id"]
        if r.get("phone_normalized"):
            id_map[("phone", r["phone_normalized"])] = pid
        if r.get("email_normalized"):
            id_map[("email", r["email_normalized"])] = pid
        if r.get("ghl_contact_id"):
            id_map[("ghl", r["ghl_contact_id"])] = pid

    # Build timeline rows
    timeline_rows = []
    for p in registry.all:
        pid = None
        if p.phone and ("phone", p.phone) in id_map:
            pid = id_map[("phone", p.phone)]
        elif p.email and ("email", p.email) in id_map:
            pid = id_map[("email", p.email)]
        elif p.ghl_id and ("ghl", p.ghl_id) in id_map:
            pid = id_map[("ghl", p.ghl_id)]
        if not pid:
            continue
        for e in p.events:
            timeline_rows.append({"prospect_id": pid, **e})

    log.info("Inserting %d timeline events...", len(timeline_rows))
    sb_exec_insert("prospects_timeline", timeline_rows)
    return len(timeline_rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("PROSPECTS AGGREGATOR — %s", "DRY RUN" if args.dry_run else "PRODUCTION")
    log.info("=" * 60)

    registry = ProspectRegistry()

    ingest_sac_calls(registry)
    log.info("Registry stats: %s", registry.stats())

    ingest_kb_emails(registry)
    log.info("Registry stats: %s", registry.stats())

    ingest_payments(registry)
    log.info("Registry stats: %s", registry.stats())

    ingest_our_sms(registry)
    log.info("Registry stats: %s", registry.stats())

    if args.limit:
        registry.all = registry.all[:args.limit]
        log.info("Limited to %d prospects for this run", args.limit)

    saved = upsert_prospects(registry, dry_run=args.dry_run)
    timeline_count = insert_timeline(registry, dry_run=args.dry_run)

    log.info("")
    log.info("=" * 60)
    stats = registry.stats()
    log.info("DONE")
    log.info("  Total prospects: %d", stats["total"])
    log.info("  With phone:      %d", stats["with_phone"])
    log.info("  With email:      %d", stats["with_email"])
    log.info("  Paid:            %d", stats["paid"])
    log.info("  Saved:           %d", saved)
    log.info("  Timeline events: %d", timeline_count)
    log.info("=" * 60)


if __name__ == "__main__":
    main()
