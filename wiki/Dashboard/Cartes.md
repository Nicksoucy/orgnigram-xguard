---
type: dashboard
project: xguard-coaching
status: active
tags: [dashboard, github-pages, cartes, impression, hiti]
updated: 2026-07-18
---

# Dashboard — Vue Cartes (impression HiTi)

Onglet **🪪 Cartes** de l'organigramme. Transforme les personnes en **cartes d'identite
imprimables** a la taille physique exacte **CR-80** (85,6 × 54 mm), le standard des
imprimantes a cartes HiTi (serie CS).

## Deux sorties (echelle reelle)
- **🖨 Imprimer** — impression navigateur, `@page` verrouille a la taille carte, une carte par page.
- **📄 Export PDF** — un PDF, une carte par page, rasterise a ≥300 dpi (resolution native HiTi).

## Options carte (persistees en localStorage)
- Format: CR-80 (defaut) / CR-79 / Custom (mm)
- Orientation: Paysage / Portrait
- Faces: Recto seul / Recto + verso
- Fond perdu (bleed): 0 / 1 / 2 mm — 1 mm recommande pour l'impression bord a bord HiTi
- Theme: Clair (economise le ruban) / Fonce
- QR: lien profil (`?card=<id>`) ou vCard, URL de base configurable
- Couleur d'accent, date d'emission, toggles departement / programmes / ID

## Fichiers cles
- `js/views/cards.js` — logique de la vue (rendu carte, selection, print, export PDF)
- `css/cards.css` — dimensions physiques en mm + regles `@media print` / `@page`
- `js/vendor/qrcode.js` — generateur QR (MIT, vendore, aucune dependance CDN a l'impression)
- reutilise `html2canvas` + `jsPDF` deja charges par l'app pour le PDF

## Donnees
Source = personnes de l'organigramme (`data` + VP). Avatar a initiales (pas de photos en
base). Pour ajouter des photos: colonne `people.photo_url` + `<img>` dans `_cardFrontHTML`.

## Setup imprimante
Voir le guide complet (pilote, ruban YMCKO, over-the-edge, calibration, depannage):
`docs/HITI_PRINTING.md` a la racine du repo.

Voir: [[Organigramme]], [[../Infrastructure/Supabase]]
