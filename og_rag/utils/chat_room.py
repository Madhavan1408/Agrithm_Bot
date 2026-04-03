"""
utils/chat_room.py — 1-on-1 Mini Chat Room for Agrithm Bot
──────────────────────────────────────────────────────────
Features:
  ✅ 1-on-1 chat between farmers (same crop + village/district)
  ✅ JSON-backed message history (chat_sessions/<room_id>.json)
  ✅ Offline notification queue (chat_sessions/offline_queue.json)
  ✅ Voice message forwarding
  ✅ Leave / re-join room
  ✅ Unread badge on menu button

FIXES vs v1:
  FIX H5: All file paths now use absolute locations derived from this
           file's directory. Previously used CWD-relative paths which
           broke when bot was started from a different directory (e.g.
           via systemd, cron, or a script in a parent folder).
"""

import os
import json
import time
import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger(__name__)

# FIX H5: Absolute paths — project root is one level above utils/
_ROOT        = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHAT_DIR     = os.path.join(_ROOT, "chat_sessions")
OFFLINE_QUEUE = os.path.join(CHAT_DIR, "offline_queue.json")
ACTIVE_ROOMS  = os.path.join(CHAT_DIR, "active_rooms.json")   # user_id → partner_id

MAX_HISTORY      = 100   # messages kept per room
MAX_OFFLINE_MSGS = 20    # max queued notifications per user

