---
type: process
tags: [ventes, domingos, drone, ghl]
status: active
project: xguard-coaching
updated: 2026-04-12
---

# Coaching Domingos Oliveira — Ventes Drone/Elite

## Config
- **Person:** [[../Personnes/Domingos]]
- **Source:** GoHighLevel (PAS JustCall)
- **Cron:** domingos_daily_v3.py (23h30)
- **Scripts:** nitro_dom_daily.py -> domingos_haiku_patch.py -> domingos_daily_email.py

## Pipeline
1. GHL API: search conversations -> find recordings
2. Download via GHL recording endpoint
3. Transcription GPU
4. Classification: drone / elite / autre
5. Score Haiku (8 dimensions)
6. Email quotidien

## Classification drone/elite
| Type | Mots-cles |
|------|-----------|
| drone | telepilote, vol, aeronef, Transport Canada, certificat |
| elite | gardien, gardiennage, securite, agent, BSP, formation |
| autre | les deux matchent, ou aucun |

## Pipeline GHL (1748 opportunites)
- 43.8% Lost
- 23.5% Contacted
- 17.1% Entente de Paiement
- 3.7% conversion

## GHL Recording Endpoint
```
GET /conversations/messages/{MSG_ID}/locations/{LOCATION_ID}/recording
```
**Attention:** Le format du path est critique.

Voir: [[SOP-Vente-Drone]], [[../Personnes/Domingos]], [[../APIs/GHL]]
