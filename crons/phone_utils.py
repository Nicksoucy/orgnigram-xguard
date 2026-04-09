"""Shared phone number normalization for cross-referencing JustCall, GHL, and Supabase."""

import re


def normalize_number(num):
    """Normalize phone number to 10-digit for matching across systems.
    Handles: "+1 438 123-4567", "14381234567", "(438) 123-4567", etc.
    Returns last 10 digits or original if too short.
    """
    if not num:
        return ""
    num = re.sub(r"[\s\-\(\)\.\+]", "", str(num).strip())
    if num.startswith("+1"):
        num = num[2:]
    elif num.startswith("1") and len(num) == 11:
        num = num[1:]
    return num[-10:] if len(num) >= 10 else num


def format_display(num):
    """Format 10-digit number for display: (438) 123-4567"""
    n = normalize_number(num)
    if len(n) == 10:
        return f"({n[:3]}) {n[3:6]}-{n[6:]}"
    return num or ""
