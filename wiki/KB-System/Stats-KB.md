---
type: knowledge-base
project: xguard-coaching
status: active
tags: [kb, stats, emails]
updated: 2026-04-12
---

# Stats Knowledge Base

## Etat actuel (7 avril 2026)
- **Emails analyses:** 1185+
- **Topics canoniques:** 18
- **Source:** 272,096 emails dans academie@

## Top categories
| Categorie | % |
|-----------|---|
| inscription | 23% |
| paiement | 18% |
| annulation | 16% |
| info | 15% |
| autre | 28% |

## Crons actifs
| Script | Schedule | Role |
|--------|----------|------|
| kb_email_analyzer.py | 23h | Analyse IMAP -> Haiku -> kb_emails |
| kb_topic_aggregator.py | 06h | Merge singletons -> topics canoniques |
| kb_approval_email.py | 07h30 | Email d'approbation a Nick |

Voir: [[Architecture-KB]], [[../Infrastructure/Crons]]
