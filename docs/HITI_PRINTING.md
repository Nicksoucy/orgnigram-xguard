# Impression de cartes — HiTi (CS-series) — Guide de démarrage

Ce guide couvre tout ce qu'il faut pour **imprimer des cartes d'identité XGuard** à
partir de l'organigramme, sur une imprimante à cartes **HiTi** (série CS : CS-200e /
CS-220e / CS-290 / CS-320…).

L'app génère des cartes à la **taille physique exacte CR-80** (85,6 × 54 mm, format
carte de crédit / ISO&nbsp;7810 ID-1) — le standard de toutes les imprimantes à cartes
HiTi CS. Deux façons d'imprimer, toutes deux à l'échelle réelle :

| Bouton | Ce que ça fait | Quand l'utiliser |
|---|---|---|
| **🖨 Imprimer** | Envoie les cartes au navigateur (Ctrl+P), **une carte par page** | Impression directe sur la HiTi |
| **📄 Export PDF** | Génère un PDF, **une carte par page**, rendu à ≥300 dpi | Archiver, envoyer, ou imprimer plus tard |

> ⚠️ L'installation du **pilote HiTi** se fait sur le poste Windows/Mac **physiquement
> relié** à l'imprimante (USB/réseau). Ça ne peut pas être fait depuis l'app web — mais
> les étapes exactes sont ci-dessous.

---

## 1. Matériel et consommables

- **Imprimante** : HiTi CS-200e, CS-220e, CS-290 ou CS-320 (impression directe sur carte, 300 dpi).
- **Cartes vierges** : PVC **CR-80**, 85,6 × 54 mm, épaisseur 30 mil (0,76 mm). Standard.
- **Ruban / ribbon** : cartouche HiTi **YMCKO** (couleur recto + panneau noir + vernis).
  Une carte recto = 1 image YMCKO. Recto/verso = 2 images (prévoir un ruban qui en a assez).
- (Optionnel recto-verso automatique) : modèle **CS-290/CS-320** avec module double face.

---

## 2. Installer le pilote HiTi

### Windows
1. Télécharger le pilote de votre modèle depuis le site HiTi
   (**Support → Downloads → Card Printers → CS-2xx / CS-3xx**), ex. `CS-200e Driver`.
2. Lancer l'installateur, brancher l'imprimante en USB quand demandé, terminer.
3. **Panneau de configuration → Périphériques et imprimantes** → l'imprimante HiTi apparaît.

### macOS
1. Télécharger le pilote macOS HiTi pour votre modèle.
2. Installer le `.pkg`, brancher l'imprimante.
3. **Réglages Système → Imprimantes et scanners** → **Ajouter** → sélectionner la HiTi.

> 💡 Pas d'internet sur le poste d'impression&nbsp;? Récupérer l'installateur sur une clé USB.
> Le pilote HiTi est aussi souvent fourni sur le CD/clé livré avec l'imprimante.

---

## 3. Configurer le pilote (une seule fois)

Ouvrir **Préférences d'impression** du pilote HiTi et régler :

| Réglage | Valeur |
|---|---|
| Type de ruban / Ribbon | **YMCKO** (auto-détecté en général) |
| Taille de carte / Card size | **CR-80 (85,6 × 54 mm)** |
| Orientation | **Paysage** (Landscape) — défaut des cartes de l'app |
| Impression pleine page / **Over-the-edge** | **Activé** ⬅️ essentiel pour imprimer bord à bord sans liseré blanc |
| Recto-verso / Duplex | **Activé** seulement pour un modèle double face + option « Recto+verso » dans l'app |
| Qualité | Standard / 300 dpi |

Enregistrer comme réglages par défaut.

---

## 4. Imprimer depuis l'app

