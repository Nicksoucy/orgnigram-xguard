---
type: dashboard
project: xguard-coaching
status: active
tags: [dashboard, rapports, coaching]
updated: 2026-04-12
---

# Vue Rapports dans le Dashboard

## URL
https://nicksoucy.github.io/orgnigram-xguard/ (onglet "Rapports")

## Ce qu'elle affiche
- **Score global IA** par agent (grille 4x2)
- Forces et ameliorations
- Top objections
- Call breakdown (plainte/inscription/support/info)
- Historique des cron logs

## Fichiers
- `js/views/reports.js` — rendu de la vue
- `js/db.js` — `dbGetLatestCoachingReport()`, `dbGetCoachingReports()`, `dbGetCronLogs()`
- `js/state.js` — `REPORT_PEOPLE` definit les agents visibles

## Roles
- **admin** — voit tous les agents + cron logs
- **formateur** — voit ses agents
- **agent** — voit ses propres donnees seulement

Voir: [[Organigramme]], [[../SAC/Scoring-10-Dimensions]]
