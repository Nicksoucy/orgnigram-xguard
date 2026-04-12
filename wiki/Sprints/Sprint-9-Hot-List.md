---
type: sprint
project: xguard-coaching
status: completed
tags: [sprint-9, hot-list, leads]
updated: 2026-04-12
---

# Sprint 9 — Hot List 17h (Close Leads)

**Date:** 12 avril 2026
**Statut:** COMPLETE
**Cron:** XGuard_HotList_17h (17h00 daily sur Nitro)

## Objectif
Email quotidien a 17h avec les top 5 leads a rappeler MAINTENANT, base sur les 3 derniers jours.

## Scoring des leads
| Signal | Points |
|--------|--------|
| SMS paiement/inscription | 10 pts |
| Appel manque | 8 pts |
| Email sans reponse | 7 pts |
| Contact multi-canal (appel+SMS+email) | 15 pts |
| Callback du aujourd'hui | 10 pts |

## Logique
1. Cross-ref JustCall + SMS + emails des 72 dernieres heures
2. Score chaque contact par signaux
3. Rank par probabilite de close
4. Top 5 -> email a [[../Personnes/Hamza]]

## Scripts potentiels
- `hot_leads.py` (existe deja, a completer)
- Cron a 17h00

Voir: [[Sprint-10-39-Indicateurs]], [[../SAC/Pipeline-SAC]]
