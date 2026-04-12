---
type: process
tags: [ventes, heidys, gardiennage, coaching]
status: active
project: xguard-coaching
updated: 2026-04-12
---

# Coaching Heidys Garcia — Formation Gardiennage

## Config
- **Person:** [[../Personnes/Heidys]]
- **Source:** JustCall (garheidys@gmail.com, agent 407715)
- **Cron:** heidys_daily_v3.py (22h00)
- **Scripts:** nitro_heidys_daily.py -> heidys_haiku_patch.py -> heidys_daily_email.py

## Pipeline
1. JustCall fetch (meme API, different agent_id)
2. Download recordings
3. Transcription GPU (Whisper medium CUDA)
4. Score Haiku (8 dimensions ventes)
5. Email quotidien

## Scoring (8 dimensions ventes)
intro, qualification, objections, closing, empathy, energy, duration, engagement

## Bug JustCall important
> `from_datetime` / `to_datetime` sont **ignores** par l'API. Il faut paginer avec `from_date`/`to_date` et filtrer cote client.

## Analyse (398 appels)
- **Forces:** Introduction (7.2), Energie (6.8), Engagement (6.5)
- **Faiblesses:** Closing (3.1), Objections (3.8), Qualification (4.2)
- Top 3 objections: "C'est trop cher", "Je vais reflechir", "Pas le temps"

Voir: [[../Personnes/Heidys]], [[Domingos-Oliveira]], [[../Infrastructure/Crons]]
