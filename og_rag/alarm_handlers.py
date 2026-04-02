"""
alarm_handlers.py
─────────────────
Self-contained alarm feature for Agrithm.

HOW TO PLUG IN (only 2 lines added to bot.py — nothing else changes):

    # At the top of bot.py, after all other imports:
    from alarm_handlers import register_alarm_handlers, alarm_scheduler_job

    # Inside build_app(), just before  return app:
    register_alarm_handlers(app)

    # Inside create_scheduler() in utils/scheduler.py  — OR  —
    # Inside main() in bot.py, after scheduler.start():
    scheduler.add_job(
        alarm_scheduler_job,
        "interval",
        minutes=1,
        args=[app.bot],         # pass the bot object
        id="alarm_checker",
        replace_existing=True,
    )

That's it.  No other file is modified.
"""

from __future__ import annotations

import asyncio
import logging
import os
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
    MessageHandler,
    filters,
)

# ── Agrithm imports (already exist in the project) ───────────────
from agrithm_config import AUDIO_TEMP_DIR, LANGUAGES
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
from utils.voice import (
    get_lang_config,
    translate_to_english,
)

log = logging.getLogger(__name__)

# ── Sarvam speaker map (mirrors bot.py) ──────────────────────────
_SARVAM_LANG_MAP     = {k: v["code"]        for k, v in LANGUAGES.items()}
_SARVAM_SPEAKERS_MAP = {k: v["tts_speaker"] for k, v in LANGUAGES.items()}


# ══════════════════════════════════════════════════════════════════
# TRIGGER DETECTION  (called from bot.py message handlers)
# ══════════════════════════════════════════════════════════════════

_ALARM_TRIGGERS = [
    # English
    r'\balarm\b', r'\breminder\b', r'\bremind me\b', r'\bwake me\b',
    r'\bset.{0,10}alarm\b', r'\bset.{0,10}reminder\b',
    # Hindi / Hinglish
    r'\balarm lagao\b', r'\balarm set\b', r'\byaad dilao\b',
    r'\bsmart.{0,5}alarm\b',
    # Telugu
    r'\balarm pettandi\b', r'\balarm padu\b',
    # Tamil
    r'\balarム\b', r'\bnenaivuppaduththu\b',
]
_ALARM_RE = re.compile("|".join(_ALARM_TRIGGERS), re.IGNORECASE)

_LIST_TRIGGERS = re.compile(
    r'\b(list|show|my)\s*(alarm|reminder)s?\b'
    r'|\balarms?\b|\breminders?\b',
    re.IGNORECASE,
)


def is_alarm_request(text: str) -> bool:
    """Returns True if the message is asking to SET an alarm."""
    return bool(_ALARM_RE.search(text))


def is_alarm_list_request(text: str) -> bool:
    """Returns True if the message is asking to LIST/VIEW alarms."""
    return bool(_LIST_TRIGGERS.search(text)) and not is_alarm_request(text)


# ══════════════════════════════════════════════════════════════════
# KEYBOARDS
# ══════════════════════════════════════════════════════════════════

