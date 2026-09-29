# XGuard Cartes — kit portable

Tout ce qu'il faut pour **fabriquer et imprimer les cartes d'identité XGuard sur une
imprimante à cartes HiTi**, sur n'importe quel ordinateur Windows ou Mac.
**Aucune connexion internet ni compte requis** pour faire les cartes.

## Installation (une fois par ordinateur)

1. Décompresser ce dossier (ex. sur le Bureau ou une clé USB).
2. *(Recommandé)* Mettre l'installateur du **pilote HiTi** dans le dossier `drivers/`
   (voir `drivers/LISEZMOI.txt`). Sinon, l'installateur ouvre le site HiTi pour le télécharger.
3. Brancher et allumer l'imprimante HiTi.
4. Lancer l'installateur :
   - **Windows** : double-clic sur **`Installer-Windows.bat`**
   - **Mac** : double-clic sur **`Installer-Mac.command`** (si bloqué : clic droit → Ouvrir)

L'installateur :
- copie l'app sur l'ordinateur et crée le raccourci **XGuard Cartes** (Bureau + menu) ;
- détecte l'imprimante HiTi, et installe le pilote s'il manque ;
- ouvre les réglages du pilote (CR-80, paysage, **over-the-edge**, ruban YMCKO) et peut imprimer une page test.

> Sans installer : **Windows** → double-clic sur `Ouvrir-Cartes.bat` ;
> **Mac** → ouvrir `index.html` dans Chrome, Edge ou Safari.

## Utilisation

1. **Personnes** → **📥 Importer** :
   - le `.json` exporté de l'organigramme (onglet **Cartes → 📦 Exporter pour le kit**), ou
   - un fichier Excel / CSV (voir **📄 Modèle Excel** et `exemple-personnes.csv`), ou
   - ajout à la main avec le formulaire.
2. **Cartes** → cocher les personnes → vérifier l'aperçu (taille réelle).
3. **🖨 Imprimer** → imprimante HiTi → **échelle 100 %**, **marges : aucune**.
   (ou **📄 Export PDF** puis imprimer le PDF en taille réelle)

Onglet **❓ Aide** dans l'app pour le dépannage rapide. Guide complet : `GUIDE-HITI.md`.

## Contenu

| Élément | Rôle |
|---|---|
| `index.html`, `kit.js`, `kit.css` | L'app de cartes (hors ligne) |
| `app/` | Moteur de rendu des cartes (identique à l'organigramme) |
| `lib/` | Librairies locales : QR, PDF, Excel, polices (licences incluses) |
| `drivers/` | Où déposer le pilote HiTi pour une installation sans internet |
| `Installer-Windows.bat`, `Installer-Mac.command`, `install/` | Installateurs |
| `Ouvrir-Cartes.bat` | Lancement portable Windows (sans installation) |
| `claude-skill/` | Compétence Claude pour que Claude sache utiliser/maintenir ce kit |
| `GUIDE-HITI.md` | Guide HiTi complet (pilote, ruban, calibration, dépannage) |

## Données

Les personnes sont gardées **dans le navigateur de cet ordinateur** (rien n'est envoyé en
ligne). Pour sauvegarder ou déplacer : **📤 Exporter CSV** puis réimporter ailleurs.

## Compétence Claude

Pour que Claude (Claude Code ou claude.ai) sache faire les cartes sur l'autre ordinateur :
- **Claude Code** : copier `claude-skill/xguard-cartes/` dans `~/.claude/skills/`
  (Windows : `%USERPROFILE%\.claude\skills\`).
- **claude.ai** : Paramètres → Capacités → Compétences → téléverser `claude-skill/xguard-cartes.zip`.
