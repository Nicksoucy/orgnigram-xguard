"""
SAC Scoring Library — Shared scoring functions for daily/weekly/backfill.
10 SAC-adapted dimensions + classification + first-name detection + objection normalization.
"""

import re

# ---------------------------------------------------------------------------
# First-name detection
# ---------------------------------------------------------------------------

AGENT_NAME_PATTERNS = {
    "lilia": re.compile(r"\b(lilia|lilya|lilea|lillian)\b", re.IGNORECASE),
    "hamza": re.compile(r"\b(hamza|hamzah|amza|amjad)\b", re.IGNORECASE),
    "sekou": re.compile(r"\b(sekou|sékou|secou|sécou|sécoudé|secoudé|sékou de|secou de|sekou de)\b", re.IGNORECASE),
}

def detect_agent_from_transcript(text: str):
    intro = " ".join(text.split()[:150]).lower()
    for agent, pat in AGENT_NAME_PATTERNS.items():
        if pat.search(intro):
            return agent
    return None

# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------

_PLAINTE = re.compile(r"\b(plainte|mécontent|insatisfait|rembours|annuler|annulation|déçu|inacceptable|pire|problème grave)\b", re.I)
_INSCRIPTION = re.compile(r"\b(inscrire|inscription|formation|cours|session|programme|date|place|disponible|gardiennage|sécurité|bsp|secourisme)\b", re.I)
_SUPPORT = re.compile(r"\b(problème|aide|fonctionne pas|ne marche pas|erreur|bug|technique|accès|mot de passe|connexion|identifiant|compte)\b", re.I)
_INFO = re.compile(r"\b(information|renseignement|question|comment|combien|prix|tarif|horaire|adresse|coût|frais)\b", re.I)

def classify_call(text: str) -> str:
    if _PLAINTE.search(text): return "plainte"
    if _INSCRIPTION.search(text): return "inscription"
    if _SUPPORT.search(text): return "support"
    if _INFO.search(text): return "info"
    return "autre"

# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _count(text, patterns):
    c = 0
    for p in patterns:
        c += len(re.findall(p, text, re.IGNORECASE))
    return c

def _norm(raw, high=10):
    return round(min(10.0, max(0, (raw / high) * 10)), 1)

# ---------------------------------------------------------------------------
# 10 SAC Dimensions
# ---------------------------------------------------------------------------

SAC_DIMENSIONS = [
    "accueil", "ecoute", "resolution", "patience", "professionnalisme",
    "vente_subtile", "qualification", "gestion_objections", "energie", "engagement",
    "empathie", "connaissance_produit", "suivi",
]

DIM_LABELS = {
    "accueil": "Accueil", "ecoute": "Écoute active", "resolution": "Résolution",
    "patience": "Patience", "professionnalisme": "Professionnalisme",
    "vente_subtile": "Vente subtile", "qualification": "Qualification",
    "gestion_objections": "Gestion des objections", "energie": "Énergie positive",
    "engagement": "Engagement",
    "empathie": "Empathie", "connaissance_produit": "Connaissance produit",
    "suivi": "Suivi",
}

# Weights for global score — SAC-focused
DIM_WEIGHTS = {
    "accueil": 1.5, "ecoute": 1.5, "resolution": 1.5, "patience": 1.5, "professionnalisme": 1.5,
    "vente_subtile": 1.0, "qualification": 1.0, "gestion_objections": 1.0,
    "energie": 0.8, "engagement": 0.8,
    "empathie": 1.2, "connaissance_produit": 1.2, "suivi": 1.2,
}

def score_accueil(text):
    words = text.split()
    intro = " ".join(words[:150]) if len(words) > 150 else text
    s = 0.0
    if re.search(r"\b(bonjour|bonsoir|allo)\b", intro, re.I): s += 2.0
    if re.search(r"\b(xguard|x[\s-]?guard|académie|academiexguard)\b", intro, re.I): s += 2.5
    if re.search(r"\b(je m'appelle|mon nom est|c'est|ici)\b", intro, re.I): s += 2.0
    if re.search(r"\b(comment puis-je vous aider|en quoi puis-je|que puis-je faire)\b", intro, re.I): s += 2.0
    if re.search(r"\bcomment (allez|ça va|vas)\b", intro, re.I): s += 1.5
    return round(min(10.0, s), 1)

