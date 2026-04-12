---
type: knowledge-base
project: xguard-coaching
status: active
tags: [kb, faq, email, haiku]
updated: 2026-04-12
---

# Knowledge Base System

## Pipeline
```
IMAP (academie@academiexguard.ca)
  365 jours, 1500/folder
       |
       v
  kb_email_analyzer.py (23h)
  Haiku classifie chaque email
       |
       v
  Supabase (kb_emails: 1185+ rows)
       |
       v
  kb_topic_aggregator.py (06h)
  Merge semantique -> topics canoniques
       |
       v
  Supabase (kb_topics: 18+ rows)
       |
       v
  kb_approval_email.py (07h30)
  Email a Nick avec topics en attente
       |
       v
  Admin Page
  https://nicksoucy.github.io/orgnigram-xguard/kb_admin.html
  Approve / Correct / Reject
```

## Config (sur Nitro)
- MAX_EMAILS_PER_RUN = 2000
- MAX_PER_FOLDER = 1500
- since_days = 365
- CHUNK_SIZE = 30 (aggregateur)
- HAIKU_MERGE_TIMEOUT = 180s

## Categories detectees
inscription (23%), paiement (18%), annulation (16%), info (15%)

## Bug corrige
`call_claude_json` essayait `{` avant `[` pour parser les arrays JSON. **Fix:** essayer `[` en premier.

Voir: [[Stats-KB]], [[../APIs/Gmail-IMAP]], [[../Infrastructure/Crons]]
