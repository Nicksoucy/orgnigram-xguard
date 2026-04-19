"""
telegram_bot.py — Telegram bot API wrapper for SMS approval workflow.

Core operations:
  - send_approval_message(approval_id, sms_body, context) -> posts message with 4 buttons
  - poll_for_callbacks() -> checks updates, updates Supabase with decisions
  - delete_message(message_id) -> cleanup after decision made

Uses ton bot existant @Xguard_claude_bot (token in config).
Chat ID resolution: first user to /start becomes authorized.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent))

from kb_config import sb_get, sb_upsert, sb_patch

log = logging.getLogger("telegram_bot")

# Telegram bot config (from session recap — already created)
TELEGRAM_BOT_TOKEN = "8040724534:AAHRLbkH2v0ji0swXQlv1aNrSxUXCwobRps"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# File to persist the last-processed update_id (avoid reprocessing)
UPDATES_STATE_FILE = Path(r"C:\Users\user\crons\secrets\telegram_last_update.json")


# ---------------------------------------------------------------------------
# State file: last processed update_id
# ---------------------------------------------------------------------------

def _load_last_update_id():
    try:
        if UPDATES_STATE_FILE.exists():
            return json.loads(UPDATES_STATE_FILE.read_text()).get("last_update_id", 0)
    except Exception:
        pass
    return 0


def _save_last_update_id(update_id):
    try:
        UPDATES_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        UPDATES_STATE_FILE.write_text(json.dumps({"last_update_id": update_id}))
    except Exception as e:
        log.warning("Failed to save last_update_id: %s", e)


# ---------------------------------------------------------------------------
# Authorized chats (who can approve SMS)
# ---------------------------------------------------------------------------

AUTHORIZED_CHATS_FILE = Path(r"C:\Users\user\crons\secrets\telegram_authorized.json")


def _load_authorized_chats():
    """Load list of chat_ids allowed to approve SMS."""
    try:
        if AUTHORIZED_CHATS_FILE.exists():
            return set(json.loads(AUTHORIZED_CHATS_FILE.read_text()).get("chats", []))
    except Exception:
        pass
    return set()


def _save_authorized_chats(chat_ids):
    try:
        AUTHORIZED_CHATS_FILE.parent.mkdir(parents=True, exist_ok=True)
        AUTHORIZED_CHATS_FILE.write_text(json.dumps({"chats": list(chat_ids)}))
    except Exception as e:
        log.warning("Failed to save authorized chats: %s", e)


def authorize_chat(chat_id):
    """Add a chat to the authorized list (first-time pairing)."""
    chats = _load_authorized_chats()
    chats.add(int(chat_id))
    _save_authorized_chats(chats)


def is_authorized(chat_id):
    chats = _load_authorized_chats()
    # If no one is authorized yet, first /start wins (bootstrap)
    if not chats:
        return True
    return int(chat_id) in chats


# ---------------------------------------------------------------------------
# Telegram API wrappers
# ---------------------------------------------------------------------------

def _api(method, **kwargs):
    """Call Telegram Bot API. Returns response JSON or None."""
    url = f"{TELEGRAM_API}/{method}"
    try:
        r = requests.post(url, json=kwargs, timeout=20)
        data = r.json()
        if not data.get("ok"):
            log.warning("Telegram %s failed: %s", method, data.get("description"))
            return None
        return data.get("result")
    except Exception as e:
        log.error("Telegram %s exception: %s", method, e)
        return None


def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Send a message to a Telegram chat. Returns the sent message dict."""
    kwargs = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    return _api("sendMessage", **kwargs)


def edit_message_text(chat_id, message_id, text, reply_markup=None, parse_mode="HTML"):
    """Edit an existing message."""
    kwargs = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    if reply_markup is not None:
        kwargs["reply_markup"] = reply_markup
    return _api("editMessageText", **kwargs)


def answer_callback_query(callback_query_id, text=None, show_alert=False):
    """Acknowledge a button click. Required by Telegram API."""
    kwargs = {"callback_query_id": callback_query_id}
    if text:
        kwargs["text"] = text
    if show_alert:
        kwargs["show_alert"] = True
    return _api("answerCallbackQuery", **kwargs)


def get_updates(offset=None, timeout=0):
    """Poll for updates. offset = last_update_id + 1 to skip already-processed."""
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        r = requests.get(f"{TELEGRAM_API}/getUpdates", params=params, timeout=timeout + 10)
        data = r.json()
        if not data.get("ok"):
            log.warning("getUpdates failed: %s", data.get("description"))
            return []
        return data.get("result", [])
    except Exception as e:
        log.error("getUpdates exception: %s", e)
        return []


# ---------------------------------------------------------------------------
# Approval message builders
# ---------------------------------------------------------------------------