def score_ecoute(text):
    # Basic acknowledgment (1x weight)
    ack = [r"\bje comprends\b", r"\bje vous comprends\b", r"\bje vois\b", r"\bd'accord\b",
           r"\btout à fait\b", r"\bexactement\b", r"\bbien sûr\b", r"\babsolument\b",
           r"\ben effet\b", r"\bc'est une bonne question\b", r"\bvous avez raison\b"]
    # Deep reformulation (2x weight — shows real listening)
    reform = [r"\bsi je comprends bien\b", r"\bdonc vous\b", r"\bce que vous dites\b",
              r"\bvous me dites que\b", r"\bsi je résume\b", r"\bvous cherchez (donc|à)\b",
              r"\bsi j'ai bien compris\b", r"\bvous (souhaitez|voulez) (donc|que)\b"]
    return _norm(_count(text, ack) + _count(text, reform) * 2, high=10)

def score_resolution(text):
    sol = [r"\bvoici ce (qu'on|que je)\b", r"\bje vais vous\b", r"\bje vous envoie\b",
           r"\bje vous transfère\b", r"\bla réponse\b", r"\bvous pouvez\b",
           r"\bje vous explique\b", r"\bje vais vérifier\b", r"\bc'est (fait|noté|envoyé|confirmé)\b",
           r"\bj'ai (noté|pris en note|vérifié|confirmé)\b",
           r"\bc'est réglé\b", r"\bvoilà c'est fait\b", r"\bon a tout couvert\b"]
    conf = [r"\best-ce que.*clair\b", r"\bavez-vous d'autres questions\b",
            r"\best-ce que ça.*aide\b", r"\by a-t-il.*autre\b",
            r"\best-ce que ça (vous )?convient\b", r"\bça répond à votre\b"]
    # Penalty for unresolved
    unresolved = [r"\bje ne sais pas\b", r"\bil faudrait (appeler|contacter)\b",
                  r"\bje ne peux pas\b", r"\bmalheureusement\b"]
    raw = _count(text, sol) * 1.2 + _count(text, conf) * 2.0 - _count(text, unresolved) * 1.5
    return _norm(max(0, raw), high=10)

def score_patience(dur_s):
    m = dur_s / 60
    if m < 0.5: return 1.0
    if m < 1: return 3.0
    if m < 2: return 5.0
    if m < 4: return 7.0
    if m < 8: return 9.0
    if m <= 15: return 10.0
    if m <= 25: return 9.5
    return 9.0

def score_professionnalisme(text):
    pro = [r"\bmerci\b", r"\bs'il vous plaît\b", r"\bje vous en prie\b", r"\bavec plaisir\b",
           r"\bbonne journée\b", r"\bbonne soirée\b", r"\bn'hésitez pas\b", r"\bà votre disposition\b"]
    neg = [r"\b(euh|tsé|genre|là là|faque)\b", r"\b(ça marche pas|j'sais pas|aucune idée)\b"]
    return _norm(max(0, _count(text, pro) * 1.5 - _count(text, neg)), high=8)

def score_vente_subtile(text):
    soft = [r"\bsi (ça|cela) vous intéresse\b", r"\bje (peux|pourrais) vous inscrire\b",
            r"\bvoulez-vous (que je|qu'on)\b", r"\bla prochaine (session|formation|date)\b",
            r"\bil (reste|y a) (encore|des) place\b", r"\bsi vous voulez réserver\b"]
    val = [r"\bl'avantage\b", r"\bce qui est bien\b", r"\bça (permet|va vous)\b",
           r"\b(certification|certifié|accrédité|reconnu)\b", r"\b(emploi|employeur|carrière)\b"]
    nxt = [r"\bje vous envoie (le lien|les infos|un courriel)\b", r"\bje vous rappelle\b",
           r"\bon se (reparle|rappelle)\b", r"\bquand (seriez|êtes)-vous disponible\b"]
    return _norm(_count(text, soft) * 2 + _count(text, val) * 1.5 + _count(text, nxt) * 2, high=10)

