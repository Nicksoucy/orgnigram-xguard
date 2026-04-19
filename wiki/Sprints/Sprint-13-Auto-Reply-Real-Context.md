---
type: sprint
project: xguard-coaching
status: paused
tags: [sprint-13, auto-reply, kb, emails, hamza-voice]
updated: 2026-04-14
---

# Sprint 13 — Auto-Reply avec Vrai Contexte d'Hamza

**Date creation:** 14 avril 2026
**Statut:** PAUSE (reprendre quand KB enrichi)

## Probleme decouvert

Le premier essai d'auto-reply (`auto_reply_drafts.py`) fonctionne techniquement mais genere des reponses **trop generiques**. Exemple observe:

> Bonjour Dion, c'est excellent! Nous pouvons certainement accommoder votre
> demande. Nous offrons des plans de financement flexibles... Je vous
> recommande de nous appeler pour confirmer les details specifiques...

**Le probleme:** Cette reponse ne contient pas:
- Le **lien Stripe** qu'Hamza envoie vraiment
- Les **details du virement Interac** (email, montant, reference)
- Les **instructions specifiques** pour finaliser le paiement
- Les **formules exactes** qu'Hamza utilise (vocabulaire, ton, longueur)

## Cause racine

Le systeme KB actuel (`kb_email_analyzer.py`) analyse uniquement les emails **recus** (1185+ emails classifies). Les `suggested_response` dans `kb_topics` sont generees par Haiku **sans aucun contexte reel** — c'est l'IA qui devine ce qu'il faudrait repondre.

**Ce qui manque:** Analyser les **500+ reponses reelles d'Hamza** dans `[Gmail]/Messages envoyés` pour extraire:
- Le vrai vocabulaire et ton
- Les liens precis (Stripe, formulaires, site web)
- Les instructions Interac (montant, email, reference)
- Les templates recurrents
- Les informations structurees (adresses, horaires, numeros)

## Plan pour reprendre

### Phase 1: Analyser les reponses reelles d'Hamza

**Nouveau script:** `crons/analyze_hamza_replies.py`

```
Fetch [Gmail]/Messages envoyés des 6-12 derniers mois
  -> Filtre: from academie@academiexguard.ca, not internal forwards
  -> Pour chaque email envoye:
    - Extract topic via Haiku (paiement/inscription/annulation/etc.)
    - Extract liens (regex: https://buy.stripe.com/*, formulaires, etc.)
    - Extract infos structurees:
      * Montants ($XXX.XX)
      * Emails Interac
      * References/codes de reservation
      * Adresses
      * Dates et heures
    - Stocker texte complet
  -> Grouper par topic
  -> Save dans hamza_reply_templates
```

### Phase 2: Nouvelle table Supabase

```sql
CREATE TABLE hamza_reply_templates (
  id BIGSERIAL PRIMARY KEY,
  topic_id TEXT NOT NULL,
  category TEXT,
  full_reply TEXT,              -- texte complet de la reponse
  extracted_links JSONB,        -- [{type: "stripe", url: "https://..."}]
  payment_info JSONB,           -- {interac_email, amount, reference}
  structured_data JSONB,        -- autres infos extraites
  reply_count INTEGER,          -- nombre d'emails similaires
  sent_date TIMESTAMPTZ,
  msg_id TEXT UNIQUE,
  analyzed_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_hamza_templates_topic ON hamza_reply_templates(topic_id);
```

### Phase 3: Refaire auto_reply_drafts.py

Au lieu d'utiliser `kb_topics.suggested_response` (generique), utiliser:

```python
def draft_reply(email_obj, topic):
    # Fetch 5-10 real replies from Hamza for this topic
    real_replies = sb_get(
        f"hamza_reply_templates?topic_id=eq.{topic['topic_id']}"
        f"&order=sent_date.desc&limit=10"
    )

    # Extract common links and structured data
    stripe_links = [r["extracted_links"]["stripe"] for r in real_replies if "stripe" in r["extracted_links"]]
    interac_info = next((r["payment_info"] for r in real_replies if r.get("payment_info")), None)

    # Build enriched prompt with REAL examples
    prompt = f"""Voici 5 vraies reponses d'Hamza sur ce sujet:

    Exemple 1:
    {real_replies[0]['full_reply']}

    Exemple 2:
    {real_replies[1]['full_reply']}
    ...

    Liens Stripe a inclure si paiement: {stripe_links}
    Email Interac: {interac_info['interac_email'] if interac_info else 'N/A'}

    Redige une reponse dans CE style exact, avec CES liens et CES details,
    adaptee au nouvel email ci-dessous.

    Nouvel email:
    {email_obj['body']}
    """

    return call_claude(prompt, model="haiku")
```

### Phase 4: Validation

Avant de relancer l'auto-reply en production:
1. Dry-run sur 10 emails avec nouvelles donnees
2. Comparer vs l'ancien systeme
3. Verifier que les liens Stripe/Interac apparaissent
4. Verifier que le ton ressemble vraiment a Hamza

## Fichiers a creer/modifier

| Fichier | Action | Notes |
|---------|--------|-------|
| `crons/analyze_hamza_replies.py` | CREATE | Extraction des vraies reponses |
| `crons/auto_reply_drafts.py` | MODIFY | Utiliser les templates au lieu de KB generique |
| Supabase table `hamza_reply_templates` | CREATE | Stockage des reponses reelles |
| `crons/extract_payment_info.py` | CREATE | Helper pour extraire montants/liens/Interac |

## Risques a considerer

1. **PII dans les emails** — les reponses contiennent des montants, adresses, noms. Les stocker chiffres ou ne pas les exposer.
2. **Liens Stripe expires** — Stripe genere des liens qui peuvent expirer. Ne pas reutiliser des vieux liens.
3. **Prix qui changent** — Si un cours passe de $399 a $449, un vieux template aura le mauvais prix.
4. **Reponses non-standard** — Hamza reponse parfois de facon tres specifique (ex: "voici ton remboursement de $X"). Ces reponses ne sont PAS des templates.

## Decision: quand reprendre

A reprendre quand:
- [ ] Tu as le temps de reviser la qualite des templates extraits
- [ ] Ou quand tu veux vraiment automatiser et as 2-3h pour le faire bien
- [ ] Ou si tu trouves que Hamza perd trop de temps sur des reponses repetitives

**Pour l'instant:** Le code actuel de `auto_reply_drafts.py` reste deploye sur Nitro mais **pas de cron actif**. Les fichiers sont prets a etre relances quand on aura les vraies donnees.

## Liens

- [[../SAC/Pipeline-SAC|Pipeline SAC]]
- [[../KB-System/Architecture-KB|KB System]]
- [[../Personnes/Hamza|Hamza]]
- Script actuel: `C:/Users/nicol/orgnigram-xguard/crons/auto_reply_drafts.py`
