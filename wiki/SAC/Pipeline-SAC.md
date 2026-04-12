---
type: process
project: xguard-coaching
status: active
tags: [sac, pipeline, daily, justcall, whisper]
updated: 2026-04-12
---

# Pipeline SAC — Flux Complet

## Vue d'ensemble
```
JustCall API (2 comptes)
  academie@ (301418) — Hamza + Sekou
  formateur@ (302145) — Lilia
       |
       v
  sac_daily_v2.py (19h00)
       |
       v
  Nitro GPU (Whisper medium CUDA)
  15-25s par appel, ~200-300 appels/jour
       |
       v
  Classification + Scoring
  (regex 10 dimensions + Haiku IA)
       |
       v
  Supabase (sac_calls, coaching_data)
       |
       v
  daily_email_report.py
  Email a Hamza + Nick avec:
  - Score global /100 (39 indicateurs)
  - KPIs, shifts, dedup
  - Top/worst appels
  - SMS + Email stats
       |
       v
  Dashboard GitHub Pages
  https://nicksoucy.github.io/orgnigram-xguard/
```

## Etapes du Daily (sac_daily_v2.py)
1. Fetch JustCall (2 comptes, pagination, 0.5s sleep)
2. Filtre: duration >= 30s ET recording_url present
3. [[Attribution]] par notes + jour + heure
4. Download recordings sur Nitro
5. Transcription faster-whisper (medium, CUDA, fr)
6. Re-attribution par detection prenom dans transcript
7. [[Classification-Appels]] (plainte > inscription > support > info)
8. [[Scoring-10-Dimensions]] (regex)
9. Push Supabase (sac_calls, sac_contacts, coaching_data)
10. Smart stats ([[39-Indicateurs]]) + Email quotidien

## Fiabilite
- Lock file previent les double-runs
- Skip si deja transcrit (idempotent)
- Abort apres 10 echecs consecutifs
- Retry avec backoff sur JustCall API
- Fallback regex si Haiku echoue
- Logs: `C:\Users\user\sac_logs\daily_YYYY-MM-DD.log`
- Check espace disque (min 500MB)

## Chiffres cles (Mars 2026)
- ~200-300 appels bruts/jour en semaine
- Taux de reponse reel: ~35-45%
- Haiku scores moyens: ~4.5/10 (vs regex ~3.5/10)
- Top objection: "deja fait" (434x en mars)

Voir: [[39-Indicateurs]], [[Attribution]], [[Rapport-Quotidien]], [[../Infrastructure/Crons]]