def score_qualification(text):
    qpats = [r"\bqu['']est-ce (que|qui)\b.*\?", r"\bpourquoi\b.*\?", r"\bcomment\b.*\?",
             r"\bquand\b.*\?", r"\bcombien\b.*\?", r"\bquel(le)?s?\b.*\?",
             r"\best-ce que\b.*\?", r"\bavez[- ]vous\b.*\?"]
    tops = [r"\b(besoin|objectif|motivation)\b", r"\b(expérience|parcours)\b",
            r"\b(disponibilité|horaire|quand|date)\b", r"\b(situation|emploi|travail)\b"]
    return round(min(10.0, min(6, _count(text, qpats)) + min(4, _count(text, tops) * 0.8)), 1)

def score_gestion_objections(text):
    obj = [r"c'est trop cher", r"pas le budget", r"je vais réfléchir", r"pas le temps",
           r"pas intéressé", r"pas le bon moment", r"mécontent", r"insatisfait", r"plainte"]
    hand = [r"\bje comprends\b", r"\bjustement\b", r"\ben fait\b", r"\bc'est normal\b",
            r"\bbonne question\b", r"\btout à fait\b", r"\bje vais (vérifier|m'occuper)\b",
            r"\bon va (trouver|régler)\b", r"\bsolution\b", r"\balternative\b"]
    o = _count(text, obj); h = _count(text, hand)
    if o == 0: return 7.0
    r = h / max(o, 1)
    if r >= 2: return 10.0
    if r >= 1: return 8.0
    if r >= 0.5: return 6.0
    if r > 0: return 4.0
    return 2.0

def score_energie(text):
    pos = [r"\bexcellent\b", r"\bparfait\b", r"\bsuper\b", r"\bgénial\b",
           r"\bfantastique\b", r"\bbravo\b", r"\bbienvenue\b", r"\bfélicitations\b",
           r"\bavec plaisir\b", r"\bcertainement\b", r"\bformidable\b",
           r"\bça me fait plaisir\b", r"\bmerveilleux\b"]
    enc = [r"\bvous (allez|êtes) (voir|sur|capable)\b", r"\bc'est (une|la) bonne\b", r"\bbon choix\b"]
    ex = min(text.count("!"), 10)
    return _norm(_count(text, pos) * 1.5 + _count(text, enc) * 2 + ex * 0.2, high=10)

def score_engagement(text):
    # Dialogue quality: back-and-forth, personalization, open questions
    sents = [s.strip() for s in re.split(r'[.!?]+', text) if len(s.strip()) > 5]
    q = text.count("?")
    # Open-ended questions (higher quality than yes/no)
    open_q = len(re.findall(r"\b(qu'est-ce|comment|pourquoi|quel|que pensez|parlez-moi)\b.*\?", text, re.I))
    # Personalization signals
    personal = _count(text, [r"\bdans votre cas\b", r"\bpour vous\b", r"\bvous personnellement\b",
                             r"\bvotre situation\b", r"\bselon (votre|vos)\b"])
    # Sentence count as dialogue flow indicator
    flow = min(4, len(sents) * 0.08)
    q_score = min(3, open_q * 1.0 + (q - open_q) * 0.3)
    personal_score = min(3, personal * 1.0)
    return round(min(10.0, flow + q_score + personal_score), 1)


