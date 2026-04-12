---
type: infrastructure
project: xguard-coaching
status: active
tags:
  - supabase
  - database
  - tables
  - upsert
updated: 2026-04-12
---

# Supabase

## Connexion
- **URL:** `https://ctjsdpfegpsfpwjgusyi.supabase.co`
- **Anon Key:** `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN0anNkcGZlZ3BzZnB3amd1c3lpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzM2MDU2NDQsImV4cCI6MjA4OTE4MTY0NH0.Uv2pbxbmvcbXhyDa7Y_M0HqkLuV7uJaNxl1N01q5wMo`

## Tables Coaching
| Table | Rows | Cle unique | Contenu |
|-------|------|-----------|---------|
| sac_calls | ~2700+ | call_id | Chaque appel SAC avec transcript + scores |
| sac_contacts | ~1200+ | contact_number | Contacts uniques, suivi repetitions |
| sac_coaching_metrics | 12+ | person_id + period | Rollups hebdo/mensuel |
| sac_coaching_actions | var | — | Recommandations coaching |
| sac_objections | var | — | Objections normalisees |
| coaching_data | var | person_id + sync_date | Resumes quotidiens |
| coaching_reports | var | person_id + week_start | Rapports hebdomadaires |
| nitro_status | 3 | person_id + task_type | Progression live transcription |
| cron_logs | var | — | Historique d'execution |

## Tables KB
| Table | Rows | Contenu |
|-------|------|---------|
| kb_emails | 1185+ | Emails analyses par Haiku |
| kb_topics | 18+ | Topics FAQ canoniques |
| kb_approvals | var | Audit log immutable |
| kb_run_log | var | Monitoring operationnel |

## Tables Dashboard
departments, people, tasks, canvas_order, shifts, shift_patterns

## Pattern Upsert (CRITIQUE)
```python
url = f"{SUPABASE_URL}/rest/v1/{table}?on_conflict={on_conflict}"
headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}
requests.post(url, json=data, headers=headers)
```
> **`?on_conflict=`** dans l'URL est OBLIGATOIRE sinon erreur 409.

## Person IDs
| ID | Personne |
|----|----------|
| L3 | [[../Personnes/Hamza]] |
| s2 | [[../Personnes/Lilia]] |
| s3 | [[../Personnes/Sekou]] |
| v1 | [[../Personnes/Heidys]] |
| t11 | [[../Personnes/Domingos]] |
| L2 | Mitchell Skelton (admin) |
| r1 | Banji (recrutement) |

Voir: [[Architecture]], [[Crons]], [[../SAC/Pipeline-SAC]]
