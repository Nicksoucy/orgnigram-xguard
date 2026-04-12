---
type: infrastructure
project: xguard-coaching
status: active
tags:
  - nitro
  - gpu
  - whisper
  - cuda
  - transcription
updated: 2026-04-12
---

# Nitro GPU Server

## Specs
- **Machine:** Acer Nitro N50-610
- **GPU:** NVIDIA GeForce GTX 1650, 4GB VRAM
- **CUDA:** 12.1
- **OS:** Windows

## faster-whisper Config
| Param | Valeur |
|-------|--------|
| Model | medium |
| Device | cuda |
| Compute type | int8_float16 |
| Language | fr |
| Beam size | 3 |
| VAD filter | True |
| Vitesse | 15-25s par appel |

## Repertoires de transcripts
| Agent | Chemin |
|-------|--------|
| [[../Personnes/Hamza\|Hamza]] | `C:\Users\user\xguard_transcripts\hamza\` |
| [[../Personnes/Lilia\|Lilia]] | `C:\Users\user\xguard_transcripts\lilia\` |
| [[../Personnes/Sekou\|Sekou]] | `C:\Users\user\xguard_transcripts\sekou\` |
| [[../Personnes/Heidys\|Heidys]] | `C:\Users\user\xguard_transcripts\heidys\` |
| [[../Personnes/Domingos\|Domingos]] | `C:\Users\user\xguard_transcripts\domingos\` |

## Scripts Cron
Tous dans `C:\Users\user\crons\` — voir [[Crons]]

## Format JSON des transcripts
```json
{
  "id": "call_id",
  "contact_name": "Nom",
  "call_time": "2026-03-27 14:30:00",
  "duration_s": 245,
  "transcript": "Texte complet...",
  "category": "inscription",
  "agent": "hamza"
}
```

## Troubleshooting
- **CUDA errors:** Toujours utiliser le venv Python, PAS le systeme
- **Crash apres 500+ fichiers:** OOM possible, pas de reload du modele entre batches
- **cublas64_12.dll manquant:** Python systeme, utiliser le venv

Voir: [[Architecture]], [[Crons]]
