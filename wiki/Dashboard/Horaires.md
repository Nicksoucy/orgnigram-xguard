---
type: dashboard
project: xguard-coaching
status: active
tags: [dashboard, horaires, shifts]
updated: 2026-04-12
---

# Horaires — Gestion des Shifts

## Vues
- **Grid View** — jours x personnes
- **Week View** — calendrier semaine avec drag-and-drop
- **Multi-Month** — planification long terme
- **Trainer View** — capacite/disponibilite formateurs

## Fichiers
- `js/views/horaires.js` — vue principale
- `js/views/schedule/` — 11 sous-modules (gridView, weekView, multiMonthView, etc.)
- `css/schedule.css` — styles specifiques

## Tables Supabase
- `shifts` — definitions et assignations
- `shift_patterns` — patterns repetitifs
- `trainer_availability` — capacite formateurs
- `cohort_schedules` — dates de cohortes

Voir: [[Organigramme]], [[../Infrastructure/Supabase]]
