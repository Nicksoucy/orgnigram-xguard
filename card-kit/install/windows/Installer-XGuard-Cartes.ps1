# =====================================================================
#  XGuard Cartes - installation Windows
#  1. Copie le kit dans %LOCALAPPDATA%\XGuard\Cartes
#  2. Cree les raccourcis "XGuard Cartes" (Bureau + menu Demarrer)
#  3. Verifie / installe le pilote de l'imprimante a cartes HiTi
#  4. (option) ouvre les preferences du pilote et imprime une page test
#  Lance par Installer-Windows.bat (a la racine du kit).
# =====================================================================
$ErrorActionPreference = 'Stop'
$KitRoot  = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)   # ...\install\windows -> racine du kit
$Target   = Join-Path $env:LOCALAPPDATA 'XGuard\Cartes'
$HitiPage = 'https://www.hiti.com/'

function Say($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }
function Step($n, $msg) { Write-Host ""; Write-Host "[$n] $msg" -ForegroundColor Cyan }
function Ask($q) { $r = Read-Host "$q (O/N)"; return $r -match '^(o|oui|y|yes)$' }

function Find-HitiPrinters {
  try { @(Get-Printer -ErrorAction Stop | Where-Object { $_.Name -match 'hiti' -or $_.DriverName -match 'hiti' }) }
  catch { @(Get-CimInstance Win32_Printer | Where-Object { $_.Name -match 'hiti' -or $_.DriverName -match 'hiti' }) }
}

function Find-Browser {
  $cands = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
  )
  foreach ($c in $cands) { if ($c -and (Test-Path $c)) { return $c } }
  return $null
}

Write-Host "=============================================" -ForegroundColor DarkYellow
Write-Host "   XGuard Cartes - installation (Windows)" -ForegroundColor DarkYellow
Write-Host "=============================================" -ForegroundColor DarkYellow

# ---------------------------------------------------------------- 1. copie
Step 1 "Copie du kit vers $Target"
New-Item -ItemType Directory -Force -Path $Target | Out-Null
foreach ($item in 'index.html','kit.css','kit.js','app','lib','GUIDE-HITI.md','LISEZMOI.md','exemple-personnes.csv','Ouvrir-Cartes.bat','Ouvrir-Cartes.ps1') {
  $src = Join-Path $KitRoot $item
  if (Test-Path $src) { Copy-Item $src -Destination $Target -Recurse -Force }
}
Say "   OK - kit installe." Green