def _build_approval_keyboard(approval_id):
    """4-button inline keyboard for an approval decision."""
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve:{approval_id}"},
                {"text": "❌ Reject", "callback_data": f"reject:{approval_id}"},
            ],
            [
                {"text": "✏️ Edit", "callback_data": f"edit:{approval_id}"},
                {"text": "🔄 Refine", "callback_data": f"refine:{approval_id}"},
            ],
        ]
    }


def _format_approval_message(approval):
    """Format the Telegram message for an approval request."""
    name = approval.get("contact_name") or "Inconnu"
    phone = approval.get("phone_number", "")
    display_phone = f"+1{phone}" if len(phone) == 10 else phone
    context = approval.get("context_summary", "")
    priority = approval.get("priority", "")
    sms = approval.get("sms_body", "")
    version = approval.get("version", 1)

    version_tag = f" (v{version})" if version > 1 else ""

    return (
        f"<b>📱 SMS a envoyer{version_tag}</b>\n"
        f"Priorite: <code>{priority}</code>\n\n"
        f"<b>Contact:</b> {name}\n"
        f"<b>Phone:</b> {display_phone}\n"
        f"<b>Contexte:</b> <i>{context}</i>\n\n"
        f"<b>Message:</b>\n"
        f"<pre>{sms}</pre>"
    )


def send_approval_request(approval_id, chat_id=None):
    """Fetch approval from DB, format message, send to Telegram with buttons.
    Returns the telegram message_id, or None on failure.
    """
    rows = sb_get(f"pending_sms_approvals?id=eq.{approval_id}&limit=1")
    if not rows or isinstance(rows, dict):
        log.error("Approval %s not found", approval_id)
        return None
    approval = rows[0]

    text = _format_approval_message(approval)
    keyboard = _build_approval_keyboard(approval_id)

    # If no chat_id specified, send to all authorized chats
    chats = [chat_id] if chat_id else list(_load_authorized_chats())
    if not chats:
        log.warning("No authorized chats to send approval to! Run /start on Telegram bot first.")
        return None

    first_msg_id = None
    for cid in chats:
        result = send_message(cid, text, reply_markup=keyboard)
        if result:
            msg_id = result.get("message_id")
            if first_msg_id is None:
                first_msg_id = msg_id
            # Update Supabase with telegram info (only for first authorized chat)
            sb_patch(
                "pending_sms_approvals",
                f"id=eq.{approval_id}",
                {
                    "telegram_message_id": msg_id,
                    "telegram_chat_id": cid,
                },
            )

    return first_msg_id


# ---------------------------------------------------------------------------
# Decision handlers (called by polling loop)
# ---------------------------------------------------------------------------

def handle_approve(approval_id, chat_id, message_id, username):
    """User clicked Approve."""
    rows = sb_get(f"pending_sms_approvals?id=eq.{approval_id}&limit=1")
    if not rows or isinstance(rows, dict):
        return False
    approval = rows[0]

    sb_patch(
        "pending_sms_approvals",
        f"id=eq.{approval_id}",
        {
            "status": "approved",
            "decided_at": _now_iso(),
            "decided_by": username or "unknown",
        },
    )

    edit_message_text(
        chat_id, message_id,
        _format_approval_message(approval) + "\n\n✅ <b>APPROUVE</b> — sera envoye au prochain cycle (30min).",
        reply_markup=None,
    )
    return True


def handle_reject(approval_id, chat_id, message_id, username):
    rows = sb_get(f"pending_sms_approvals?id=eq.{approval_id}&limit=1")
    if not rows or isinstance(rows, dict):
        return False
    approval = rows[0]

    sb_patch(
        "pending_sms_approvals",
        f"id=eq.{approval_id}",
        {
            "status": "rejected",
            "decided_at": _now_iso(),
            "decided_by": username or "unknown",
        },
    )

    edit_message_text(
        chat_id, message_id,
        _format_approval_message(approval) + "\n\n❌ <b>REJETE</b> — pas envoye.",
        reply_markup=None,
    )
    return True


def handle_edit_request(approval_id, chat_id, message_id, username):
    """User clicked Edit — mark as waiting for user to reply with custom text."""
    sb_patch(
        "pending_sms_approvals",
        f"id=eq.{approval_id}",
        {"status": "edited", "decided_by": username or "unknown"},
    )

    # Tell user to reply to this message with the new SMS text
    rows = sb_get(f"pending_sms_approvals?id=eq.{approval_id}&limit=1")
    approval = rows[0] if rows and not isinstance(rows, dict) else {}

    edit_message_text(
        chat_id, message_id,
        _format_approval_message(approval) +
        f"\n\n✏️ <b>EDIT MODE</b>\n\nReponds a ce message avec le texte SMS que tu veux envoyer. Commande: <code>/edit {approval_id} [ton texte]</code>",
        reply_markup=None,
    )
    return True


