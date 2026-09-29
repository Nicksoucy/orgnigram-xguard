# Ouvre index.html dans Edge/Chrome en mode application (fenetre dediee), sinon navigateur par defaut.
$index = Join-Path $PSScriptRoot 'index.html'
$uri   = ([System.Uri]$index).AbsoluteUri
$cands = @(
  "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)
$b = $cands | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if ($b) { Start-Process $b -ArgumentList "--app=`"$uri`"" } else { Start-Process $index }
