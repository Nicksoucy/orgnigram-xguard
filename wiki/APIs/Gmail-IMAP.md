---
type: api
tags: [email, imap, smtp, gmail]
status: active
project: xguard-coaching
updated: 2026-04-12
---

# Gmail IMAP — Email academie@

## Connexion
- **Email:** academie@academiexguard.ca
- **App Password:** qlhoktyrfnrcbomd
- **IMAP:** imap.gmail.com:993 (SSL)
- **SMTP:** smtp.gmail.com:465 (SSL)

## Utilisation
1. **Email stats quotidien** (email_stats.py) — emails recus/envoyes/sans reponse
2. **KB Builder** (kb_email_analyzer.py) — analyse IMAP -> classification Haiku -> FAQ
3. **Hot leads** — emails sans reponse cross-ref avec appels manques

## Dossiers importants
INBOX, "Service a la clientele a traiter", Annuler, Litige, BSP, Secourisme, Recouvrement, Drone, Retard/absence, Winback

## Stats
- 272,096 emails au total
- ~1185 analyses par le KB system
- Filtrage: exclut noreply@ et domaines internes @xguard.ca, @academiexguard.ca

## SMTP (envoi rapports)
- **Depuis:** nick@darkhorseads.com
- **App Password:** kjaqmxuewwzkxcif
- **Destinataires:** hmaghraoui65@gmail.com + nick@darkhorseads.com

Voir: [[JustCall]], [[../KB-System/Architecture-KB]]
