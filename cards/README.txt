========================================================
  ÉDITEUR DE CARTES XGUARD — VERSION WEB AUTONOME
========================================================

CE QUE C'EST
------------
« index.html » est une application web COMPLÈTE et AUTONOME :
 - un seul fichier
 - les logos (XGuard + Smith & Wesson) sont intégrés dedans (base64)
 - aucune dépendance externe, aucune connexion internet requise pour fonctionner
 - fonctionne dans n'importe quel navigateur (Chrome, Edge, Firefox, Safari)

Tu peux donc l'ouvrir localement (double-clic) OU l'héberger sur le web.


CE QU'ELLE FAIT
---------------
 - Concevoir la carte recto + verso (déplacer, redimensionner, éditer chaque
   élément : nom, dates, adresse, logos, tailles, positions).
 - Exporter en PNG 1012 x 638 px (format carte CR80, 300 DPI) — prêt à imprimer.


========================================================
  NOUVEAUTÉS
========================================================

 - MODÈLES (menu « Modèle ») : 6 designs de carte prêts à comparer et à choisir :
     • Classique (actuel)        • Sentinelle — tactique (fond foncé)
     • Permis Officiel (navy/or) • Sceau d'Honneur (prestige navy/or)
     • Repère (blanc minimal)    • Badge de Service (ID opérationnel)
   Choisis-en un, puis on le peaufine ensemble.

 - FORMATIONS (menu « Formation ») : Menottage / Gardiennage / Drone. Change le
   texte du programme, la qualification et l'accent d'un seul clic.

 - DONNÉES ÉLÈVE (panneau de droite) : remplis Nom, Prénom, Qualification, dates,
   No de carte, Formateur, No CENT — la carte se remplit toute seule (plus besoin
   de cliquer chaque texte). Le nom passe en MAJUSCULES et « Expire le » se calcule
   à +3 ans automatiquement quand tu changes « Émise le ».

 - SAUVEGARDE AUTOMATIQUE : ton travail est gardé dans le navigateur (rien n'est
   perdu au rafraîchissement). ANNULER / RÉTABLIR (Ctrl+Z / Ctrl+Maj+Z).

 - Le nom du fichier PNG exporté reprend le No de carte (ex : XG-MEN-001_recto.png)
   — plus d'écrasement d'un élève par l'autre.

 - Photo et QR sont pour l'instant des ESPACES RÉSERVÉS (visuels du design) ; le
   téléversement de photo et la vérification QR en ligne ne sont pas encore actifs.


========================================================
  TRAVAILLER ICI, IMPRIMER SUR L'AUTRE ORDINATEUR
========================================================
Cette machine n'a pas de port USB pour la HiTi CS-200e. Le flux recommandé :
 1. Conçois / ajuste les cartes ici (dans « cards/ » du dépôt).
 2. Sur l'ordinateur du bureau (relié à l'imprimante) :  git pull
 3. Ouvre « cards/index.html » (double-clic) — 100 % hors-ligne — exporte le PNG
    et imprime sur la HiTi.
Le dépôt reste PRIVÉ : ne publie pas cet outil sur une page web publique.


IMPORTANT — L'IMPRESSION RESTE LOCALE
-------------------------------------
La CONCEPTION peut être en ligne (accessible de partout).
L'IMPRESSION se fait toujours sur l'ordinateur du bureau relié en USB à la
HiTi CS-200e (le nuage ne peut pas accéder à une imprimante à cartes USB).
Workflow : concevoir en ligne -> exporter le PNG -> imprimer sur le PC du bureau.


========================================================
  COMMENT LA METTRE EN LIGNE (3 options)
========================================================

OPTION 1 — Netlify Drop (le plus rapide, gratuit, ~2 min)
---------------------------------------------------------
 1. Va sur https://app.netlify.com/drop
 2. Glisse-dépose le DOSSIER « xguard-card-web » dans la page.
 3. Netlify te donne une URL (ex: https://nom-aleatoire.netlify.app).
 -> Recommandé : mets un mot de passe sur le site (Netlify > Site settings >
    Access control) pour garder l'outil privé au bureau.

OPTION 2 — Sur ton hébergement academiexguard.ca
-------------------------------------------------
 1. Connecte-toi à ton hébergement (cPanel / FTP).
 2. Crée un sous-dossier privé, ex : /cartes/
 3. Téléverse « index.html » dedans.
 4. Accès : https://academiexguard.ca/cartes/
 -> Protège le dossier par mot de passe (.htpasswd / réglage cPanel).

OPTION 3 — Cloudflare Pages ou GitHub Pages (gratuit)
-----------------------------------------------------
 - Cloudflare Pages : crée un projet, téléverse le dossier, obtiens une URL.
 - GitHub Pages : mets index.html dans un dépôt, active Pages.


========================================================
  VIE PRIVÉE / SÉCURITÉ
========================================================
Cet outil génère des cartes de certification portant les marques XGuard,
Smith & Wesson Academy et C.E.N.T. Garde-le en accès PRIVÉ (mot de passe /
usage interne). Ne le laisse pas indexable publiquement.


========================================================
  POUR L'IMPRESSION EN LOT (plusieurs élèves)
========================================================
La génération en lot depuis un fichier CSV se fait sur le PC du bureau avec
les scripts PowerShell (dossier Desktop\Hiti\XGuard). L'éditeur web sert à
concevoir/ajuster une carte à la fois et exporter le PNG.
