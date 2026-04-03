"""
alarm_handlers.py  — v2
────────────────────────
Self-contained alarm feature for Agrithm.

Changes vs v1:
  • alarm_scheduler_job no longer creates asyncio.new_event_loop().
    It now uses run_coroutine_threadsafe with the bot's running loop,
    which is passed in at registration time.
  • register_alarm_handlers() accepts an optional loop parameter.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Optional

import pytz
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
)

from agrithm_config import LANGUAGES
from utils.alarm import (
    add_alarm,
    delete_alarm,
    fmt_days,
    get_alarms,
    get_all_active_alarms,
    parse_alarm_days,
    parse_alarm_label,
    parse_alarm_time,
    should_fire_now,
    toggle_alarm,
)
from utils.storage import get_profile
from utils.voice import get_lang_config, translate_to_english

log = logging.getLogger(__name__)

_SARVAM_LANG_MAP     = {k: v["code"]        for k, v in LANGUAGES.items()}
_SARVAM_SPEAKERS_MAP = {k: v["tts_speaker"] for k, v in LANGUAGES.items()}


# ══════════════════════════════════════════════════════════════════
# TRIGGER DETECTION
# ══════════════════════════════════════════════════════════════════

_ALARM_TRIGGERS = [
    r'\balarm\b', r'\breminder\b', r'\bremind me\b', r'\bwake me\b',
    r'\bset.{0,10}alarm\b', r'\bset.{0,10}reminder\b',
    r'\balarm lagao\b', r'\balarm set\b', r'\byaad dilao\b',
    r'\bsmart.{0,5}alarm\b',
    r'\balarm pettandi\b', r'\balarm padu\b',
    r'\bnenaivuppaduththu\b',
]
_ALARM_RE = re.compile("|".join(_ALARM_TRIGGERS), re.IGNORECASE)

_LIST_TRIGGERS = re.compile(
    r'\b(list|show|my)\s*(alarm|reminder)s?\b'
    r'|\balarms?\b|\breminders?\b',
    re.IGNORECASE,
)


def is_alarm_request(text: str) -> bool:
    return bool(_ALARM_RE.search(text))


def is_alarm_list_request(text: str) -> bool:
    return bool(_LIST_TRIGGERS.search(text)) and not is_alarm_request(text)


# ══════════════════════════════════════════════════════════════════
# KEYBOARDS
# ══════════════════════════════════════════════════════════════════

def _alarm_list_keyboard(alarms: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for a in alarms:
        status = "✅" if a["active"] else "⏸"
        label  = f"{status} {a['label']} @ {a['time']} ({fmt_days(a['days'])})"
        rows.append([
            InlineKeyboardButton(label, callback_data=f"alarm_noop_{a['id']}"),
            InlineKeyboardButton("🗑",  callback_data=f"alarm_del_{a['id']}"),
            InlineKeyboardButton(
                "⏸" if a["active"] else "▶",
                callback_data=f"alarm_tog_{a['id']}",
            ),
        ])
    rows.append([InlineKeyboardButton("➕ New alarm", callback_data="alarm_new")])
    return InlineKeyboardMarkup(rows)


def _confirm_keyboard(alarm_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirm", callback_data=f"alarm_confirm_{alarm_id}"),
        InlineKeyboardButton("✏️ Edit",   callback_data=f"alarm_edit_{alarm_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"alarm_cancel_{alarm_id}"),
    ]])


# ══════════════════════════════════════════════════════════════════
# CORE HANDLERS
# ══════════════════════════════════════════════════════════════════

async def handle_alarm_set(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    raw_text: str,
) -> None:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    tz_name  = profile.get("timezone", "Asia/Kolkata")

    try:
        english = translate_to_english(raw_text, lang_cfg["code"]) or raw_text
    except Exception:
        english = raw_text

    log.info("[alarm] parsing: %r", english)

    time_result = parse_alarm_time(english) or parse_alarm_time(raw_text)
    if time_result is None:
        await update.message.reply_text(
            "⏰ I couldn't find a time in your message.\n\n"
            "Try: *Set alarm at 6:30 morning* or *Remind me at 18:00*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    hour, minute = time_result
    days  = parse_alarm_days(english) or parse_alarm_days(raw_text)
    label = parse_alarm_label(english) or "Alarm"

    alarm = add_alarm(user_id, hour, minute, label, days, tz_name)

    time_str = f"{hour:02d}:{minute:02d}"
    days_str = fmt_days(days)

    reply = (
        f"⏰ *Alarm Set!*\n\n"
        f"🏷 Label   : {label}\n"
        f"🕐 Time    : {time_str}\n"
        f"📅 Days    : {days_str}\n"
        f"🌍 Timezone: {tz_name}\n\n"
        f"I will ring you at *{time_str}* {days_str.lower()}."
    )
    await update.message.reply_text(
        reply,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_confirm_keyboard(alarm["id"]),
    )


async def handle_alarm_list(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user_id = update.effective_user.id
    alarms  = get_alarms(user_id)

    if not alarms:
        await update.message.reply_text(
            "⏰ You have no alarms set.\n\n"
            "Say *Set alarm at 6 morning* to create one!",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    await update.message.reply_text(
        f"⏰ *Your Alarms* ({len(alarms)} total):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_alarm_list_keyboard(alarms),
    )


# ══════════════════════════════════════════════════════════════════
# CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════════════════

async def alarm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query   = update.callback_query
    user_id = query.from_user.id
    data    = query.data or ""
    await query.answer()

    if data.startswith("alarm_noop_"):
        return

    if data.startswith("alarm_del_"):
        alarm_id = data[len("alarm_del_"):]
        ok       = delete_alarm(user_id, alarm_id)
        alarms   = get_alarms(user_id)
        if not alarms:
            await query.edit_message_text("✅ Alarm deleted. You have no more alarms.")
            return
        await query.edit_message_text(
            f"{'✅ Alarm deleted.' if ok else '❌ Not found.'}\n\n"
            f"⏰ *Your Alarms* ({len(alarms)} total):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_alarm_list_keyboard(alarms),
        )
        return

    if data.startswith("alarm_tog_"):
        alarm_id   = data[len("alarm_tog_"):]
        new_state  = toggle_alarm(user_id, alarm_id)
        alarms     = get_alarms(user_id)
        state_word = "resumed ▶" if new_state else "paused ⏸"
        await query.edit_message_text(
            f"Alarm {state_word}.\n\n⏰ *Your Alarms* ({len(alarms)} total):",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_alarm_list_keyboard(alarms),
        )
        return

    if data.startswith("alarm_confirm_"):
        alarm_id = data[len("alarm_confirm_"):]
        alarms   = get_alarms(user_id)
        alarm    = next((a for a in alarms if a["id"] == alarm_id), None)
        if alarm:
            await query.edit_message_text(
                f"✅ *Alarm confirmed!*\n"
                f"🕐 {alarm['time']} — {alarm['label']}\n"
                f"📅 {fmt_days(alarm['days'])}",
                parse_mode=ParseMode.MARKDOWN,
            )
        return

    if data.startswith("alarm_edit_"):
        alarm_id = data[len("alarm_edit_"):]
        delete_alarm(user_id, alarm_id)
        await query.edit_message_text(
            "✏️ Alarm removed. Please send a new alarm message with the correct time.",
        )
        return

    if data.startswith("alarm_cancel_"):
        alarm_id = data[len("alarm_cancel_"):]
        delete_alarm(user_id, alarm_id)
        await query.edit_message_text("❌ Alarm cancelled.")
        return

    if data == "alarm_new":
        await query.edit_message_text(
            "⏰ Tell me the new alarm:\n\n"
            "Example: *Set alarm at 7 morning for irrigation*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return


# ══════════════════════════════════════════════════════════════════
# SCHEDULER JOB — FIX 4: uses run_coroutine_threadsafe, no new loop
# ══════════════════════════════════════════════════════════════════

async def _fire_alarm(bot, user_id: int, alarm: dict) -> None:
    try:
        label    = alarm.get("label", "Alarm")
        time_str = alarm.get("time", "")
        text     = (
            f"⏰ *{label}*\n"
            f"🕐 It's {time_str} — time for your alarm!\n\n"
            f"🌾 Good luck with your farming today!"
        )
        await bot.send_message(
            chat_id=user_id, text=text, parse_mode=ParseMode.MARKDOWN,
        )
        log.info("[alarm] Fired '%s' for user %s", label, user_id)
    except Exception as exc:
        log.warning("[alarm] Could not deliver to user %s: %s", user_id, exc)


def make_alarm_scheduler_job(bot, loop: asyncio.AbstractEventLoop):
    """
    Returns a synchronous callable suitable for APScheduler.
    Uses run_coroutine_threadsafe to deliver alarms on the bot's loop
    without creating a new event loop (which would conflict with PTB).

    Usage:
        loop = asyncio.get_running_loop()
        scheduler.add_job(
            make_alarm_scheduler_job(app.bot, loop),
            "interval", minutes=1, id="alarm_checker", replace_existing=True,
        )
    """
    def _job():
        for user_id, alarm in get_all_active_alarms():
            if should_fire_now(alarm):
                future = asyncio.run_coroutine_threadsafe(
                    _fire_alarm(bot, user_id, alarm), loop
                )
                try:
                    future.result(timeout=10)
                except Exception as exc:
                    log.warning("[alarm] Delivery error user=%s: %s", user_id, exc)
    return _job


# Legacy name kept for backwards compatibility (bot.py v3 used this)
def alarm_scheduler_job(bot) -> None:
    """
    Deprecated — use make_alarm_scheduler_job() instead.
    This version creates a new event loop which can conflict with PTB.
    """
    log.warning(
        "[alarm] alarm_scheduler_job() is deprecated. "
        "Use make_alarm_scheduler_job(bot, loop) instead."
    )
    active = get_all_active_alarms()
    loop   = asyncio.new_event_loop()
    try:
        for user_id, alarm in active:
            if should_fire_now(alarm):
                loop.run_until_complete(_fire_alarm(bot, user_id, alarm))
    finally:
        loop.close()


# ══════════════════════════════════════════════════════════════════
# REGISTRATION
# ══════════════════════════════════════════════════════════════════

def register_alarm_handlers(app: Application) -> None:
    """Register alarm callback handler. Call from build_app()."""
    app.add_handler(CallbackQueryHandler(alarm_callback, pattern=r"^alarm_"))
    log.info("[alarm] Handlers registered.")