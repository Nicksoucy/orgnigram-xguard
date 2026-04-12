---
type: api
tags: [ghl, gohighlevel, api, crm]
status: active
project: xguard-coaching
updated: 2026-04-12
---

# GoHighLevel API

## Connexion
- **PIT Token:** `pit-7de455ab-c46e-47a4-af9e-0b07a6c3a1ee`
- **Location ID:** `dfkLurZY2ADWAUZl4zYc`
- **API Version:** 2021-07-28
- **Base URL:** `https://services.leadconnectorhq.com`

## Utilisateurs GHL
| Personne | GHL ID |
|----------|--------|
| [[../Personnes/Heidys]] | FqpS2HfIklBPAiAoANBB |
| [[../Personnes/Domingos]] | 5kH5Q6ADlUTBkNGoPIFR |
| Banji Randri | llw4zkotq3ymdSsACRh9 |
| [[../Personnes/Nick]] | wByZytSBnOReBWcB3wof |

## Pipelines
| Pipeline | ID |
|----------|-----|
| Heidys ventes | 7vru0wO6zRcDJsfQGdFI |
| Drones | W08jXuPPrQDM0EFcCgAR |
| XGuard Elite | tj8JjZxQnqdJY8C3fq3l |

## Gotchas critiques
1. **Headers browser requis** — User-Agent, Origin, Referer pour bypasser Cloudflare
2. **Notes POST** — NE PAS inclure `locationId` dans le body (cause 422)
3. **Tasks** — DOIT inclure `completed: false`
4. **Opportunities search** — utiliser `location_id` (snake_case)
5. **Recording URL:** `GET /conversations/messages/{MSG_ID}/locations/{LOC_ID}/recording`

Voir: [[JustCall]], [[../Ventes/Domingos-Oliveira]]
