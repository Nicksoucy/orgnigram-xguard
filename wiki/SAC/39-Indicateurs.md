---
type: process
project: xguard-coaching
status: active
tags: [sac, indicateurs, hamza, score, qualite]
updated: 2026-04-12
---

# 39 Indicateurs de Hamza (Score /100)

Sprint 10 — implemente 2026-04-12.

## Score Global
Formule ponderee sur 7 dimensions. Chaque indicateur est score 0-10 vs son standard, moyenne par dimension, puis somme ponderee = score /100.

## Dimensions et Poids

| # | Dimension | Poids | Indicateurs |
|---|-----------|-------|-------------|
| 1 | Volume & Activite | 0% (suivi) | 1-7 |
| 2 | Reponse & Disponibilite | **25%** | 8-14 |
| 3 | Taux de Rappel | **25%** | 15-21 |
| 4 | Qualite de Traitement | **20%** | 22-27 |
| 5 | File d'Attente & Saturation | **8%** | 28-33 |
| 6 | Conformite & Tracabilite | **10%** | 34-37 |
| 7 | Efficacite & Charge | **12%** | 38-41 |

## Dim 1: Volume & Activite (suivi)
| # | Indicateur | Standard |
|---|-----------|----------|
| 1 | Appels bruts | Suivi |
| 2 | Contacts uniques (dedup par numero+jour+direction) | Suivi |
| 3 | Doublons exclus | Suivi |
| 4 | Appels en double 2+ meme jour | <15% |
| 5 | Appels entrants | Suivi |
| 6 | Appels sortants | Suivi |
| 7 | Rappels rapides <10 min (client re-appelle) | <20% |

## Dim 2: Reponse & Disponibilite (x25%)
| # | Indicateur | Standard |
|---|-----------|----------|
| 8 | Taux reponse brut | >75% |
| 9 | Disponibilite reelle (exclut busy+abandons) | >90% |
| 10 | Taux reponse entrant (contacts uniques) | >70% |
| 11 | Taux connexion sortant | >80% |
| 12 | Busy miss (agent deja en appel) | Contexte |
| 13 | Manques agent libre (missed_call_type=1) | <50/mois |
| 14 | Abandons avant sonnerie (missed_call_type=3) | Contexte |

## Dim 3: Taux de Rappel (x25%)
| # | Indicateur | Standard |
|---|-----------|----------|
| 15 | Taux de rappel corrige (manque -> rappel >10s) | >95% |
| 16 | Rappeles meme shift | Priorite 1 |
| 17 | Rappeles shift suivant | Priorite 2 |
| 18 | Non rappeles nets (liste nominative) | =0 |
| 19 | Manques non rappeles fin de journee | =0 |
| 20 | Delai moyen avant rappel | <60 min |
| 21 | Taux rappel dans l'heure | >70% |

## Dim 4: Qualite de Traitement (x20%)
| # | Indicateur | Standard |
|---|-----------|----------|
| 22 | Duree moyenne appel | 60-600s |
| 23 | Duree dans cible 60-600s | >80% |
| 24 | Taux d'occupation (talk time / heures) | 40-70% |
| 25 | Taux callback honore (IVR) | >95% — N/A API |
| 26 | Capacite theorique max (3600/duree_moy) | Reference |
| 27 | Nb tentatives avant traitement | <2 |

## Dim 5: File d'Attente (x8%)
| # | Indicateur | Standard |
|---|-----------|----------|
| 28-31 | Attente file, % file, raccroches, >60s | N/A — pas dans API |
| 32 | Saturation file (rappels rapides/total) | <30% |
| 33 | Facteur rush horaire (peak/avg) | <1.5x |

## Dim 6: Conformite (x10%)
| # | Indicateur | Standard |
|---|-----------|----------|
| 34 | Conformite signature (hm/lilia/sk dans notes) | >95% |
| 35 | Dossiers deja traites | <1% |
| 36 | Notes avec motif documente | >20% |
| 37 | Contacts recurrents multi-jours | <10% — weekly only |

## Dim 7: Efficacite (x12%)
| # | Indicateur | Standard |
|---|-----------|----------|
| 38 | Productivite horaire | Suivi |
| 39 | Taux utilisation capacite | 40-70% |
| 40 | Jours sans non-rappeles | >90% |
| 41 | Taux rappel dans l'heure (=21) | >70% |

## Implementation
- **Script:** `smart_stats.py` (v2) — `compute_39_indicators()` + `compute_weighted_score()`
- **Email:** `daily_email_report.py` — section score /100 avec barres visuelles
- **missed_call_type:** Disponible dans API JustCall (1=no answer, 2=busy, 3=abandoned)
- **queue_wait_time / call_traits:** PAS dans API — necessite CSV export

## Resultats (11 avril 2026)
Score global: **78.1/100**

Voir: [[Pipeline-SAC]], [[Scoring-10-Dimensions]], [[Rapport-Quotidien]]