1. Ouvrir l'organigramme → onglet **🪪 Cartes**.
2. Cocher les personnes à imprimer (bouton **tous** par département, ou **Tout sélectionner**).
3. (Optionnel) **⚙️ Options carte** :
   - **Format** : CR-80 (défaut). CR-79 / Custom disponibles.
   - **Faces** : *Recto seul* (défaut) ou *Recto + verso*.
   - **Fond perdu / bleed** : `0 mm` (taille exacte) ou `1 mm` (recommandé si des lisérés
     blancs apparaissent — voir §5).
   - **Thème** : *Clair* (recommandé, économise le ruban) ou *Foncé*.
   - QR (lien profil ou vCard), couleur d'accent, date d'émission, etc.
4. Vérifier l'**aperçu** à droite (taille réelle).

### A) Impression directe
- Cliquer **🖨 Imprimer**.
- Dans la fenêtre d'impression du navigateur :
  - **Imprimante** : la HiTi CS-…
  - **Marges** : Aucune / None.
  - **Échelle** : **100 %** (jamais « Ajuster à la page »).
  - **En-têtes et pieds de page** : décochés.
  - Format papier : **CR-80 / 85,6 × 54 mm** (l'app envoie déjà `@page size: 85.6mm 54mm`).
- Imprimer. Une carte physique sort par page. En recto+verso : page 1 = recto, page 2 = verso, etc.

### B) Via PDF
- Cliquer **📄 Export PDF** → `xguard-cartes-AAAA-MM-JJ.pdf` se télécharge.
- Ouvrir le PDF (Adobe Reader / Aperçu) → Imprimer → imprimante HiTi →
  **Taille réelle / 100 %**, marges nulles. Chaque page = une carte.

---

## 5. Calibration et dépannage

| Symptôme | Cause / correctif |
|---|---|
| **Liseré blanc** sur un ou plusieurs bords | Activer **Over-the-edge** dans le pilote HiTi, **et/ou** mettre le **bleed à 1 mm** dans les Options carte. |
| Image **décalée** (pas centrée) | Pilote HiTi → **Position adjustment / Calibration** : ajuster X/Y de quelques pixels. |
| Carte **rognée / trop petite** | L'échelle d'impression n'est pas à 100 % — désactiver « Ajuster à la page ». |
| Couleurs ternes | Vérifier le ruban YMCKO, nettoyer la tête (kit de nettoyage HiTi), qualité 300 dpi. |
| **QR ne scanne pas** | Garder le thème/QR par défaut ; ne pas réduire la carte ; éviter de trop plastifier par-dessus. |
| Recto-verso mal aligné | Modèle double face requis + Duplex activé ; sinon imprimer verso manuellement en retournant la carte. |
| Bourrage / carte n'avance pas | Cartes CR-80 30 mil, chargées selon le guide du bac, molette d'épaisseur bien réglée. |

---

## 6. Ce qu'il y a sur la carte

**Recto** : bandeau XGuard (couleur d'accent) · pastille avatar (initiales, couleur de la
personne) · nom · rôle · département · programmes (BSP, RCR, Drone…) · QR · pied avec
**ID**, date d'émission et type (VP / Lead / Employé / Contractant).

**Verso** (si activé) : QR de vérification, texte de certification, ligne de signature.

Le **QR** encode par défaut `https://nicksoucy.github.io/orgnigram-xguard/?card=<id>`
(vérification du profil) — modifiable dans **Options carte** (URL de base, ou mode vCard
qui encode plutôt les coordonnées du porteur).

### Photos
Les cartes utilisent l'avatar à initiales (comme partout dans l'app), car il n'y a pas de
photos dans la base pour l'instant. Pour ajouter de vraies photos plus tard : ajouter une
colonne `photo_url` à la table `people` et une `<img>` dans `_cardFrontHTML` (`js/views/cards.js`)
à la place de `.pc-avatar`. Le reste du pipeline d'impression ne change pas.

---

## 7. Résumé « je veux juste imprimer »

1. Pilote HiTi installé + Over-the-edge activé (§2–3).
2. App → **Cartes** → cocher les personnes.
3. **🖨 Imprimer** → imprimante HiTi, 100 %, marges nulles.
4. Carte prête. 🪪