def _alarm_list_keyboard(alarms: list[dict]) -> InlineKeyboardMarkup:
    rows = []
    for a in alarms:
        status  = "✅" if a["active"] else "⏸"
        label   = f"{status} {a['label']} @ {a['time']} ({fmt_days(a['days'])})"
        rows.append([
            InlineKeyboardButton(label,                    callback_data=f"alarm_noop_{a['id']}"),
            InlineKeyboardButton("🗑",                     callback_data=f"alarm_del_{a['id']}"),
            InlineKeyboardButton("⏸" if a["active"] else "▶", callback_data=f"alarm_tog_{a['id']}"),
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
    raw_text: str,               # already in user's language
) -> None:
    """
    Parse raw_text, translate to English, extract time/day/label,
    store alarm, reply with confirmation.

    Call this from bot.py's handle_text_query / handle_voice_query
    when is_alarm_request() returns True.
    """
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    tz_name  = profile.get("timezone", "Asia/Kolkata")

    # Translate to English for parsing
    try:
        english = translate_to_english(raw_text, lang_cfg["code"]) or raw_text
    except Exception:
        english = raw_text

    log.info("[alarm] parsing: %r", english)

    # Parse
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

    # Store (returns alarm dict with generated id)
    alarm = add_alarm(user_id, hour, minute, label, days, tz_name)

    # Friendly confirmation
    try:
        tz  = pytz.timezone(tz_name)
        now = datetime.now(tz)
    except Exception:
        now = datetime.now()

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
    """Show all alarms for the user."""
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
# CALLBACK QUERY HANDLER  (inline button presses)
# ══════════════════════════════════════════════════════════════════

async def alarm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query   = update.callback_query
    user_id = query.from_user.id
    data    = query.data or ""
    await query.answer()

    # ── noop (label button) ───────────────────────────────────────
    if data.startswith("alarm_noop_"):
        return

    # ── delete ────────────────────────────────────────────────────
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

    # ── toggle (pause / resume) ───────────────────────────────────
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

    # ── confirm (after setting) ───────────────────────────────────
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

    # ── edit (delete + ask user to re-set) ───────────────────────
    if data.startswith("alarm_edit_"):
        alarm_id = data[len("alarm_edit_"):]
        delete_alarm(user_id, alarm_id)
        await query.edit_message_text(
            "✏️ Alarm removed. Please send a new alarm message with the correct time.",
        )
        return

    # ── cancel (delete silently) ──────────────────────────────────
    if data.startswith("alarm_cancel_"):
        alarm_id = data[len("alarm_cancel_"):]
        delete_alarm(user_id, alarm_id)
        await query.edit_message_text("❌ Alarm cancelled.")
        return

    # ── new (prompt) ──────────────────────────────────────────────
    if data == "alarm_new":
        await query.edit_message_text(
            "⏰ Tell me the new alarm:\n\n"
            "Example: *Set alarm at 7 morning for irrigation*",
            parse_mode=ParseMode.MARKDOWN,
        )
        return


# ══════════════════════════════════════════════════════════════════
# SCHEDULER JOB  — runs every minute via APScheduler
# ══════════════════════════════════════════════════════════════════

async def _fire_alarm(bot, user_id: int, alarm: dict) -> None:
    """Send the alarm notification to the user."""
    try:
        label    = alarm.get("label", "Alarm")
        time_str = alarm.get("time", "")
        text     = (
            f"⏰ *{label}*\n"
            f"🕐 It's {time_str} — time for your alarm!\n\n"
            f"🌾 Good luck with your farming today, Farmer!"
        )
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        log.info("[alarm] Fired alarm '%s' for user %s", label, user_id)
    except Exception as exc:
        log.warning("[alarm] Could not deliver to user %s: %s", user_id, exc)


def alarm_scheduler_job(bot) -> None:
    """
    Synchronous wrapper — APScheduler calls this every minute.
    It checks all active alarms and fires those that match current time.

    Add to your scheduler in utils/scheduler.py or in bot.py main():

        scheduler.add_job(
            alarm_scheduler_job,
            "interval",
            minutes=1,
            args=[app.bot],
            id="alarm_checker",
            replace_existing=True,
        )
    """
    active = get_all_active_alarms()
    loop   = asyncio.new_event_loop()
    try:
        for user_id, alarm in active:
            if should_fire_now(alarm):
                loop.run_until_complete(_fire_alarm(bot, user_id, alarm))
    finally:
        loop.close()


# ══════════════════════════════════════════════════════════════════
# REGISTRATION  — call once from build_app()
# ══════════════════════════════════════════════════════════════════

def register_alarm_handlers(app: Application) -> None:
    """
    Register all alarm-related handlers on the Application.
    Call this at the end of build_app(), before `return app`.

    These handlers are intentionally OUTSIDE the ConversationHandler
    so they work from any state without breaking conversation flow.
    """
    # Inline button presses (delete / toggle / confirm / edit)
    app.add_handler(
        CallbackQueryHandler(alarm_callback, pattern=r"^alarm_")
    )
    log.info("[alarm] Handlers registered.")
