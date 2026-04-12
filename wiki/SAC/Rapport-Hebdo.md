---
type: process
project: xguard-coaching
status: active
tags: [sac, rapport, hebdomadaire, opus, docx]
updated: 2026-04-12
---

# Rapport Hebdomadaire SAC

## Script
`sac_weekly_v3.py` — Lundi 07h00

## Process
1. Load transcripts des 7 derniers jours (Lun-Dim precedent)
2. Re-attribution par prenom (rattrape les erreurs du daily)
3. Score Haiku (15s/appel, ~$0.003/appel)
4. Rapport Opus (coaching narratif detaille)
5. Genere 3 DOCX (par agent via Node.js generate_reports_docx.js)
6. Archive transcripts > 30 jours
7. Push coaching_reports + cron_logs dans [[../Infrastructure/Supabase|Supabase]]
8. Email a [[../Personnes/Hamza]] + [[../Personnes/Nick]]

## DOCX
- Chemin: `C:\Users\user\sac_reports\{person}\rapport_semaine_{date}.docx`
- Copie auto vers Google Drive: `G:\Mon Drive\SAC Rapports Coaching\`

## Scoring Haiku vs Regex
| Methode | Vitesse | Precision | Usage |
|---------|---------|-----------|-------|
| Regex (sac_scoring.py) | Instantane | ~60% | Daily |
| Haiku (claude_scoring.py) | 15s/appel | ~90% | Weekly |
| Opus | ~2 min | Narratif | Weekly coaching report |

Voir: [[Rapport-Quotidien]], [[Pipeline-SAC]], [[Scoring-10-Dimensions]]
