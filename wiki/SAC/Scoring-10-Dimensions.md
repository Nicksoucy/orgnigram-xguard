---
type: process
project: xguard-coaching
status: active
tags: [sac, scoring, haiku, regex, dimensions]
updated: 2026-04-12
---

# Scoring IA — 10 Dimensions SAC

## Deux systemes de scoring

### 1. Regex (instantane, sac_scoring.py)
Score 0-10 par detection de mots-cles dans le transcript. ~60% precis.

### 2. Haiku IA (15s/appel, claude_scoring.py)
Scoring contextuel via Claude Haiku. ~90% precis. Utilise pendant le weekly report.

## Les 10 Dimensions

| Dimension | Poids | Ce qu'on mesure |
|-----------|-------|----------------|
| **Accueil** | 1.5x | Bonjour, nom d'entreprise, offre d'aide |
| **Ecoute Active** | 1.5x | Reformulations, acquiescements |
| **Resolution** | 1.5x | Solutions proposees, verifications |
| **Patience** | 1.5x | Base sur la duree de l'appel |
| **Professionnalisme** | 1.5x | Formules de politesse minus langage familier |
| **Vente Subtile** | 1.0x | Offres douces, mentions de valeur |
| **Qualification** | 1.0x | Questions ouvertes, besoins |
| **Gestion Objections** | 1.0x | Ratio phrases de gestion vs objections |
| **Energie** | 0.8x | Mots positifs, points d'exclamation |
| **Engagement** | 0.8x | Questions posees, personnalisation |

Plus 3 dimensions bonus (Haiku seulement):
- **Empathie** (1.2x) — soutien emotionnel, desescalade
- **Connaissance Produit** (1.2x) — mentions formations, prix, certifications
- **Suivi** (1.2x) — engagements de suivi, prochaines etapes

## Score Global
Moyenne ponderee des 10-13 dimensions = score /10 par appel.

> Ne pas confondre avec le [[39-Indicateurs|score /100 des 39 indicateurs]] qui mesure la performance operationnelle (rappels, conformite, etc.), pas la qualite conversationnelle.

## Seuils de qualite
| Niveau | Score | Couleur |
|--------|-------|---------|
| Excellent | >= 7/10 | Vert |
| Bon | 5-7 | Orange |
| Moyen | 3-5 | Jaune |
| Faible | < 3 | Rouge |

Voir: [[39-Indicateurs]], [[Classification-Appels]], [[Pipeline-SAC]]
