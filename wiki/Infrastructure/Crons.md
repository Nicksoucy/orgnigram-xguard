---
type: infrastructure
project: xguard-coaching
status: active
tags:
  - crons
  - nitro
  - scheduling
  - automation
updated: 2026-04-12
---

# Cron Jobs (Production)

Tous les scripts sont sur [[Nitro-GPU]] a `C:\Users\user\crons\`

## Crons Actifs

| Nom | Script | Schedule | Agent(s) |
|-----|--------|----------|----------|
| **XGuard_SAC_Daily_v2** | sac_daily_v2.py | 19h00 daily | [[../Personnes/Hamza\|Hamza]], [[../Personnes/Lilia\|Lilia]], [[../Personnes/Sekou\|Sekou]] |
| **XGuard_SAC_Weekly_v3** | sac_weekly_v3.py | Lundi 07h00 | SAC team |
| **XGuard_Heidys_Daily** | heidys_daily_v3.py | 22h00 daily | [[../Personnes/Heidys\|Heidys]] |
| **XGuard_Domingos_Daily** | domingos_daily_v3.py | 23h30 daily | [[../Personnes/Domingos\|Domingos]] |
| **KB_Analyzer** | kb_email_analyzer.py | 23h00 daily | Emails |
| **KB_Aggregator** | kb_topic_aggregator.py | 06h00 daily | KB |
| **KB_ApprovalEmail** | kb_approval_email.py | 07h30 daily | Nick |
| **XGuard_HotList_17h** | hot_leads.py | 17h00 daily | [[../Personnes/Hamza\|Hamza]] |
| **XGuard_HealthCheck** | health_check.py | 20h00 daily | [[../Personnes/Nick\|Nick]] (alerte email si probleme) |

## Services Permanents
| Nom | Script | Demarrage |
|-----|--------|-----------|
| XGuard_ProgressServer | nitro_progress_server.py | ONLOGON |
| XGuard_Heartbeat | nitro_heartbeat.py | ONLOGON |

**Note:** `XGuard_Watchdog` (nitro_watchdog.py) est DISABLED depuis le 18 avril 2026. Remplace par `XGuard_Heartbeat` (plus simple, pas de catch-up dangereux). Le scheduler APScheduler doublonnait Windows Task Scheduler et causait des bugs ([[../Decisions/index|voir decision log]]).

## Scripts Principaux

### SAC Daily (19h)
1. Fetch 2 comptes JustCall (academie@ + formateur@)
2. [[../SAC/Attribution]] par notes + jour + prenom
3. Download recordings + transcribe GPU (Whisper medium CUDA)
4. [[../SAC/Classification-Appels]] + [[../SAC/Scoring-10-Dimensions]]
5. Smart stats (dedup, agent busy, shifts) — [[../SAC/39-Indicateurs]]
6. SMS stats + Email stats
7. Push Supabase + Email quotidien

### SAC Weekly (Lundi 7h)
1. Score Haiku (15s/appel) sur 7 derniers jours
2. Rapport Opus (coaching narratif)
3. Genere 3 DOCX (par agent)
4. Push coaching_reports + email

### Commande pour creer/modifier un task
```bash
ssh -i C:/Users/nicol/.ssh/id_nitro user@100.109.177.101 "schtasks /Create /TN NomDuTask /TR \"venv_path script_path\" /SC DAILY /ST 19:00 /F"
```

Voir: [[Architecture]], [[../SAC/Pipeline-SAC]]
