@echo off
rem Double-cliquez ce fichier pour installer XGuard Cartes + le pilote HiTi.
chcp 65001 >nul
title XGuard Cartes - installation
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install\windows\Installer-XGuard-Cartes.ps1"
echo.
pause