def handle_refine_request(approval_id, chat_id, message_id, username):
    """User clicked Refine — ask for feedback, regenerate."""
    sb_patch(
        "pending_sms_approvals",
        f"id=eq.{approval_id}",
        {"status": "refine_requested", "decided_by": username or "unknown"},
    )

    rows = sb_get(f"pending_sms_approvals?id=eq.{approval_id}&limit=1")
    approval = rows[0] if rows and not isinstance(rows, dict) else {}

    edit_message_text(
        chat_id, message_id,
        _format_approval_message(approval) +
        f"\n\n🔄 <b>REFINE MODE</b>\n\nReponds avec ton feedback. Commande: <code>/refine {approval_id} [ton feedback]</code>\n\nEx: <code>/refine {approval_id} plus court, moins formel</code>",
        reply_markup=None,
    )
    return True


def handle_custom_edit(approval_id, new_text, chat_id, username):
    """User sent /edit <id> <text> — replace SMS body with their version."""
    from sms_validator import validate_sms

    # Validate the edited text
    ok, reason = validate_sms(new_text)
    if not ok:
        send_message(chat_id,
            f"❌ Le texte propose ne passe pas la validation: <b>{reason}</b>\n\nRe-envoie avec <code>/edit {approval_id} [texte corrige]</code>",
        )
        return False

    sb_patch(
        "pending_sms_approvals",
        f"id=eq.{approval_id}",
        {
            "sms_body": new_text,
            "status": "approved",  # Edited = auto-approved
            "decided_at": _now_iso(),
            "decided_by": username or "unknown",
            "user_feedback": f"EDITED by {username}",
        },
    )

    send_message(chat_id,
        f"✅ <b>Edit accepte, SMS approuve.</b>\n\n<pre>{new_text}</pre>\n\nSera envoye au prochain cycle (30 min).",
    )
    return True


def handle_refine_feedback(approval_id, feedback, chat_id, username):
    """User sent /refine <id> <feedback> — regenerate SMS with this guidance."""
    from claude_scoring import call_claude

    rows = sb_get(f"pending_sms_approvals?id=eq.{approval_id}&limit=1")
    if not rows or isinstance(rows, dict):
        send_message(chat_id, f"❌ Approval {approval_id} introuvable.")
        return False
    approval = rows[0]

    # Build refinement prompt: original SMS + user feedback
    prompt = f"""Tu as propose ce SMS a l'utilisateur:
<SMS>
{approval['sms_body']}
</SMS>

L'utilisateur a demande une amelioration avec ce feedback:
<FEEDBACK>
{feedback}
</FEEDBACK>

Re-ecris le SMS en appliquant le feedback. Garde ces regles:
- Angle service (pas de vente pushy)
- Tutoiement Quebec naturel
- Max 320 caracteres
- Pas d'emojis, pas de markdown, pas de guillemets
- Contient "(438) 802-0475"
- Commence par "Bonjour"

Retourne UNIQUEMENT le nouveau texte du SMS."""

    new_sms = call_claude(prompt, model="haiku", timeout=45)
    if not new_sms:
        send_message(chat_id, f"❌ Haiku n'a pas repondu. Reessaie ou utilise /edit.")
        return False

    new_sms = new_sms.strip().strip('"').strip("'")

    # Validate
    from sms_validator import validate_sms
    ok, reason = validate_sms(new_sms)
    if not ok:
        send_message(chat_id,
            f"❌ Le SMS refine ne passe pas la validation: <b>{reason}</b>\n\n<pre>{new_sms}</pre>\n\nReessaie avec un feedback different.",
        )
        return False

    # Create a NEW approval (version+1) — keep the old one for audit
    new_approval = {
        "phone_number": approval["phone_number"],
        "contact_name": approval["contact_name"],
        "ghl_contact_id": approval.get("ghl_contact_id"),
        "prospect_id": approval.get("prospect_id"),
        "sms_body": new_sms,
        "context_summary": approval.get("context_summary"),
        "priority": approval.get("priority"),
        "status": "pending",
        "version": (approval.get("version", 1) or 1) + 1,
        "parent_approval_id": approval_id,
        "user_feedback": feedback,
        "run_date": approval.get("run_date"),
    }
    sb_upsert("pending_sms_approvals", new_approval)

    # Find the new approval's ID
    latest = sb_get(
        f"pending_sms_approvals?parent_approval_id=eq.{approval_id}"
        f"&order=id.desc&limit=1"
    )
    if latest and not isinstance(latest, dict):
        new_id = latest[0]["id"]
        send_approval_request(new_id, chat_id=chat_id)
    else:
        send_message(chat_id, f"⚠️ SMS refine mais erreur de tracking. Check Supabase.")

    return True


