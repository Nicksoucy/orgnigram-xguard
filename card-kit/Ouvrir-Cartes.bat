@echo off
rem Ouvre XGuard Cartes sans rien installer (version portable, ex. depuis une cle USB).
powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0Ouvrir-Cartes.ps1"
