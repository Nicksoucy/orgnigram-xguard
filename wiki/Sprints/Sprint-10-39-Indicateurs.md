---
type: sprint
project: xguard-coaching
status: completed
tags: [sprint-10, indicateurs, hamza, score]
updated: 2026-04-12
---

# Sprint 10 — 39 Indicateurs de Hamza

**Date:** 12 avril 2026
**Statut:** COMPLETE

## Objectif
Aligner le rapport quotidien automatise avec le framework 39 indicateurs de [[../Personnes/Hamza]], 7 dimensions ponderees = score /100.

## Ce qui a ete construit
1. `compute_callback_stats()` — tracking des rappels (manque -> callback meme numero >10s)
2. `compute_39_indicators()` — tous les indicateurs depuis les donnees JustCall
3. `compute_weighted_score()` — score /100 avec poids par dimension
4. `missed_call_type` extrait de l'API (1=no answer, 2=busy, 3=abandoned)
5. Section score dans daily_email_report.py (barres visuelles + non-rappeles)
6. Score dans le sujet de l'email: "SAC Lundi — 78.1/100 — Rapport Quotidien"

## Fichiers modifies
- `smart_stats.py` — v2 avec 39 indicateurs
- `daily_email_report.py` — section score + sujet

## Resultat test (11 avril)
Score: **78.1/100**

## Decouvertes API
- `missed_call_type`: DISPONIBLE (valeurs 1, 2, 3)
- `queue_wait_time`: PAS disponible (CSV seulement)
- `call_traits`: PAS disponible (CSV seulement)

Voir: [[../SAC/39-Indicateurs]], [[../Decisions/index]]
