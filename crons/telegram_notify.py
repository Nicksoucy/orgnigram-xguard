"""
Telegram Notifications — Shared module for all XGuard crons.
Send alerts on cron success/failure, errors, and daily summaries.

Usage:
    from telegram_notify import notify, notify_cron_result, notify_error
    notify("Hello from Nitro!")
    notify_cron_result("sac_daily", "success", "86 calls transcribed, 3 failed")
    notify_error("kb_analyzer", "IMAP connection failed")
"""

import logging
import requests

log = logging.getLogger("telegram")

BOT_TOKEN = "8040724534:AAHRLbkH2v0ji0swXQlv1aNrSxUXCwobRps"
CHAT_ID = None  # Will be discovered on first run
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def _discover_chat_id():
    """Get chat_id from the most recent message to the bot."""
    global CHAT_ID
    if CHAT_ID:
        return CHAT_ID
    try:
        r = requests.get(f"{API_URL}/getUpdates", timeout=10)
        if r.status_code == 200:
            updates = r.json().get("result", [])
            for u in reversed(updates):
                msg = u.get("message", {})
                chat = msg.get("chat", {})
                if chat.get("id"):
                    CHAT_ID = chat["id"]
                    log.info("Telegram chat_id discovered: %s", CHAT_ID)
                    return CHAT_ID
    except Exception as e:
        log.warning("Telegram chat_id discovery failed: %s", e)
    return None


def notify(message, silent=False):
    """Send a text message via Telegram."""
    chat_id = _discover_chat_id()
    if not chat_id:
        log.warning("Telegram: no chat_id, cannot send message")
        return False
    try:
        r = requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
            "disable_notification": silent,
        }, timeout=10)
        if r.status_code == 200:
            return True
        log.warning("Telegram send failed (%d): %s", r.status_code, r.text[:100])
        return False
    except Exception as e:
        log.warning("Telegram send error: %s", e)
        return False


def notify_cron_result(script, status, details=""):
    """Send formatted cron result notification."""
    icon = {"success": "\u2705", "error": "\u274c", "partial": "\u26a0\ufe0f", "paused": "\u23f8"}.get(status, "\u2753")
    msg = f"{icon} <b>{script}</b> — {status.upper()}\n{details}" if details else f"{icon} <b>{script}</b> — {status.upper()}"
    return notify(msg)


def notify_error(script, error_msg):
    """Send error alert (not silent)."""
    msg = f"\u274c <b>ERREUR: {script}</b>\n{error_msg[:500]}"
    return notify(msg, silent=False)


def notify_daily_summary(stats):
    """Send daily summary at 8h."""
    lines = ["\U0001f4ca <b>Resume quotidien Nitro</b>"]
    for name, info in stats.items():
        icon = "\u2705" if info.get("status") == "success" else "\u274c"
        lines.append(f"  {icon} {name}: {info.get('detail', '')}")
    return notify("\n".join(lines))


# --- CLI test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    chat_id = _discover_chat_id()
    if chat_id:
        print(f"Chat ID: {chat_id}")
        ok = notify("\U0001f916 <b>XGuard Nitro</b> - Telegram connecte!\nLes notifications de crons seront envoyees ici.")
        if ok:
            print("Test message sent!")
        else:
            print("Failed to send test message")
    else:
        print("No chat_id found. Please send /start to @Xguard_claude_bot first.")
