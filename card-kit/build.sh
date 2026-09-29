#!/usr/bin/env bash
# Builds the portable XGuard Cartes kit (dist/XGuard-Cartes/ + dist/XGuard-Cartes.zip).
# The card renderer is copied from the org chart (js/views/cards.js, css/cards.css)
# so the app and the kit always print identical cards. Re-run after changing them.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
DIST="$HERE/dist"
OUT="$DIST/XGuard-Cartes"

rm -rf "$DIST"
mkdir -p "$OUT/app" "$OUT/lib" "$OUT/drivers" "$OUT/install/windows" "$OUT/claude-skill"

# App shell + shared renderer
cp "$HERE/index.html" "$HERE/kit.css" "$HERE/kit.js" "$OUT/"
cp "$REPO/js/views/cards.js" "$REPO/css/cards.css" "$OUT/app/"

# Libraries (all local: the kit must work offline)
cp -R "$HERE/lib/." "$OUT/lib/"
cp "$REPO/js/vendor/qrcode.js" "$OUT/lib/qrcode.js"
cp "$REPO/js/vendor/qrcode.LICENSE.md" "$OUT/lib/qrcode.LICENSE.md"

# Docs, sample data, drivers drop folder
cp "$HERE/LISEZMOI.md" "$HERE/exemple-personnes.csv" "$OUT/"
cp "$REPO/docs/HITI_PRINTING.md" "$OUT/GUIDE-HITI.md"
cp "$HERE/drivers/LISEZMOI.txt" "$OUT/drivers/"
# Any HiTi driver installers placed in card-kit/drivers/ locally get bundled too
# (they are git-ignored: they're the manufacturer's software).
find "$HERE/drivers" -maxdepth 1 -type f ! -name 'LISEZMOI.txt' -exec cp {} "$OUT/drivers/" \;

# Installers / launchers — Windows files need CRLF line endings
for f in Installer-Windows.bat Ouvrir-Cartes.bat Ouvrir-Cartes.ps1; do
  sed 's/\r$//; s/$/\r/' "$HERE/$f" > "$OUT/$f"
done
sed 's/\r$//; s/$/\r/' "$HERE/install/windows/Installer-XGuard-Cartes.ps1" > "$OUT/install/windows/Installer-XGuard-Cartes.ps1"
cp "$HERE/Installer-Mac.command" "$OUT/"
chmod +x "$OUT/Installer-Mac.command"

# Claude skill: folder (Claude Code) + zip (claude.ai upload)
cp -R "$HERE/skill/xguard-cartes" "$OUT/claude-skill/"
(cd "$OUT/claude-skill" && zip -qr xguard-cartes.zip xguard-cartes)

# Final archive (zip keeps the exec bit on Installer-Mac.command)
(cd "$DIST" && zip -qr -X XGuard-Cartes.zip XGuard-Cartes)
echo "Built: $DIST/XGuard-Cartes.zip ($(du -h "$DIST/XGuard-Cartes.zip" | cut -f1))"