# ---------------------------------------------------------------------------
# Polling loop — process callbacks + commands
# ---------------------------------------------------------------------------

def process_update(update):
    """Process a single Telegram update. Returns True if actionable."""
    # Callback query (button click)
    if "callback_query" in update:
        cb = update["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        username = cb["from"].get("username") or cb["from"].get("first_name", "unknown")

        if not is_authorized(chat_id):
            answer_callback_query(cb["id"], text="Non autorise", show_alert=True)
            return False

        data = cb.get("data", "")
        if ":" not in data:
            answer_callback_query(cb["id"])
            return False

        action, approval_id_str = data.split(":", 1)
        try:
            approval_id = int(approval_id_str)
        except ValueError:
            answer_callback_query(cb["id"])
            return False

        if action == "approve":
            handle_approve(approval_id, chat_id, message_id, username)
            answer_callback_query(cb["id"], text="Approuve!")
        elif action == "reject":
            handle_reject(approval_id, chat_id, message_id, username)
            answer_callback_query(cb["id"], text="Rejete")
        elif action == "edit":
            handle_edit_request(approval_id, chat_id, message_id, username)
            answer_callback_query(cb["id"], text="Envoie le texte avec /edit")
        elif action == "refine":
            handle_refine_request(approval_id, chat_id, message_id, username)
            answer_callback_query(cb["id"], text="Envoie ton feedback avec /refine")
        else:
            answer_callback_query(cb["id"])

        return True

    # Text message (commands)
    if "message" in update and "text" in update["message"]:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        username = msg["from"].get("username") or msg["from"].get("first_name", "unknown")
        text = msg["text"].strip()

        # /start — first-time authorization
        if text.lower().startswith("/start"):
            if not _load_authorized_chats():
                authorize_chat(chat_id)
                send_message(chat_id,
                    f"✅ <b>Bot active pour toi!</b>\n\nTon chat_id est <code>{chat_id}</code>.\n\n"
                    f"Les SMS proposes par l'IA t'arriveront ici chaque jour a 14h pour approbation."
                )
            elif is_authorized(chat_id):
                send_message(chat_id, f"✅ Deja autorise. Chat id: <code>{chat_id}</code>")
            else:
                send_message(chat_id, "❌ Cette instance du bot est deja pairee avec un autre utilisateur.")
            return True

        if not is_authorized(chat_id):
            send_message(chat_id, "❌ Non autorise.")
            return False

        # /edit <id> <text>
        if text.lower().startswith("/edit "):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                send_message(chat_id, "Usage: <code>/edit &lt;id&gt; &lt;texte&gt;</code>")
                return True
            try:
                approval_id = int(parts[1])
            except ValueError:
                send_message(chat_id, "ID invalide")
                return True
            new_text = parts[2]
            handle_custom_edit(approval_id, new_text, chat_id, username)
            return True

        # /refine <id> <feedback>
        if text.lower().startswith("/refine "):
            parts = text.split(maxsplit=2)
            if len(parts) < 3:
                send_message(chat_id, "Usage: <code>/refine &lt;id&gt; &lt;feedback&gt;</code>")
                return True
            try:
                approval_id = int(parts[1])
            except ValueError:
                send_message(chat_id, "ID invalide")
                return True
            feedback = parts[2]
            handle_refine_feedback(approval_id, feedback, chat_id, username)
            return True

    return False


def poll_once():
    """Process any pending updates. Returns count of updates processed."""
    last_id = _load_last_update_id()
    updates = get_updates(offset=last_id + 1 if last_id else None, timeout=0)
    count = 0
    max_id = last_id
    for update in updates:
        uid = update.get("update_id", 0)
        if uid > max_id:
            max_id = uid
        try:
            if process_update(update):
                count += 1
        except Exception as e:
            log.error("Error processing update %s: %s", uid, e, exc_info=True)
    if max_id > last_id:
        _save_last_update_id(max_id)
    return count


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso():
    from datetime import datetime
    return datetime.now().isoformat()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    if len(sys.argv) > 1 and sys.argv[1] == "poll":
        # Run a single poll cycle (for cron)
        n = poll_once()
        print(f"Processed {n} updates")
    else:
        # Show current state
        authorized = _load_authorized_chats()
        last = _load_last_update_id()
        print(f"Authorized chats: {authorized or 'NONE (first /start wins)'}")
        print(f"Last update_id: {last}")
        print()
        print(f"Bot: @Xguard_claude_bot")
        print(f"Token: {TELEGRAM_BOT_TOKEN[:20]}...")
        print()
        print("To authorize your account: send /start to @Xguard_claude_bot on Telegram")
        print("To run once: python telegram_bot.py poll")
