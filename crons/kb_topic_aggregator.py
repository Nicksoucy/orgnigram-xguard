#!/usr/bin/env python3
"""
KB Topic Aggregator — Daily cron (06h) on Nitro.
Reads kb_emails, groups by faq_topic, uses Haiku to semantically
merge similar topics into canonical kb_topics.

Cost: 1 Haiku call per run (sends full topic list for merge).
Incremental: only processes unmapped topics after first run.
"""

import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from kb_config import sb_upsert, sb_get, sb_patch, sb_count
from claude_scoring import call_claude_json

os.environ["CLAUDE_CODE_GIT_BASH_PATH"] = r"C:\Program Files\Git\bin\bash.exe"

LOG_DIR = Path(r"C:\Users\user\sac_logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(str(LOG_DIR / f"kb_aggregator_{datetime.now():%Y-%m-%d}.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger("kb_aggregator")


MERGE_PROMPT = """Tu es un expert en service a la clientele de l'Academie XGuard (formation gardiennage/securite au Quebec).

Voici {n_topics} sujets FAQ extraits de {n_emails} emails clients. Certains sujets sont similaires et doivent etre regroupes.

Regroupe les sujets similaires en topics canoniques. Pour chaque group:

SUJETS A REGROUPER:
{topics_list}

Reponds UNIQUEMENT en JSON (array):
[
  {{
    "topic_id": "slug-kebab-case (ex: inscription-en-ligne)",
    "category": "inscription|info|paiement|plainte|annulation|changement_date|certificat|emploi|technique|autre",
    "topic_label": "Libelle lisible (ex: Inscription en ligne)",
    "question_pattern": "Question type du client (ex: Comment s'inscrire a la formation?)",
    "suggested_response": "Reponse suggeree complete (2-3 phrases, professionnelle, avec info utile)",
    "merged_raw_topics": ["sujet1", "sujet2", ...]
  }},
  ...
]

REGLES:
- Chaque sujet brut doit apparaitre dans exactement UN group
- Maximum 50 topics canoniques (fusionne les petits sujets similaires)
- Le topic_id doit etre unique, en kebab-case, sans accents
- La suggested_response doit etre utile et specifique a XGuard
- Si un sujet est "spam" ou non pertinent, mets-le dans un group "autre"
"""


def get_raw_topic_counts():
    """Get all raw faq_topic values with their counts from kb_emails."""
    # Supabase doesn't support GROUP BY via REST, so we fetch all and aggregate in Python
    topics = {}
    offset = 0
    page_size = 1000
    while True:
        rows = sb_get(f"kb_emails?select=faq_topic,category&offset={offset}&limit={page_size}")
        if not rows:
            break
        for r in rows:
            t = r.get("faq_topic") or "autre"
            cat = r.get("category") or "autre"
            if t not in topics:
                topics[t] = {"count": 0, "categories": {}}
            topics[t]["count"] += 1
            topics[t]["categories"][cat] = topics[t]["categories"].get(cat, 0) + 1
        if len(rows) < page_size:
            break
        offset += page_size

    return topics


def get_existing_topic_mappings():
    """Get existing topic_id assignments from kb_topics."""
    rows = sb_get("kb_topics?select=topic_id,merged_raw_topics")
    mappings = {}
    for r in rows:
        tid = r.get("topic_id", "")
        for raw in (r.get("merged_raw_topics") or []):
            mappings[raw] = tid
    return mappings


def get_example_emails_for_topics(raw_topics, limit=3):
    """Get example emails for a set of raw topics."""
    # Build filter for multiple topics
    examples = []
    for topic in raw_topics[:3]:  # Check top 3 raw topics
        rows = sb_get(
            f"kb_emails?faq_topic=eq.{topic}&select=subject,from_addr,body_preview,email_date"
            f"&order=email_date.desc&limit={limit}"
        )
        examples.extend(rows)
    return examples[:limit]


CHUNK_SIZE = 80  # Max topics per Haiku call
HAIKU_MERGE_TIMEOUT = 180  # 3 min per chunk


def merge_topics_with_haiku(raw_topics):
    """Send raw topics to Haiku for semantic merge in batches. Returns list of canonical topics."""
    # Sort by frequency desc — process the most common first
    sorted_topics = sorted(raw_topics.items(), key=lambda x: -x[1]["count"])

    # Pre-filter: group singletons (count=1) into a catch-all to reduce volume
    significant = {}
    singleton_cats = {}
    for topic, data in sorted_topics:
        if data["count"] >= 2:
            significant[topic] = data
        else:
            # Group singletons by their top category
            top_cat = max(data["categories"], key=data["categories"].get) if data["categories"] else "autre"
            if top_cat not in singleton_cats:
                singleton_cats[top_cat] = {"count": 0, "categories": {}}
            singleton_cats[top_cat]["count"] += data["count"]
            singleton_cats[top_cat]["categories"][top_cat] = singleton_cats[top_cat]["categories"].get(top_cat, 0) + 1

    # Add singleton groups as "divers - {category}"
    for cat, data in singleton_cats.items():
        key = f"divers - {cat} (sujets uniques)"
        significant[key] = data

    log.info("Pre-filter: %d significant topics (from %d raw, %d singletons grouped)",
             len(significant), len(raw_topics), len(raw_topics) - len(significant) + len(singleton_cats))

    # Chunk the significant topics
    topic_items = list(sorted(significant.items(), key=lambda x: -x[1]["count"]))
    all_canonical = []

    for chunk_start in range(0, len(topic_items), CHUNK_SIZE):
        chunk = dict(topic_items[chunk_start:chunk_start + CHUNK_SIZE])
        total_in_chunk = sum(t["count"] for t in chunk.values())

        lines = []
        for i, (topic, data) in enumerate(sorted(chunk.items(), key=lambda x: -x[1]["count"]), 1):
            top_cat = max(data["categories"], key=data["categories"].get) if data["categories"] else "autre"
            lines.append(f'{i}. "{topic}" ({data["count"]}x, category: {top_cat})')

        topics_text = "\n".join(lines)

        prompt = MERGE_PROMPT.format(
            n_topics=len(chunk),
            n_emails=total_in_chunk,
            topics_list=topics_text,
        )

        chunk_num = chunk_start // CHUNK_SIZE + 1
        total_chunks = (len(topic_items) + CHUNK_SIZE - 1) // CHUNK_SIZE
        log.info("Chunk %d/%d: %d topics (%d emails) -> Haiku...",
                 chunk_num, total_chunks, len(chunk), total_in_chunk)

        result = call_claude_json(prompt, model="haiku", timeout=HAIKU_MERGE_TIMEOUT)

        if isinstance(result, list):
            log.info("  Haiku returned %d canonical topics", len(result))
            all_canonical.extend(result)
        elif isinstance(result, dict):
            # Try common keys
            for key in ("topics", "canonical_topics", "result"):
                if key in result and isinstance(result[key], list):
                    log.info("  Haiku returned %d canonical topics (key: %s)", len(result[key]), key)
                    all_canonical.extend(result[key])
                    break
            else:
                log.warning("  Unexpected Haiku dict response, skipping chunk")
        else:
            log.warning("  Haiku returned %s, skipping chunk", type(result))

        # Small pause between chunks
        if chunk_start + CHUNK_SIZE < len(topic_items):
            import time
            time.sleep(5)

    log.info("Total canonical topics from all chunks: %d", len(all_canonical))
    return all_canonical


def main():
    log.info("=" * 60)
    log.info("KB TOPIC AGGREGATOR — %s", datetime.now().strftime("%Y-%m-%d %H:%M"))
    log.info("=" * 60)

    # Check how many emails we have
    total_emails = sb_count("kb_emails")
    if total_emails == 0:
        log.info("No emails in kb_emails yet. Waiting for analyzer to run.")
        return

    log.info("Total emails in kb_emails: %d", total_emails)

    # Get raw topic counts
    raw_topics = get_raw_topic_counts()
    log.info("Found %d unique raw faq_topics", len(raw_topics))

    if not raw_topics:
        log.info("No topics to aggregate.")
        return

    # Check which are already mapped
    existing_mappings = get_existing_topic_mappings()
    unmapped = {k: v for k, v in raw_topics.items() if k not in existing_mappings}
    log.info("Already mapped: %d, Unmapped: %d", len(raw_topics) - len(unmapped), len(unmapped))

    # Decide what to send to Haiku
    if not unmapped and len(existing_mappings) > 0:
        log.info("All topics already mapped. Updating frequencies only.")
        # Just update frequencies on existing topics
        topics_rows = sb_get("kb_topics?select=topic_id,merged_raw_topics")
        for tr in topics_rows:
            tid = tr["topic_id"]
            merged = tr.get("merged_raw_topics") or []
            freq = sum(raw_topics.get(rt, {}).get("count", 0) for rt in merged)
            if freq > 0:
                sb_patch("kb_topics", f"topic_id=eq.{tid}", {
                    "frequency": freq,
                    "last_seen": datetime.utcnow().isoformat() + "Z",
                })
        log.info("Frequencies updated.")
        return

    # Full merge: send ALL topics (not just unmapped) for best grouping
    # But if we have existing approved topics, only merge unmapped ones
    existing_approved = sb_get("kb_topics?select=topic_id&approval_status=in.(approved,corrected)")
    if existing_approved and unmapped:
        # Incremental: only merge unmapped topics
        topics_to_merge = unmapped
        log.info("Incremental merge: %d unmapped topics", len(topics_to_merge))
    else:
        # Full merge
        topics_to_merge = raw_topics
        log.info("Full merge: %d topics", len(topics_to_merge))

    # Call Haiku for semantic merge
    canonical = merge_topics_with_haiku(topics_to_merge)

    if not canonical:
        log.warning("Haiku returned no canonical topics!")
        return

    # Upsert canonical topics to kb_topics
    topics_created = 0
    topics_updated = 0

    for ct in canonical:
        tid = ct.get("topic_id", "").strip()
        if not tid:
            continue

        merged_raw = ct.get("merged_raw_topics", [])
        freq = sum(raw_topics.get(rt, {}).get("count", 0) for rt in merged_raw)

        # Get example emails
        examples = get_example_emails_for_topics(merged_raw, limit=3)

        # Get top 5 subjects
        example_subjects = []
        for rt in merged_raw[:5]:
            rows = sb_get(f"kb_emails?faq_topic=eq.{rt}&select=subject&order=email_date.desc&limit=2")
            for r in rows:
                s = r.get("subject", "")
                if s and s not in example_subjects:
                    example_subjects.append(s)
                    if len(example_subjects) >= 5:
                        break
            if len(example_subjects) >= 5:
                break

        row = {
            "topic_id": tid,
            "category": ct.get("category", "autre"),
            "topic_label": ct.get("topic_label", tid),
            "question_pattern": ct.get("question_pattern", ""),
            "suggested_response": ct.get("suggested_response", ""),
            "frequency": freq,
            "example_subjects": example_subjects,
            "example_emails": json.dumps(examples, ensure_ascii=False) if examples else None,
            "merged_raw_topics": merged_raw,
            "last_seen": datetime.utcnow().isoformat() + "Z",
            "last_aggregated": datetime.utcnow().isoformat() + "Z",
        }

        # Check if exists (don't overwrite approved topics)
        existing = sb_get(f"kb_topics?topic_id=eq.{tid}&select=topic_id,approval_status")
        if existing and existing[0].get("approval_status") in ("approved", "corrected"):
            # Only update frequency and examples, not the response
            sb_patch("kb_topics", f"topic_id=eq.{tid}", {
                "frequency": freq,
                "example_subjects": example_subjects,
                "example_emails": json.dumps(examples, ensure_ascii=False) if examples else None,
                "last_seen": datetime.utcnow().isoformat() + "Z",
                "last_aggregated": datetime.utcnow().isoformat() + "Z",
            })
            topics_updated += 1
        else:
            sb_upsert("kb_topics", row, on_conflict="topic_id")
            topics_created += 1

        # Update kb_emails with topic_id
        for rt in merged_raw:
            sb_patch("kb_emails", f"faq_topic=eq.{rt}&topic_id=is.null", {"topic_id": tid})

        log.info("  %s: %s (%dx, %d raw topics)", tid, ct.get("topic_label", ""), freq, len(merged_raw))

    log.info("")
    log.info("=" * 60)
    log.info("DONE — %d created, %d updated, %d total canonical topics",
             topics_created, topics_updated, sb_count("kb_topics"))
    log.info("=" * 60)

    # Log run
    sb_upsert("kb_run_log", {
        "script": "kb_topic_aggregator",
        "batch_id": f"agg_{datetime.now():%Y%m%d}",
        "status": "completed",
        "finished_at": datetime.utcnow().isoformat() + "Z",
        "emails_analyzed": total_emails,
        "topics_created": topics_created,
        "topics_updated": topics_updated,
    })


if __name__ == "__main__":
    main()
