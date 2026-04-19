"""
ghl_helpers.py — Shared GoHighLevel API helpers.

Centralizes GHL operations so multiple scripts can reuse them:
- ghl_find_contact_by_email(email)
- ghl_get_contact(contact_id)
- ghl_create_contact(email, first_name, last_name, phone, tags)
- ghl_add_tag(contact_id, tag)
- ghl_has_tag(contact, tag)

All respect 0.3s rate limiting between calls.
"""

import logging
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

import requests

from kb_config import GHL_BASE, GHL_HEADERS, GHL_LOCATION

log = logging.getLogger("ghl_helpers")

# Rate limiting
_last_call = [0.0]
MIN_SLEEP_SEC = 0.3


def _rate_limit():
    """Sleep if less than MIN_SLEEP_SEC since last call."""
    elapsed = time.time() - _last_call[0]
    if elapsed < MIN_SLEEP_SEC:
        time.sleep(MIN_SLEEP_SEC - elapsed)
    _last_call[0] = time.time()


def _request(method, path, **kwargs):
    """Make a GHL API request with rate limiting + retries on 429/500."""
    _rate_limit()
    url = f"{GHL_BASE}{path}"
    for attempt in range(3):
        try:
            r = requests.request(method, url, headers=GHL_HEADERS, timeout=30, **kwargs)
            if r.status_code in (429, 500, 502, 503):
                backoff = (attempt + 1) * 2
                log.warning("GHL %s %s -> %d (retry in %ds)", method, path, r.status_code, backoff)
                time.sleep(backoff)
                continue
            return r
        except requests.exceptions.RequestException as e:
            log.warning("GHL %s %s network error (attempt %d): %s", method, path, attempt + 1, e)
            if attempt < 2:
                time.sleep(2)
                continue
            raise
    return r  # last response even if failed


def ghl_find_contact_by_email(email):
    """Find a GHL contact by email. Returns contact dict or None.
    If multiple matches, returns the newest (by dateAdded).
    """
    if not email:
        return None

    email = email.lower().strip()

    # GHL search endpoint: /contacts/?locationId=X&query=email
    r = _request("GET", "/contacts/", params={
        "locationId": GHL_LOCATION,
        "query": email,
        "limit": 20,
    })

    if r.status_code != 200:
        log.warning("GHL search %s -> %d: %s", email, r.status_code, r.text[:200])
        return None

    contacts = r.json().get("contacts", [])
    if not contacts:
        return None

    # Filter: exact email match (case-insensitive)
    exact = [c for c in contacts if (c.get("email") or "").lower().strip() == email]
    if not exact:
        return None

    # If multiple, return newest by dateAdded
    if len(exact) > 1:
        exact.sort(key=lambda c: c.get("dateAdded", ""), reverse=True)
        log.info("GHL: %d contacts with email %s, using newest (id=%s)",
                 len(exact), email, exact[0].get("id"))

    return exact[0]


def ghl_get_contact(contact_id):
    """Get full contact details by ID."""
    r = _request("GET", f"/contacts/{contact_id}")
    if r.status_code != 200:
        log.warning("GHL get contact %s -> %d", contact_id, r.status_code)
        return None
    return r.json().get("contact")


def ghl_create_contact(email, first_name=None, last_name=None, phone=None, tags=None):
    """Create a new contact in GHL with optional tags.
    Returns the created contact dict or None on failure.
    """
    if not email:
        return None

    body = {
        "locationId": GHL_LOCATION,
        "email": email.lower().strip(),
    }
    if first_name:
        body["firstName"] = first_name
    if last_name:
        body["lastName"] = last_name
    if phone:
        body["phone"] = phone
    if tags:
        body["tags"] = tags

    r = _request("POST", "/contacts/", json=body)

    if r.status_code in (200, 201):
        data = r.json()
        return data.get("contact") or data
    # 400 with "Duplicated contacts" = contact already exists
    if r.status_code == 400 and "duplicat" in r.text.lower():
        log.info("GHL create: %s already exists, searching instead", email)
        return ghl_find_contact_by_email(email)

    log.error("GHL create %s -> %d: %s", email, r.status_code, r.text[:300])
    return None


def ghl_add_tag(contact_id, tag):
    """Add a tag to a contact (additive — doesn't replace other tags).
    Returns True on success.
    """
    if not contact_id or not tag:
        return False

    r = _request("POST", f"/contacts/{contact_id}/tags", json={"tags": [tag]})

    if r.status_code in (200, 201):
        return True

    log.warning("GHL add_tag %s/%s -> %d: %s", contact_id, tag, r.status_code, r.text[:200])
    return False


def ghl_remove_tag(contact_id, tag):
    """Remove a tag from a contact.
    Returns True on success.
    """
    if not contact_id or not tag:
        return False

    r = _request("DELETE", f"/contacts/{contact_id}/tags", json={"tags": [tag]})

    if r.status_code in (200, 201, 204):
        return True

    log.warning("GHL remove_tag %s/%s -> %d: %s", contact_id, tag, r.status_code, r.text[:200])
    return False


def ghl_has_tag(contact, tag):
    """Check if a contact dict has a tag (case-insensitive)."""
    if not contact or not tag:
        return False
    tags = contact.get("tags") or []
    tag_lower = tag.lower().strip()
    return any((t or "").lower().strip() == tag_lower for t in tags)


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    import sys

    if len(sys.argv) < 2:
        print("Usage: python ghl_helpers.py <email>")
        sys.exit(1)

    email = sys.argv[1]
    c = ghl_find_contact_by_email(email)
    if c:
        print(f"Found contact:")
        print(f"  ID: {c.get('id')}")
        print(f"  Name: {c.get('firstName', '')} {c.get('lastName', '')}")
        print(f"  Email: {c.get('email')}")
        print(f"  Phone: {c.get('phone')}")
        print(f"  Tags: {c.get('tags')}")
        print(f"  Has 'xguard paid' tag: {ghl_has_tag(c, 'xguard paid')}")
    else:
        print(f"No contact found for: {email}")
