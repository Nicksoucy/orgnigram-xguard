"""
sms_validator.py — Validate Haiku-generated SMS before sending to customers.

Checks:
1. Length: 30-320 chars (SMS standard max with Unicode)
2. Must contain the XGuard phone number "(438) 802-0475" or variants
3. No toxic/profane language (French + English wordlist)
4. No unauthorized prices or financial promises
5. No PII of OTHER people leaked (emails, other phone numbers)
6. No quotes/markup artifacts from Haiku
7. Must start with "Bonjour"

Returns (is_valid: bool, reason: str or None).

USED BY: smart_hot_leads.py before calling send_sms().
"""

import re

# Expected phone number (accept multiple formats Haiku might produce)
VALID_PHONE_PATTERNS = [
    r'\(438\)\s*802[\-\s]?0475',
    r'438[\-\s]802[\-\s]0475',
    r'4388020475',
    r'1?\s*438\s*802\s*0475',
]

# Hard blockers — reject if ANY of these appears
TOXIC_WORDS_FR = {
    'tabarnak', 'calisse', 'crisse', 'osti', 'ostie', 'caliss', 'estie',
    'fuck', 'shit', 'damn', 'hell', 'bitch', 'asshole',
    'idiot', 'stupide', 'con', 'conne', 'imbecile', 'cretin',
    'merde', 'putain', 'salope',
}

# Words suggesting unauthorized promises — reject
PROMISE_WORDS = {
    'garantie', 'garanti', 'garantis', 'guarantee', 'guaranteed',
    '100%', 'assure', 'assurez-vous',
    'rabais', 'rabais exclusif', 'discount', 'promo', 'promotion',
    'gratuit', 'gratuite', 'free',
    'offre limitee', 'limited offer', 'derniere chance', 'last chance',
}

# Authorized prices (if Haiku mentions a price, it must be one of these)
AUTHORIZED_PRICES_REGEX = re.compile(
    r'\$\s*(3[0-9]{2}|4[0-9]{2}|5[0-9]{2}|6[0-9]{2}|7[0-9]{2})(?:[\.,]\d{2})?',
    re.IGNORECASE,
)  # Prices $300-$799 are authorized. Others need to match this pattern.

# Markdown/quote artifacts
MARKDOWN_ARTIFACTS = [
    '**', '__', '##', '```', '> ', '- ', '* ', '`',
]

# Email regex (to detect leaked email addresses)
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

# Phone regex (to detect OTHER phone numbers that aren't ours)
OTHER_PHONE_RE = re.compile(r'\b(?!438)\d{3}[\-\s]?\d{3}[\-\s]?\d{4}\b')


def validate_sms(sms_body, recipient_name=None):
    """Validate a generated SMS body.

    Args:
        sms_body: the SMS text from Haiku
        recipient_name: optional, the prospect's name (used for personalization check)

    Returns:
        (is_valid, reason): reason is None if valid, else a short string.
    """
    if not sms_body:
        return False, "empty SMS"

    text = sms_body.strip()

    # Length
    if len(text) < 30:
        return False, f"too short ({len(text)} chars)"
    if len(text) > 320:
        return False, f"too long ({len(text)} chars)"

    lower = text.lower()

    # Must start with Bonjour
    if not lower.startswith("bonjour"):
        return False, "doesn't start with Bonjour"

    # Must contain our phone
    has_phone = any(re.search(p, text, re.IGNORECASE) for p in VALID_PHONE_PATTERNS)
    if not has_phone:
        return False, "missing XGuard phone (438) 802-0475"

    # Toxic language
    for word in TOXIC_WORDS_FR:
        # Word boundary to avoid false positives (e.g. "constamment" containing "con")
        if re.search(rf'\b{re.escape(word)}\b', lower):
            return False, f"toxic word detected: '{word}'"

    # Unauthorized promises
    for word in PROMISE_WORDS:
        if word in lower:
            return False, f"unauthorized promise: '{word}'"

    # Unauthorized prices (if ANY dollar sign, must match authorized pattern)
    if '$' in text:
        prices = re.findall(r'\$\s*\d+(?:[\.,]\d{2})?', text)
        for p in prices:
            if not AUTHORIZED_PRICES_REGEX.match(p):
                return False, f"unauthorized price: '{p}'"

    # Markdown artifacts
    for art in MARKDOWN_ARTIFACTS:
        if art in text:
            return False, f"markdown artifact: '{art}'"

    # Leaked emails (SMS should not contain email addresses — feels spammy)
    if EMAIL_RE.search(text):
        return False, "contains email address (suspicious)"

    # Other phone numbers (only ours should appear)
    other_phones = OTHER_PHONE_RE.findall(text)
    if other_phones:
        return False, f"contains other phone number: {other_phones[0]}"

    # Unclosed quotes
    if text.count('"') % 2 != 0:
        return False, "unclosed double quote"
    if text.count("'") % 2 != 0:
        # Allow apostrophes in French ("l'", "d'", "n'") — count only straight singles as pairs
        # Check if there are suspicious sequences
        if '"' in text or "''" in text:
            return False, "unclosed single quote"

    # Bracket placeholder not filled (e.g. "[prenom]", "[nom]")
    if re.search(r'\[[a-z_]+\]', lower):
        return False, "unfilled placeholder (e.g., [prenom])"

    return True, None


if __name__ == "__main__":
    # Smoke test
    import sys
    test_cases = [
        ("Bonjour Jean, merci pour votre appel! On est disponible pour repondre a vos questions. Appelez-nous au (438) 802-0475 — Academie XGuard", True),
        ("Bonjour Marie, votre formation est garantie 100%! Appelez au (438) 802-0475", False),  # garantie
        ("Hi there", False),  # no Bonjour, too short
        ("Hello, call us", False),  # no Bonjour, no phone
        ("Bonjour Jean, [prenom] votre formation. Appelez au (438) 802-0475.", False),  # unfilled placeholder
        ("Bonjour Jean, tabarnak appelez-nous au (438) 802-0475.", False),  # toxic
        ("Bonjour Jean, voici l'info au (438) 802-0475 de la part de l'Academie", True),  # apostrophes OK
    ]
    for sms, expected in test_cases:
        ok, reason = validate_sms(sms)
        status = "PASS" if ok == expected else "FAIL"
        print(f"{status} expected={expected} got={ok} reason={reason or 'OK'}")
        print(f"   SMS: {sms[:80]}")
