---
type: dashboard
project: xguard-coaching
status: active
tags: [dashboard, github-pages, organigramme]
updated: 2026-04-12
---

# Dashboard — App Organigramme

## URL
https://nicksoucy.github.io/orgnigram-xguard/

## Tech Stack
- Frontend: Vanilla HTML/CSS/JS (pas de build)
- Backend: Supabase (PostgreSQL)
- Hosting: GitHub Pages
- Fonts: DM Sans + Space Mono

## 8 Vues
1. **By Department** (dept.js) — grille par departement
2. **Reporting Hierarchy** (tree.js) — arbre organigramme
3. **Future State** (future.js) — planification
4. **Canvas** (canvas.js) — drag-to-pan, zoom, positions persistees
5. **Tasks & Outcomes** (tasks.js) — board de taches
6. **Rapports** (reports.js) — coaching scores par agent
7. **Horaires** (horaires.js) — gestion des shifts
8. **Schedule** (schedule/) — calendrier multi-mois

## Auth
- Magic link ou JWT via Supabase
- Roles: admin (voit tout + crons), formateur, hr, agent (propres donnees)

## Fichiers cles
- `index.html` — entree unique
- `js/app.js` — logique principale
- `js/db.js` — toutes les queries Supabase
- `js/state.js` — REPORT_PEOPLE definit qui apparait dans sidebar
- `js/views/reports.js` — grille scores 4x2, objections, call breakdown

Voir: [[Rapports-Vue]], [[Horaires]], [[../Infrastructure/Supabase]]
