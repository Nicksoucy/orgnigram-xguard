---
type: process
project: xguard-coaching
status: active
tags: [sac, email, rapport, quotidien]
updated: 2026-04-12
---

# Rapport Quotidien SAC

## Script
`daily_email_report.py` — appele apres sac_daily_v2.py

## Destinataires
- hmaghraoui65@gmail.com ([[../Personnes/Hamza]])
- nick@darkhorseads.com ([[../Personnes/Nick]])

## Sujet de l'email
`SAC Lundi 2026-04-13 — 78.1/100 — Rapport Quotidien`

## Sections du rapport
1. **Score Qualite /100** — [[39-Indicateurs]] avec barres par dimension + non-rappeles
2. **KPI Cards** — Total appels, repondus, vrais manques, taux reel, transcrits
3. **Analyse des manques** — Doublons retires, agent occupe, vrais manques
4. **Top rappeleurs** — Clients appelant 2+ fois
5. **Performance par plage horaire** — Matin (8-12) vs apres-midi (12-18)
6. **Volume par compte** — Academie vs Formateur
7. **Distribution horaire** — 8h a 18h avec alertes
8. **Appels transcrits + Score IA** — Par agent avec classification
9. **Duree des appels** — Moy, mediane, max, total par agent
10. **Meilleurs appels** — Top 3 avec coaching note
11. **Appels a ameliorer** — Bottom 3 avec coaching note
12. **Distribution qualite** — Excellent/Bon/Moyen/Faible
13. **SMS Stats** — Volume, sans reponse, hot leads
14. **Email Stats** — Recus/envoyes/sans reponse
15. **Conversion Stats** — 30 jours, par pipeline

## Sources de donnees
- `smart_stats.py` — KPIs + 39 indicateurs
- `sms_stats.py` — SMS via JustCall v2.1 API
- `email_stats.py` — IMAP academie@
- `conversion_metrics.py` — Supabase sac_calls
- Supabase `sac_calls` — appels transcrits avec scores IA

Voir: [[Pipeline-SAC]], [[39-Indicateurs]], [[Rapport-Hebdo]]