def score_empathie(text):
    """Emotional support, compassion, de-escalation."""
    empathy = [r"\bje suis désolé\b", r"\bje m'excuse\b", r"\btoutes mes excuses\b",
               r"\bje comprends votre (frustration|situation|inquiétude)\b",
               r"\bc'est normal de\b", r"\bje comprends que c'est\b",
               r"\bon va (régler|trouver|s'occuper de) ça\b", r"\bpas de (problème|souci)\b",
               r"\bje suis (là|ici) pour\b", r"\bne vous inquiétez pas\b",
               r"\bje vous assure\b", r"\bprenez votre temps\b",
               r"\bça arrive\b", r"\bje comprends tout à fait\b"]
    return _norm(_count(text, empathy) * 1.5, high=8)


def score_connaissance_produit(text):
    """XGuard product knowledge — mentions specific formations, requirements, details."""
    products = [r"\bgardiennage\b", r"\bsécurité privée\b", r"\bBSP\b", r"\bbureau de la sécurité\b",
                r"\bsecourisme\b", r"\bRCR\b", r"\bpremiers soins\b",
                r"\bdrone\b", r"\bélite\b", r"\bpilote de drone\b",
                r"\bformation en ligne\b", r"\bprésentiel\b", r"\ben classe\b",
                r"\b70 heures\b", r"\b16 heures\b", r"\bcarte (ASP|de gardien)\b",
                r"\bpermis (de|d'agent)\b", r"\bcertification\b", r"\baccrédité\b",
                r"\bexamen\b", r"\battestation\b", r"\bdiplôme\b"]
    details = [r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b.*\b(au|à)\b",
               r"\b\d{1,2}\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\b",
               r"\b(350|400|450|500)\s*\$\b",
               r"\b(montréal|québec|laval|gatineau|en ligne)\b"]
    return _norm(_count(text, products) * 1.0 + _count(text, details) * 1.5, high=10)


def score_suivi(text):
    """Follow-up commitment + clear next steps."""
    followup = [r"\bje vais vous rappeler\b", r"\bje vous rappelle\b",
                r"\bvous (allez |)recevr(ez|a) un (courriel|email|message)\b",
                r"\bje vous envoie\b", r"\bje note\b", r"\bj'ai pris en note\b",
                r"\bprochaine étape\b", r"\bon se reparle\b",
                r"\bn'hésitez pas à (rappeler|nous contacter|revenir)\b",
                r"\bje vais (vérifier|m'informer) et\b",
                r"\bd'ici (lundi|mardi|demain|la fin|ce soir)\b",
                r"\bje vous (tiens|tiendrai) au courant\b"]
    return _norm(_count(text, followup) * 2.0, high=8)


def score_call(text: str, duration_s: int) -> dict:
    """Score a single call on all 13 SAC dimensions. Returns {dim: score}."""
    return {
        "accueil": score_accueil(text),
        "ecoute": score_ecoute(text),
        "resolution": score_resolution(text),
        "patience": score_patience(duration_s),
        "professionnalisme": score_professionnalisme(text),
        "vente_subtile": score_vente_subtile(text),
        "qualification": score_qualification(text),
        "gestion_objections": score_gestion_objections(text),
        "energie": score_energie(text),
        "engagement": score_engagement(text),
        "empathie": score_empathie(text),
        "connaissance_produit": score_connaissance_produit(text),
        "suivi": score_suivi(text),
    }


def global_score(scores: dict) -> float:
    """Weighted average — SAC core dims weighted higher than sales dims."""
    total_weight = 0
    weighted_sum = 0
    for dim, val in scores.items():
        if isinstance(val, (int, float)):
            w = DIM_WEIGHTS.get(dim, 1.0)
            weighted_sum += val * w
            total_weight += w
    return round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0

# ---------------------------------------------------------------------------
# Objection normalization
# ---------------------------------------------------------------------------

OBJECTION_CATEGORIES = [
    (r"c'est trop cher|pas le budget|pas les moyens|coût|cher", "prix", "Prix/Budget"),
    (r"je vais réfléchir|pas encore décidé|y penser", "reflexion", "Réflexion"),
    (r"pas le temps|pas disponible|occupé", "temps", "Temps/Disponibilité"),
    (r"déjà.*formation|déjà.*carte|déjà fait|déjà.*cours", "deja_fait", "Déjà fait"),
    (r"mécontent|insatisfait|plainte|problème grave", "plainte", "Plainte/Mécontentement"),
    (r"pas intéressé|ça ne m'intéresse|non merci", "pas_interesse", "Pas intéressé"),
    (r"rappeler plus tard|un autre moment|rappelez", "reporter", "Reporter"),
]