os.makedirs(CHAT_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════
# ROOM ID HELPERS
# ═══════════════════════════════════════════════════════════════════════

def room_id(user_a: int, user_b: int) -> str:
    """Stable room id regardless of who initiated."""
    lo, hi = sorted([user_a, user_b])
    return f"room_{lo}_{hi}"


def room_path(uid_a: int, uid_b: int) -> str:
    return os.path.join(CHAT_DIR, f"{room_id(uid_a, uid_b)}.json")


# ═══════════════════════════════════════════════════════════════════════
# ACTIVE ROOMS  (who is currently chatting with whom)
# ═══════════════════════════════════════════════════════════════════════

def _load_active() -> dict:
    if os.path.exists(ACTIVE_ROOMS):
        try:
            with open(ACTIVE_ROOMS, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_active(data: dict) -> None:
    with open(ACTIVE_ROOMS, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_partner(user_id: int) -> Optional[int]:
    """Return the partner user_id if user is in an active chat, else None."""
    data = _load_active()
    val  = data.get(str(user_id))
    return int(val) if val else None


def set_active_chat(user_id: int, partner_id: int) -> None:
    data = _load_active()
    data[str(user_id)]    = partner_id
    data[str(partner_id)] = user_id
    _save_active(data)
    log.info("Chat opened: %s ↔ %s", user_id, partner_id)


def leave_chat(user_id: int) -> Optional[int]:
    """Remove both sides from active map. Returns partner_id if found."""
    data       = _load_active()
    partner_id = data.pop(str(user_id), None)
    if partner_id:
        data.pop(str(int(partner_id)), None)
        _save_active(data)
        log.info("Chat closed: %s left (partner %s)", user_id, partner_id)
        return int(partner_id)
    _save_active(data)
    return None


def is_in_chat(user_id: int) -> bool:
    return get_partner(user_id) is not None


# ═══════════════════════════════════════════════════════════════════════
# MESSAGE HISTORY
# ═══════════════════════════════════════════════════════════════════════

def _load_room(uid_a: int, uid_b: int) -> dict:
    path = room_path(uid_a, uid_b)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"messages": [], "participants": sorted([uid_a, uid_b])}


def _save_room(uid_a: int, uid_b: int, data: dict) -> None:
    with open(room_path(uid_a, uid_b), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_message(
    from_id:     int,
    to_id:       int,
    msg_type:    str,     # "text" | "voice"
    content:     str,     # text string OR file_id for voice
    sender_name: str = "",
) -> dict:
    """Append a message to the room history. Returns the saved message dict."""
    data = _load_room(from_id, to_id)
    entry = {
        "id":          int(time.time() * 1000),
        "from":        from_id,
        "sender_name": sender_name,
        "type":        msg_type,
        "content":     content,
        "ts":          datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "read":        False,
    }
    data["messages"].append(entry)
    # Trim to MAX_HISTORY
    if len(data["messages"]) > MAX_HISTORY:
        data["messages"] = data["messages"][-MAX_HISTORY:]
    _save_room(from_id, to_id, data)
    return entry


def get_history(uid_a: int, uid_b: int, last_n: int = 10) -> list:
    """Return the last N messages for the room."""
    data = _load_room(uid_a, uid_b)
    return data["messages"][-last_n:]


def mark_read(uid_a: int, uid_b: int, reader_id: int) -> None:
    """Mark all messages sent TO reader_id as read."""
    data    = _load_room(uid_a, uid_b)
    changed = False
    for m in data["messages"]:
        if m["from"] != reader_id and not m["read"]:
            m["read"] = True
            changed   = True
    if changed:
        _save_room(uid_a, uid_b, data)


def unread_count(user_id: int, partner_id: int) -> int:
    """Count unread messages sent TO user_id in this room."""
    data = _load_room(user_id, partner_id)
    return sum(
        1 for m in data["messages"]
        if m["from"] != user_id and not m["read"]
    )


# ═══════════════════════════════════════════════════════════════════════
# OFFLINE NOTIFICATION QUEUE
# ═══════════════════════════════════════════════════════════════════════

def _load_queue() -> dict:
    if os.path.exists(OFFLINE_QUEUE):
        try:
            with open(OFFLINE_QUEUE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_queue(data: dict) -> None:
    with open(OFFLINE_QUEUE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def queue_offline_notification(to_id: int, from_name: str, preview: str) -> None:
    """
    Store an offline notification for a user who is not currently in chat.
    Called when sender sends a message but partner has no active chat session.
    """
    data  = _load_queue()
    key   = str(to_id)
    msgs  = data.get(key, [])
    msgs.append({
        "from_name": from_name,
        "preview":   preview[:80],
        "ts":        datetime.utcnow().strftime("%H:%M UTC"),
    })
    # Cap per user
    if len(msgs) > MAX_OFFLINE_MSGS:
        msgs = msgs[-MAX_OFFLINE_MSGS:]
    data[key] = msgs
    _save_queue(data)


def pop_offline_notifications(user_id: int) -> list:
    """
    Retrieve and clear all offline notifications for user_id.
    Returns list of notification dicts (may be empty).
    """
    data = _load_queue()
    key  = str(user_id)
    msgs = data.pop(key, [])
    if msgs:
        _save_queue(data)
    return msgs


def has_offline_notifications(user_id: int) -> bool:
    data = _load_queue()
    return bool(data.get(str(user_id)))


# ═══════════════════════════════════════════════════════════════════════
# FORMATTING HELPERS
# ═══════════════════════════════════════════════════════════════════════

def format_history_text(messages: list, my_id: int) -> str:
    """Format last N messages for display in Telegram."""
    if not messages:
        return "_No messages yet. Say hello! 👋_"
    lines = []
    for m in messages:
        arrow = "➡️ You" if m["from"] == my_id else f"⬅️ {m['sender_name']}"
        label = "🎙️ [Voice]" if m["type"] == "voice" else m["content"]
        lines.append(f"`{m['ts']}`  {arrow}\n{label}")
    return "\n\n".join(lines)


def format_offline_notifications(notifications: list) -> str:
    if not notifications:
        return ""
    lines = ["📬 *Messages received while you were away:*\n"]
    # Group by sender
    grouped: dict = {}
    for n in notifications:
        grouped.setdefault(n["from_name"], []).append(n)
    for name, msgs in grouped.items():
        count = len(msgs)
        last  = msgs[-1]["preview"]
        lines.append(f"• *{name}* sent {count} message(s)\n  _Last: \"{last}\"_")
    return "\n".join(lines)