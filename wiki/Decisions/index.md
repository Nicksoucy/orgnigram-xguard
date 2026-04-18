---
type: decision
project: xguard-coaching
status: active
tags: [decisions, log, technique]
updated: 2026-04-12
---

# Log des Decisions Techniques

## 2026-04-18 — nitro_watchdog.py remplace par nitro_heartbeat.py
**Probleme:** Le watchdog (400 lignes) avait 2 bugs graves:
1. Son SCHEDULE table hardcode duplicait Windows Task Scheduler avec des horaires differents
2. Sa logique de catch-up "est-ce que ca a tourne aujourd'hui depuis 00:00 UTC" declenchait des re-runs le matin car le run de 19h EDT log a 23:49 UTC (la veille en local, le jour meme en UTC — piege timezone)

**Consequence:** Le 18 avril 8h20, le watchdog a lance sac_daily_v2.py alors que la journee venait de commencer. Rapport envoye a Hamza avec 5 appels de Sekou en 20 minutes, comme si c'etait une journee complete.

**Decision:** Remplacer par `nitro_heartbeat.py` (~130 lignes) qui fait SEULEMENT le heartbeat. Windows Task Scheduler devient la seule source de verite pour les crons.

**Perdu:** Catch-up automatique, GPU mutex, retry logic.
**Garde:** Heartbeat toutes les 5 min avec snapshot des scheduled tasks (pour le dashboard).

**Safety net ajoute:** `sac_daily_v2.py` refuse maintenant d'envoyer un email si l'heure locale est < 17h (evite les rapports partiels).

## 2026-04-14 — Auto-reply mis en pause (reponses trop generiques)
**Decision:** Le premier essai d'auto-reply (`auto_reply_drafts.py`) a genere des drafts techniquement corrects mais **trop generiques**. Les reponses ne contiennent pas les vrais liens Stripe, instructions Interac exactes, ou formules specifiques qu'Hamza utilise.

**Cause:** Le systeme KB analyse seulement les emails RECUS, pas les REPONSES d'Hamza. Les `suggested_response` sont inventees par Haiku sans contexte reel.

**Plan pour reprendre:** [[../Sprints/Sprint-13-Auto-Reply-Real-Context]] — analyser 500+ vraies reponses d'Hamza pour extraire liens, payment info, et templates reels avant de re-deployer l'auto-reply.

**Status:** Code deploye sur Nitro mais **pas de cron actif**. A reprendre quand on aura le temps de bien faire l'extraction.

## 2026-04-12 — missed_call_type dans l'API JustCall
L'API retourne bien `missed_call_type`: 1=no answer (agent libre), 2=busy, 3=abandoned (client raccroche). Permet de calculer la [[../SAC/39-Indicateurs|disponibilite reelle]] exacte au lieu de l'approximation par busy-windows.
**Impact:** Disponibilite reelle passe de 75% (approxime) a 97.1% (precis) car la plupart des manques sont type 3 (abandons).

## 2026-04-12 — queue_wait_time absent de l'API
Les champs `queue_wait_time` et `call_traits` ne sont PAS retournes par l'API JustCall (disponibles uniquement dans CSV export). Les indicateurs 25, 28-31 restent N/A pour l'instant.

## 2026-04-06 — Filtre 8h-18h pour stats SAC
On exclut les appels avant 8h et apres 18h des stats car aucun agent ne travaille a ces heures. Les appels hors-heures sont comptes separement dans le rapport.

## 2026-04-06 — Haiku pour scoring quotidien, Opus pour weekly
Haiku est 15s/appel (~$0.003), utilise pour le scoring quotidien rapide. Opus est plus lent mais produit des rapports narratifs de coaching — reserve au weekly.

## 2026-03-27 — Architecture 2 machines
Decision de separer: PC local (orchestration) et Nitro (GPU transcription). Raison: le PC local a un AMD Radeon sans CUDA, la transcription Whisper necessite NVIDIA.

Voir: [[../Sprints/index]]
