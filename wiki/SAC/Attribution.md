---
type: process
project: xguard-coaching
status: active
tags: [sac, attribution, hamza, lilia, sekou]
updated: 2026-04-12
---

# Attribution des appels (Hamza/Lilia/Sekou)

## Probleme
[[../Personnes/Hamza|Hamza]] et [[../Personnes/Sekou|Sekou]] partagent le meme compte JustCall (academie@ 301418). [[../Personnes/Lilia|Lilia]] se connecte aussi sur academie@ entre 16-18h.

## Methode d'attribution (3 niveaux)

### 1. Pre-transcription: Notes JustCall
Le champ `notes` contient la signature de l'agent:
- `hm` ou `hamza` -> Hamza
- `lilia` ou `lilya` -> Lilia
- `sk` ou `sekou` ou `secoudé` -> Sekou

### 2. Pre-transcription: Jour et heure
Si pas de signature dans les notes:
- **Semaine (lun-ven):** academie@ = Hamza, formateur@ = Lilia
- **Weekend (sam-dim):** academie@ = Sekou
- **16h-18h semaine:** Lilia possible sur academie@ (overlap)

### 3. Post-transcription: Detection du prenom
Analyse les 150 premiers mots du transcript pour les prenoms:
- Patterns: sekou, secoudé, sécoudé + "sk" dans notes
- Patterns: hamza, amjad
- Patterns: lilia, lilya, lillian

## Horaires de travail
| Agent | Plage | Jours | Compte |
|-------|-------|-------|--------|
| Hamza | 8h-12h (parfois 16h) | Lun-Ven | academie@ |
| Lilia | 12h-18h | Lun-Ven | formateur@ + academie@ 16-18h |
| Sekou | 8h-17h | Sam-Dim | academie@ |

Voir: [[Pipeline-SAC]], [[../Personnes/Hamza]], [[../Personnes/Lilia]], [[../Personnes/Sekou]]
