---
type: process
project: xguard-coaching
status: active
tags: [sac, classification, categories]
updated: 2026-04-12
---

# Classification des appels SAC

## Ordre de priorite
Si plusieurs categories matchent, la plus haute gagne:
1. **plainte** (priorite max)
2. **inscription**
3. **support**
4. **info**
5. **autre** (defaut)

## Mots-cles par categorie

| Categorie | Mots-cles (regex, case-insensitive) |
|-----------|-------------------------------------|
| plainte | plainte, mecontent, insatisfait, rembours, annuler, annulation, decu, inacceptable |
| inscription | inscrire, inscription, formation, cours, session, programme, gardiennage, securite, bsp, secourisme |
| support | probleme, aide, fonctionne pas, ne marche pas, erreur, bug, technique, acces, mot de passe, connexion |
| info | information, renseignement, question, comment, combien, prix, tarif, horaire, cout, frais |
| autre | Defaut quand 0 match |

## Stats (Mars 2026)
- inscription: ~23%
- info: ~15%
- support: variable
- plainte: rare mais prioritaire

## Implementation
Script: `sac_scoring.py` fonction `classify_call(transcript)`

Voir: [[Scoring-10-Dimensions]], [[Pipeline-SAC]]
