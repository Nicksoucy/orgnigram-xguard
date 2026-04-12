---
type: decision
project: xguard-coaching
status: active
tags: [decisions, log, technique]
updated: 2026-04-12
---

# Log des Decisions Techniques

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
