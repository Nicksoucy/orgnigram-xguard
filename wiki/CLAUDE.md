---
type: config
project: xguard-coaching
status: active
tags: [claude, config, instructions]
updated: 2026-04-12
---

# CLAUDE.md

## Qui je suis
Nicolas Soucy Legault (Nick) — proprio de DarkHorse Ads, j'automatise le coaching IA pour XGuard Academie (centre de formation en securite).

## Projet actif
Systeme de coaching IA automatise pour 5 agents XGuard. Pipeline: JustCall/GHL -> Nitro GPU (Whisper) -> Haiku/Opus scoring -> Supabase -> Dashboard + Email quotidien.

## Structure du vault
- [[wiki/index|Index]] — carte complete du vault
- `wiki/Infrastructure/` — serveurs, GPU, connexions
- `wiki/SAC/` — Service a la clientele (Hamza, Lilia, Sekou)
- `wiki/Ventes/` — Heidys (gardiennage) + Domingos (drone)
- `wiki/APIs/` — JustCall, GHL, Supabase, Gmail
- `wiki/Personnes/` — fiches par personne
- `wiki/Decisions/` — log des decisions techniques
- `wiki/Sprints/` — historique des sprints
- `wiki/Dashboard/` — app organigramme GitHub Pages
- `wiki/KB-System/` — base de connaissances FAQ

## Regles de travail
- Lire le fichier index du dossier pertinent avant de travailler
- JAMAIS transcrire localement — toujours SSH vers Nitro
- Supabase upsert: `?on_conflict=` dans l'URL + `Prefer: resolution=merge-duplicates`
- JustCall API: `from_datetime/to_datetime` sont ignores — paginer et filtrer cote client

## Contexte actif
Sprint 10 complete (39 indicateurs de Hamza). Prochains: Sprint 11 (fixes daily report), Sprint 9 (Hot List 17h).
