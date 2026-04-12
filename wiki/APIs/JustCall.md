---
type: api
tags: [justcall, api, appels, telephonie]
status: active
project: xguard-coaching
updated: 2026-04-12
---

# JustCall API

## Connexion
- **Base URL:** `https://api.justcall.io/v1`
- **API Key:** `daf60d953694336f07c84c74205eb311dd85c996`
- **API Secret:** `20612f8fcb80ef33845cbdc226bc8174853c82dd`
- **Auth:** Header `Authorization: {KEY}:{SECRET}`

## Endpoint principal
`POST /calls/query`
```json
{
  "from_date": "YYYY-MM-DD",
  "to_date": "YYYY-MM-DD",
  "agent_id": "301418",
  "per_page": 100,
  "page": 1
}
```

## Comptes et agents
| Compte | Agent ID | Utilise par |
|--------|----------|-------------|
| academie@ | 301418 | [[../Personnes/Hamza]] + [[../Personnes/Sekou]] |
| formateur@ | 302145 | [[../Personnes/Lilia]] |
| garheidys@ | 407715 | [[../Personnes/Heidys]] |

## Champs retournes par l'API
| Champ | Type | Notes |
|-------|------|-------|
| id | int | Identifiant unique |
| time | string | "YYYY-MM-DD HH:MM:SS" |
| duration | string | Secondes |
| direction | string | "1"=inbound, "0"=outbound |
| contact_name | string | |
| contact_number | string | |
| notes | string | Signature agent + motif |
| recording | string | URL (vide si pas d'enregistrement) |
| missed_call_type | string | "1"=no answer, "2"=busy, "3"=abandoned |
| status | string | Toujours "0" |

## Champs NON disponibles dans l'API
- `queue_wait_time` — disponible uniquement dans CSV export
- `call_traits` — disponible uniquement dans CSV export
- Ces champs alimentent les indicateurs 25, 28-31 des [[../SAC/39-Indicateurs]]

## Gotchas
> **`from_datetime` / `to_datetime` sont IGNORES.** Utiliser `from_date`/`to_date` et filtrer cote client.

- Rate limit: ajouter 0.5s sleep entre pages
- Pagination: incrementer `page` jusqu'a `data` vide ou len < 100
- Filtre recommande: `duration >= 30` ET `recording` non vide

Voir: [[GHL]], [[../SAC/Pipeline-SAC]]
