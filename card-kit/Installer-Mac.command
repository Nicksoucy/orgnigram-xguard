#!/bin/bash
# =====================================================================
#  XGuard Cartes - installation macOS  (double-cliquez ce fichier)
#  1. Copie le kit dans ~/Applications/XGuard Cartes
#  2. Cree l'app "XGuard Cartes" (Applications + Bureau)
#  3. Verifie / installe le pilote de l'imprimante a cartes HiTi
#  Si macOS bloque l'ouverture : clic droit > Ouvrir.
# =====================================================================
set -u
KIT="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/Applications/XGuard Cartes"
APP="$HOME/Applications/XGuard Cartes.app"
HITI_PAGE="https://www.hiti.com/"

c() { printf "\033[%sm%s\033[0m\n" "$1" "$2"; }
step() { echo; c "36" "[$1] $2"; }
ask() { read -r -p "$1 (o/n) " r; [[ "$r" =~ ^([oOyY]|oui|yes)$ ]]; }
find_hiti() { lpstat -v 2>/dev/null | grep -i hiti; }

c "33" "============================================="
c "33" "   XGuard Cartes - installation (macOS)"
c "33" "============================================="

# ---------------------------------------------------------------- 1. copie
step 1 "Copie du kit vers $TARGET"
mkdir -p "$TARGET"
for item in index.html kit.css kit.js app lib GUIDE-HITI.md LISEZMOI.md exemple-personnes.csv; do
  [ -e "$KIT/$item" ] && cp -R "$KIT/$item" "$TARGET/"
done
xattr -dr com.apple.quarantine "$TARGET" 2>/dev/null || true
c "32" "   OK - kit installe."

# ---------------------------------------------------------------- 2. app
step 2 "Application 'XGuard Cartes'"
INDEX="$TARGET/index.html"
if [ -d "/Applications/Google Chrome.app" ]; then
  # Fenetre dediee (mode application), comme un vrai logiciel.
  LAUNCH="open -na 'Google Chrome' --args --app='file://$INDEX'"
elif [ -d "/Applications/Microsoft Edge.app" ]; then
  LAUNCH="open -na 'Microsoft Edge' --args --app='file://$INDEX'"
else
  LAUNCH="open '$INDEX'"
fi
rm -rf "$APP"
if osacompile -o "$APP" -e "do shell script \"$LAUNCH\"" 2>/dev/null; then
  ln -sfn "$APP" "$HOME/Desktop/XGuard Cartes"
  c "32" "   OK - app creee dans ~/Applications et raccourci sur le Bureau."
else
  ln -sfn "$INDEX" "$HOME/Desktop/XGuard Cartes.html"
  c "33" "   osacompile indisponible - raccourci vers index.html cree sur le Bureau."
fi
[ -d "/Applications/Google Chrome.app" ] || [ -d "/Applications/Microsoft Edge.app" ] || \
  c "33" "   Conseil : Chrome ou Edge donne le meilleur rendu d'impression (Safari fonctionne aussi)."

# ---------------------------------------------------------------- 3. pilote HiTi
step 3 "Imprimante a cartes HiTi"
if find_hiti >/dev/null; then
  c "32" "   OK - imprimante HiTi deja installee :"; find_hiti | sed 's/^/      /'
else
  c "33" "   Aucune imprimante HiTi installee. Branchez-la (USB) et allumez-la."
  shopt -s nullglob nocaseglob
  PKGS=("$KIT"/drivers/*.pkg "$KIT"/drivers/*.dmg "$KIT"/drivers/*.zip)
  shopt -u nullglob nocaseglob
  if [ ${#PKGS[@]} -gt 0 ]; then
    for f in "${PKGS[@]}"; do
      c "0" "   Installateur trouve : $(basename "$f")"
      case "$f" in
        *.zip|*.ZIP) d="$(mktemp -d)"; unzip -q "$f" -d "$d"; open "$d" ;;
        *)     open "$f" ;;
      esac
    done
    read -r -p "   Terminez l'assistant HiTi, puis appuyez sur Entree... " _
  else
    c "33" "   Le dossier 'drivers' du kit est vide : il faut telecharger le pilote HiTi macOS."
    c "33" "   Sur le site HiTi : Support -> Download -> Card Printer -> votre modele (ex. CS-200e)."
    c "33" "   Astuce : deposez l'installateur (.pkg/.dmg) dans 'drivers' pour les prochaines fois."
    open "$HITI_PAGE"
    read -r -p "   Installez le pilote, puis appuyez sur Entree... " _
  fi
  if ! find_hiti >/dev/null; then
    c "33" "   Ajoutez maintenant l'imprimante : Reglages Systeme > Imprimantes et scanners > Ajouter."
    open "x-apple.systempreferences:com.apple.Print-Scan-Settings.extension" 2>/dev/null || \
      open "x-apple.systempreferences:com.apple.preference.printfax"
    read -r -p "   Imprimante ajoutee ? Appuyez sur Entree... " _
  fi
  if find_hiti >/dev/null; then c "32" "   OK - imprimante HiTi detectee."
  else c "31" "   Imprimante HiTi introuvable. Verifiez USB/alimentation puis relancez ce fichier."; fi
fi

# ---------------------------------------------------------------- 4. reglages
echo
c "36" "[4] Reglages du pilote (dans la fenetre d'impression > options HiTi) :"
echo "     - Carte / Card size : CR-80 (85,6 x 54 mm)"
echo "     - Orientation       : Paysage"
echo "     - Over-the-edge     : ACTIVE (bord a bord)"
echo "     - Ruban             : YMCKO"

echo
c "32" "============================================="
c "32" "  Termine ! Ouvrez 'XGuard Cartes' (Bureau ou Applications)."
c "32" "  Aide : onglet 'Aide' dans l'app, ou GUIDE-HITI.md"
c "32" "============================================="
if ask "Ouvrir XGuard Cartes maintenant ?"; then
  if [ -d "$APP" ]; then open "$APP"; else open "$INDEX"; fi
fi