COACHING_RESPONSES = {
    "prix": "Je comprends que c'est un investissement. Ce qui est bien, c'est que cette certification vous ouvre des portes pour l'emploi. On a aussi des options de paiement flexibles.",
    "reflexion": "Bien sûr, prenez le temps. Par contre, les places partent vite. Voulez-vous que je vous réserve une place sans engagement?",
    "temps": "Je comprends. On offre des horaires flexibles: soirs et weekends. Quelle plage vous conviendrait le mieux?",
    "deja_fait": "Parfait! Alors vous connaissez déjà le domaine. Est-ce que vous cherchez à renouveler votre certification ou à ajouter une spécialisation?",
    "plainte": "Je suis désolé pour cette situation. Laissez-moi noter votre préoccupation et on va trouver une solution ensemble.",
    "pas_interesse": "Pas de problème. Si jamais votre situation change, n'hésitez pas à nous rappeler. Bonne journée!",
    "reporter": "Absolument. Quand est-ce que ça vous conviendrait que je vous rappelle? Je vais noter ça.",
}

def detect_objections_normalized(text: str) -> list:
    """Returns list of (category, raw_match) tuples found in text."""
    found = []
    for pattern, category, label in OBJECTION_CATEGORIES:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            found.append((category, matches[0] if isinstance(matches[0], str) else matches[0]))
    return found

# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------

DIMENSION_RECOMMENDATIONS = {
    "accueil": ("Standardiser l'accueil: 'Bonjour, [prénom] de l'Académie XGuard, comment puis-je vous aider?'", 6),
    "ecoute": ("Pratiquer la reformulation: 'Si je comprends bien, vous cherchez...' avant de répondre", 5),
    "resolution": ("Toujours confirmer la résolution: 'Est-ce que ça répond à votre question?' avant de raccrocher", 5),
    "vente_subtile": ("Quand un prospect demande des infos, mentionner les prochaines dates disponibles et proposer l'inscription", 4),
    "professionnalisme": ("Terminer chaque appel par 'Merci d'avoir appelé, bonne journée!' et 'N'hésitez pas à nous rappeler'", 5),
    "qualification": ("Avant de répondre, poser 2-3 questions: situation actuelle, besoin spécifique, disponibilité", 5),
    "energie": ("Utiliser des mots positifs naturels: 'Excellent choix!', 'C'est parfait!', 'Bienvenue!'", 4),
    "engagement": ("Poser des questions ouvertes: 'Qu'est-ce qui vous a intéressé dans cette formation?'", 5),
    "gestion_objections": ("Dire: 'Je comprends tout à fait, c'est une bonne question. En fait, [réponse avec solution]...'", 5),
    "patience": ("Prendre le temps d'expliquer calmement. Un client bien servi revient ou réfère.", 4),
    "empathie": ("Dire: 'Je comprends votre frustration' ou 'C'est normal de se sentir ainsi'. Reconnaitre l'émotion avant de résoudre.", 5),
    "connaissance_produit": ("Mentionner les détails: durée (70h gardiennage), prochaines dates, prix, carte BSP. Montrer qu'on connait nos formations.", 5),
    "suivi": ("Toujours proposer une prochaine étape: 'Je vous envoie un courriel' ou 'Je vous rappelle demain à 10h'", 5),
}

def generate_recommendations(avg_scores: dict) -> list:
    """Generate recommendations for dimensions below threshold."""
    recs = []
    for dim, (rec, threshold) in DIMENSION_RECOMMENDATIONS.items():
        if avg_scores.get(dim, 10) < threshold:
            recs.append({"dimension": dim, "recommendation": rec, "current_score": avg_scores.get(dim, 0)})
    return recs
