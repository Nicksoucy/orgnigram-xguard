---
type: infrastructure
project: xguard-coaching
status: active
tags:
  - nitro
  - gpu
  - ssh
  - architecture
updated: 2026-04-12
---

# Architecture — 2 Machines

## PC Local (DESKTOP-BIS8JTE)
- **GPU:** AMD Radeon (PAS de CUDA)
- **Role:** Orchestration, Claude Code, edition de code
- **User:** nicol
- **IMPORTANT:** Ne JAMAIS transcrire ici. Pas de GPU NVIDIA.

## Nitro GPU (DESKTOP-VRNB9OV)
- **GPU:** NVIDIA GeForce GTX 1650 (4GB VRAM)
- **CUDA:** 12.1
- **Role:** Transcription Whisper, cron jobs, scoring IA
- **User:** user (PAS nicol)
- **IP Tailscale:** 100.109.177.101
- **SSH:** `ssh -i C:/Users/nicol/.ssh/id_nitro user@100.109.177.101`
- **SCP:** `scp -i C:/Users/nicol/.ssh/id_nitro fichier user@100.109.177.101:C:/Users/user/chemin`

## Connexion
- **Tailscale** relie les 2 machines
- **Claude Code** installe sur Nitro (v2.1.63, Max plan, nick@darkhorseads.com)

## Venv Python (Nitro)
```
C:\Users\User\.gemini\antigravity\scratch\audio_transcriber\venv\Scripts\python.exe
```
Ce venv a PyTorch + CUDA + faster-whisper. **Toujours utiliser ce venv**, pas le Python systeme.

## Regle absolue
> **JAMAIS transcrire localement.** Le PC local est AMD Radeon sans CUDA. Toujours SSH vers Nitro pour la transcription.

Voir aussi: [[Nitro-GPU]], [[Crons]], [[../SAC/Pipeline-SAC]]