# ---------------------------------------------------------------- 2. raccourcis
Step 2 "Raccourcis 'XGuard Cartes'"
$index   = Join-Path $Target 'index.html'
$fileUri = ([System.Uri]$index).AbsoluteUri
$browser = Find-Browser
$shell   = New-Object -ComObject WScript.Shell
$places  = @([Environment]::GetFolderPath('Desktop'), (Join-Path ([Environment]::GetFolderPath('Programs')) 'XGuard'))
foreach ($dir in $places) {
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  $lnk = $shell.CreateShortcut((Join-Path $dir 'XGuard Cartes.lnk'))
  if ($browser) {
    # Fenetre dediee (mode application) : pas de barre d'adresse, comme un vrai logiciel.
    $lnk.TargetPath = $browser
    $lnk.Arguments  = "--app=`"$fileUri`""
    $lnk.IconLocation = "$browser,0"
  } else {
    $lnk.TargetPath = $index
  }
  $lnk.WorkingDirectory = $Target
  $lnk.Description = 'Impression de cartes XGuard (HiTi CR-80)'
  $lnk.Save()
}
if ($browser) { Say "   OK - raccourcis crees (ouvre avec $([IO.Path]::GetFileNameWithoutExtension($browser)))." Green }
else { Say "   OK - raccourcis crees (navigateur par defaut). Edge ou Chrome recommande." Yellow }

# ---------------------------------------------------------------- 3. pilote HiTi
Step 3 "Imprimante a cartes HiTi"
$hiti = Find-HitiPrinters
if ($hiti.Count -gt 0) {
  Say "   OK - imprimante(s) HiTi deja installee(s) :" Green
  $hiti | ForEach-Object { Say "      - $($_.Name)" Green }
} else {
  Say "   Aucune imprimante HiTi installee pour l'instant." Yellow
  Say "   -> Branchez l'imprimante (USB) et allumez-la avant de continuer." Yellow
  $drvDir = Join-Path $KitRoot 'drivers'
  $inst = @()
  if (Test-Path $drvDir) {
    $inst = @(Get-ChildItem $drvDir -File | Where-Object { $_.Extension -in '.exe','.msi','.zip' } | Sort-Object Name)
  }
  if ($inst.Count -gt 0) {
    foreach ($f in $inst) {
      Say "   Installateur trouve : $($f.Name)"
      if ($f.Extension -eq '.zip') {
        $x = Join-Path $env:TEMP ("hiti_" + [IO.Path]::GetFileNameWithoutExtension($f.Name))
        Expand-Archive -Path $f.FullName -DestinationPath $x -Force
        $setup = Get-ChildItem $x -Recurse -Include 'setup.exe','*.msi','*install*.exe' -File | Select-Object -First 1
        if ($setup) {
          Say "   Lancement de $($setup.Name) (suivez l'assistant HiTi)..."
          Start-Process -FilePath $setup.FullName -Wait
        } else {
          $infs = Get-ChildItem $x -Recurse -Filter '*.inf' -File
          if ($infs) {
            Say "   Ajout du pilote au magasin Windows (pnputil, droits administrateur)..."
            foreach ($inf in $infs) { Start-Process pnputil.exe -ArgumentList "/add-driver `"$($inf.FullName)`" /install" -Verb RunAs -Wait }
          } else { Say "   Rien d'installable dans $($f.Name)." Red }
        }
      } elseif ($f.Extension -eq '.msi') {
        Say "   Lancement de $($f.Name)..."
        Start-Process msiexec.exe -ArgumentList "/i `"$($f.FullName)`"" -Wait
      } else {
        Say "   Lancement de $($f.Name) (suivez l'assistant HiTi)..."
        Start-Process -FilePath $f.FullName -Wait
      }
    }
  } else {
    Say ""
    Say "   Le dossier 'drivers' du kit est vide : il faut telecharger le pilote HiTi." Yellow
    Say "   Sur le site HiTi : Support -> Download -> Card Printer -> votre modele (ex. CS-200e)." Yellow
    Say "   Astuce : deposez l'installateur dans le dossier 'drivers' du kit pour les" Yellow
    Say "   prochaines installations (ca marchera alors sans internet)." Yellow
    Start-Process $HitiPage
    Read-Host "   Installez le pilote HiTi dans le navigateur qui vient de s'ouvrir, puis appuyez sur Entree"
  }
  Start-Sleep -Seconds 2
  $hiti = Find-HitiPrinters
  if ($hiti.Count -gt 0) {
    Say "   OK - imprimante HiTi detectee : $($hiti[0].Name)" Green
  } else {
    Say "   Imprimante HiTi toujours introuvable. Verifiez le cable USB / l'alimentation," Red
    Say "   puis relancez Installer-Windows.bat. (Parametres > Imprimantes et scanners)" Red
  }
}

# ---------------------------------------------------------------- 4. reglages
if ($hiti.Count -gt 0) {
  $name = $hiti[0].Name
  Step 4 "Reglages du pilote pour les cartes"
  Say "   Dans la fenetre qui va s'ouvrir, reglez :"
  Say "     - Carte / Card size : CR-80 (85,6 x 54 mm)"
  Say "     - Orientation       : Paysage (Landscape)"
  Say "     - Over-the-edge     : ACTIVE (impression bord a bord)"
  Say "     - Ruban             : YMCKO"
  Say "   puis 'Appliquer' / 'OK'."
  if (Ask "   Ouvrir les preferences d'impression de '$name' maintenant ?") {
    Start-Process rundll32.exe -ArgumentList "printui.dll,PrintUIEntry /e /n `"$name`"" -Wait
  }
  if (Ask "   Imprimer une page test Windows (utilise une carte vierge) ?") {
    Start-Process rundll32.exe -ArgumentList "printui.dll,PrintUIEntry /k /n `"$name`""
  }
}

# ---------------------------------------------------------------- fin
Write-Host ""
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Termine ! Ouvrez 'XGuard Cartes' sur le Bureau." -ForegroundColor Green
Write-Host "  Aide : onglet 'Aide' dans l'app, ou GUIDE-HITI.md" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
if (Ask "Ouvrir XGuard Cartes maintenant ?") {
  if ($browser) { Start-Process $browser -ArgumentList "--app=`"$fileUri`"" } else { Start-Process $index }
}
