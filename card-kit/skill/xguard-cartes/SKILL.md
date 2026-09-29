---
name: xguard-cartes
description: Make and print XGuard ID cards (staff/trainer badges) on a HiTi CS-series card printer using the portable "XGuard Cartes" kit. Use when the user asks to make, print, reprint or design XGuard cards/badges ("cartes", "carte d'identité", "badge", "imprimer des cartes"), to add or import people for cards, to install or troubleshoot the HiTi card printer or its driver, or to set the card kit up on a new computer.
---

# XGuard Cartes — ID cards on a HiTi card printer

The **XGuard Cartes kit** is a self-contained, offline web app (plain HTML/JS, no server,
no login) that renders ID cards at the exact **ISO CR-80** size (85.6 × 54 mm) used by
HiTi CS-series card printers (CS-200e / CS-220e / CS-290 / CS-320), and prints them one
card per page. It is the portable twin of the **Cartes** tab in the XGuard org chart app
(`https://nicksoucy.github.io/orgnigram-xguard/`, repo `Nicksoucy/orgnigram-xguard`).

## Where things are

Installed location (after running the installer):
- Windows: `%LOCALAPPDATA%\XGuard\Cartes\` — shortcut "XGuard Cartes" on the Desktop.
- macOS: `~/Applications/XGuard Cartes/` — app `~/Applications/XGuard Cartes.app`.

Kit files: `index.html` (entry), `kit.js` (people manager + import/export),
`app/cards.js` + `app/cards.css` (card renderer — same code as the org chart),
`lib/` (vendored qrcode, jsPDF, html2canvas, SheetJS, fonts), `drivers/` (HiTi driver
installers go here), `Installer-Windows.bat`, `Installer-Mac.command`, `GUIDE-HITI.md`.

If the kit isn't installed, look for the unzipped `XGuard-Cartes` folder (Downloads,
Desktop, USB key) and run the installer for the OS.

## Workflow

1. **Get people into the kit** (tab *Personnes* → *📥 Importer*):
   - JSON from the org chart: org chart → tab *Cartes* → *📦 Exporter pour le kit*
     (`xguard-cartes-personnes-YYYY-MM-DD.json`, format `xguard-cards-v1`, includes
     departments + card options).
   - Excel/CSV with columns `id` (optional), `nom`, `role`, `type`
     (employé / contractuel / lead / vp), `departement`, `programmes` (separated by `;`).
     French or English headers are accepted. Template: *📄 Modèle Excel*.
   - Or the manual form. Imports **upsert** (match on id, else on name).
   If the user gives you a list of people (chat, spreadsheet, email), produce a CSV in
   the format above for them to import — `exemple-personnes.csv` is a reference. Save it
   with a UTF-8 BOM so Excel keeps the accents.
2. **Tab *Cartes*** → tick people → check the real-size preview. *⚙️ Options carte*:
   format (CR-80 default / CR-79 / custom), orientation, recto or recto+verso, bleed
   0/1/2 mm, light/dark theme, organisation name, subtitle, accent colour, issue date,
   QR (profile link `…/?card=<id>` or vCard), field toggles. Options persist per computer.
3. **Print**: *🖨 Imprimer* → HiTi printer → **Scale 100 %**, **Margins: none**, headers/
   footers off. The page size is already forced to the card size via `@page`.
   Or *📄 Export PDF* (one card per page, ≥300 dpi) → print at **actual size**.

## HiTi driver settings (once per computer)

Card size **CR-80**, orientation **Landscape**, **Over-the-edge ON** (edge-to-edge),
ribbon **YMCKO**, duplex only on double-sided models with *Recto + verso*. Windows:
`rundll32 printui.dll,PrintUIEntry /e /n "<HiTi printer name>"` opens the preferences.
The driver is HiTi's software and is **not bundled**: put the installer in `drivers/`
(then the kit's installer uses it offline) or download it from hiti.com → Support →
Download → Card Printer → model. Check it's installed: Windows `Get-Printer | ? Name -match hiti`,
macOS `lpstat -v | grep -i hiti`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| White sliver on an edge | Driver: Over-the-edge ON; and/or kit: bleed 1 mm |
| Image shifted | Driver: Position adjustment / calibration (X/Y offset) |
| Card printed too small / cropped | Print scale not 100 % ("Fit to page" on) |
| Blank page between cards | Browser headers/footers or margins on — turn off |
| QR won't scan | Don't shrink the card; keep the default QR size; light theme |
| Faded colours | YMCKO ribbon, clean the print head (HiTi cleaning kit) |
| People disappeared | Data lives in that browser's localStorage (per computer/browser). Re-import the JSON/CSV. Advise *📤 Exporter CSV* as backup. |
| Accents wrong after Excel edit | Save as "CSV UTF-8" or import the .xlsx directly |

## Changing the card design

The design lives in `app/cards.js` (`_cardFrontHTML`, `_cardBackHTML`) and
`app/cards.css` (all sizes in mm/pt — never px inside `.print-card`, it breaks physical
calibration). The canonical source is `js/views/cards.js` + `css/cards.css` in the
`orgnigram-xguard` repo; `card-kit/build.sh` there rebuilds this kit. Edit the repo copy
when possible so the org chart and the kit stay identical; for a quick local tweak, edit
the installed `app/` files and tell the user the change is local to that computer.

Photos: no photo data exists yet. To add them: a `photo` field (URL or data URL) per
person, and an `<img>` replacing `.pc-avatar` in `_cardFrontHTML`.
