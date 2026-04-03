"""
crop_journey_handlers.py
─────────────────────────
All Telegram handler logic for the Crop Journey feature.

COMMANDS / TEXT TRIGGERS handled here:
  • "Start <crop> journey"  / "Begin <crop> monitoring"
  • "Crop status"           — shows today's card on demand
  • "End journey"           / "Stop monitoring"
  • "Journey timeline"      — shows full stage timeline
  • Inline callback: journey_confirm / journey_cancel / journey_now

REGISTRATION:
  Call register_journey_handlers(app) in build_app() in bot.py.

ALARM INTEGRATION:
  The _fire_journey_card() coroutine is called every morning from
  the alarm scheduler in bot.py — pass it app.bot and the running loop.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import date
from typing import Optional

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

from utils.crop_journey import (
    CROP_LIFECYCLES,
    end_journey,
    get_all_active_journeys,
    get_current_day,
    get_journey,
    get_stage_for_day,
    get_supported_crops,
    journey_summary_text,
    match_crop,
    start_journey,
)
from utils.crop_schedule import (
    build_daily_card,
    build_daily_tip_prompt,
    build_journey_start_message,
)
from utils.storage import get_profile

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# TRIGGER DETECTION
# ══════════════════════════════════════════════════════════════════

_START_JOURNEY_RE = re.compile(
    r'(?:start|begin|suru|shuru|start\s+karo|start\s+cheyyi|arambhi|thodangi)'
    r'.{0,20}'
    r'(?:journey|monitoring|track|schedule)',
    re.IGNORECASE,
)

_STATUS_RE = re.compile(
    r'(?:crop\s+status|today.{0,10}crop|my\s+crop|show\s+crop|'
    r'crop\s+card|daily\s+card|what\s+to\s+do\s+today|journey\s+status)',
    re.IGNORECASE,
)

_END_JOURNEY_RE = re.compile(
    r'(?:end\s+journey|stop\s+monitoring|stop\s+journey|band\s+karo|'
    r'journey\s+end|cancel\s+journey)',
    re.IGNORECASE,
)

_TIMELINE_RE = re.compile(
    r'(?:journey\s+timeline|stage\s+timeline|crop\s+stages|show\s+stages)',
    re.IGNORECASE,
)


def is_start_journey_request(text: str) -> bool:
    return bool(_START_JOURNEY_RE.search(text))


def is_crop_status_request(text: str) -> bool:
    return bool(_STATUS_RE.search(text))


def is_end_journey_request(text: str) -> bool:
    return bool(_END_JOURNEY_RE.search(text))


def is_timeline_request(text: str) -> bool:
    return bool(_TIMELINE_RE.search(text))


def extract_crop_from_text(text: str) -> Optional[str]:
    """Try to extract a crop name from the journey start request."""
    # Try known crop names in the text
    for key, data in CROP_LIFECYCLES.items():
        for alias in data.get("aliases", []):
            if alias in text.lower():
                return key
    return None


# ══════════════════════════════════════════════════════════════════
# KEYBOARDS
# ══════════════════════════════════════════════════════════════════

def _crop_select_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for picking crop when not specified in text."""
    crops = list(CROP_LIFECYCLES.keys())
    rows  = []
    for i in range(0, len(crops), 2):
        row = []
        for crop in crops[i:i+2]:
            data = CROP_LIFECYCLES[crop]
            stage_emoji = data["stages"][0]["emoji"] if data["stages"] else "🌱"
            row.append(InlineKeyboardButton(
                f"{stage_emoji} {crop.title()} ({data['total_days']}d)",
                callback_data=f"journey_crop_{crop}",
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="journey_cancel")])
    return InlineKeyboardMarkup(rows)


def _journey_confirm_keyboard(crop_key: str, sow_date_str: str) -> InlineKeyboardMarkup:
    """Confirm/cancel before starting the journey."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Start Journey", callback_data=f"journey_confirm_{crop_key}_{sow_date_str}"),
        InlineKeyboardButton("❌ Cancel",        callback_data="journey_cancel"),
    ]])


def _journey_action_keyboard() -> InlineKeyboardMarkup:
    """Quick actions shown after crop card."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Full Timeline", callback_data="journey_timeline"),
        InlineKeyboardButton("🔔 Get Card Now",  callback_data="journey_now"),
        InlineKeyboardButton("🛑 End Journey",   callback_data="journey_end_confirm"),
    ]])


# ══════════════════════════════════════════════════════════════════
# HANDLE: Start Journey
# ══════════════════════════════════════════════════════════════════

async def handle_start_journey(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}

    # Check if already in a journey
    existing = get_journey(user_id)
    if existing and existing.get("active"):
        day     = get_current_day(existing)
        summary = journey_summary_text(existing)
        await update.message.reply_text(
            f"🌾 You already have an active crop journey!\n\n"
            f"{summary}\n\n"
            f"Type _'end journey'_ first if you want to start a new one.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_journey_action_keyboard(),
        )
        return

    # Try to extract crop from the text
    crop_key = extract_crop_from_text(text)

    if crop_key:
        # Show confirm screen with today as sow date
        today    = date.today()
        crop     = crop_key.title()
        data     = CROP_LIFECYCLES[crop_key]
        total    = data["total_days"]
        har_date = today
        from datetime import timedelta
        har_date = today + timedelta(days=total)
        harvest_date = har_date.strftime("%d %b %Y")
        alarm_time   = profile.get("digest_time", "06:00")

        stages_preview = "\n".join(
            f"  {s['emoji']} {s['name']} (Day {s['start']+1}–{s['end']})"
            for s in data["stages"]
        )

        msg = (
            f"🌱 *Start {crop} Journey?*\n\n"
            f"📅 Sow date    : Today ({today.strftime('%d %b %Y')})\n"
            f"🎉 Est. harvest: {harvest_date}\n"
            f"⏱ Duration    : {total} days\n"
            f"🔔 Daily alarm : {alarm_time} every morning\n\n"
            f"*Growth stages:*\n{stages_preview}\n\n"
            f"You'll receive a *Daily Crop Card* every morning with tasks, "
            f"do's & don'ts, fertilizer reminders, and monitoring tips.\n\n"
            f"Confirm to start?"
        )
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_journey_confirm_keyboard(crop_key, today.isoformat()),
        )
    else:
        # Ask them to pick a crop
        supported = ", ".join(get_supported_crops())
        await update.message.reply_text(
            f"🌱 *Start a Crop Journey*\n\n"
            f"Which crop would you like to monitor?\n\n"
            f"Supported: _{supported}_\n\n"
            f"Tap your crop below:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_crop_select_keyboard(),
        )


# ══════════════════════════════════════════════════════════════════
# HANDLE: Crop Status (on demand)
# ══════════════════════════════════════════════════════════════════

async def handle_crop_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    ollama_query_fn,        # pass query_ollama_async from bot.py
    speak_fn,               # pass _speak_sarvam from bot.py
) -> None:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")

    journey = get_journey(user_id)
    if not journey or not journey.get("active"):
        supported = ", ".join(get_supported_crops())
        await update.message.reply_text(
            f"🌱 You don't have an active crop journey.\n\n"
            f"Start one by saying:\n"
            f"  _\"Start rice journey\"_\n"
            f"  _\"Start wheat monitoring\"_\n\n"
            f"Supported crops: _{supported}_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    name = profile.get("name", "Farmer")

    # Generate AI tip
    tip_prompt = build_daily_tip_prompt(journey, profile)
    try:
        ai_tip = await ollama_query_fn(tip_prompt)
    except Exception:
        ai_tip = None

    md, tts = build_daily_card(journey, name, ollama_tip=ai_tip)

    await update.message.reply_text(
        md,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_journey_action_keyboard(),
    )

    if speak_fn:
        try:
            await speak_fn(update, tts, lang, "Daily Crop Card 🌾")
        except Exception as e:
            log.warning("[journey-card] TTS failed: %s", e)


# ══════════════════════════════════════════════════════════════════
# HANDLE: End Journey
# ══════════════════════════════════════════════════════════════════

async def handle_end_journey(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user_id = update.effective_user.id
    journey = get_journey(user_id)

    if not journey or not journey.get("active"):
        await update.message.reply_text(
            "You don't have an active crop journey to end.",
        )
        return

    crop = journey["crop_name"]
    day  = get_current_day(journey)

    await update.message.reply_text(
        f"🛑 *End {crop} Journey?*\n\n"
        f"You are on Day {day}. If you end now, daily cards will stop.\n\n"
        f"Are you sure?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Yes, end it", callback_data="journey_end_confirm"),
            InlineKeyboardButton("❌ Keep going",  callback_data="journey_cancel"),
        ]]),
    )


# ══════════════════════════════════════════════════════════════════
# HANDLE: Timeline
# ══════════════════════════════════════════════════════════════════

async def handle_journey_timeline(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    user_id = update.effective_user.id
    journey = get_journey(user_id)

    if not journey or not journey.get("active"):
        await update.message.reply_text(
            "You don't have an active crop journey. Type 'Start rice journey' to begin."
        )
        return

    crop_key  = journey["crop_key"]
    day       = get_current_day(journey)
    lifecycle = CROP_LIFECYCLES[crop_key]
    stages    = lifecycle["stages"]
    total     = lifecycle["total_days"]
    crop      = journey["crop_name"]

    lines = [f"🗺 *{crop} Growth Timeline*\n", f"Today: Day {day} of {total}\n"]
    for s in stages:
        is_current = s["start"] <= day < s["end"]
        is_done    = day >= s["end"]
        if is_current:
            marker = "▶ *NOW*"
        elif is_done:
            marker = "✓ Done"
        else:
            days_from_now = s["start"] - day
            marker = f"○ In {days_from_now}d"

        fert_note = ""
        if s.get("fertilizer") and not is_done:
            lo, hi = s["fertilizer"]["day_range"]
            fert_note = f" | 💊 Fert: Day {lo}–{hi}"

        critical_note = " ⚠️" if s.get("critical") else ""
        lines.append(
            f"{s['emoji']} *{s['name']}*{critical_note}\n"
            f"  {marker} | Day {s['start']+1}–{s['end']}{fert_note}\n"
        )

    sow     = journey["sow_date"]
    harvest = journey["harvest_date"]
    lines.append(f"\n📅 Sow date: {sow}\n🎉 Harvest : {harvest}")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_journey_action_keyboard(),
    )


# ══════════════════════════════════════════════════════════════════
# CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════════════════

def make_journey_callback_handler(ollama_query_fn, speak_fn):
    """
    Returns the callback handler with ollama and TTS functions closed over.
    """
    async def journey_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query   = update.callback_query
        user_id = query.from_user.id
        data    = query.data or ""
        await query.answer()

        profile = get_profile(user_id) or {}
        lang    = profile.get("language", "English")
        name    = profile.get("name", "Farmer")
        tz      = profile.get("timezone", "Asia/Kolkata")
        alarm   = profile.get("digest_time", "06:00")

        # ── User picked a crop from the selector ─────────────────
        if data.startswith("journey_crop_"):
            crop_key  = data[len("journey_crop_"):]
            today     = date.today()
            from datetime import timedelta
            data_lc   = CROP_LIFECYCLES[crop_key]
            total     = data_lc["total_days"]
            har_date  = (today + timedelta(days=total)).strftime("%d %b %Y")
            stages_p  = "\n".join(
                f"  {s['emoji']} {s['name']} (Day {s['start']+1}–{s['end']})"
                for s in data_lc["stages"]
            )
            msg = (
                f"🌱 *Start {crop_key.title()} Journey?*\n\n"
                f"📅 Sow date    : Today ({today.strftime('%d %b %Y')})\n"
                f"🎉 Est. harvest: {har_date}\n"
                f"⏱ Duration    : {total} days\n"
                f"🔔 Daily alarm : {alarm} every morning\n\n"
                f"*Growth stages:*\n{stages_p}\n\n"
                f"Confirm to start?"
            )
            await query.edit_message_text(
                msg,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_journey_confirm_keyboard(crop_key, today.isoformat()),
            )
            return

        # ── Confirm and start the journey ─────────────────────────
        if data.startswith("journey_confirm_"):
            parts    = data[len("journey_confirm_"):].split("_", 1)
            crop_key = parts[0]
            sow_str  = parts[1] if len(parts) > 1 else date.today().isoformat()
            sow_date = date.fromisoformat(sow_str)

            journey = start_journey(
                user_id  = user_id,
                crop_key = crop_key,
                sow_date = sow_date,
                alarm_time = alarm,
                timezone   = tz,
            )
            msg = build_journey_start_message(journey, name)
            await query.edit_message_text(
                msg,
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        # ── Get card now ──────────────────────────────────────────
        if data == "journey_now":
            journey = get_journey(user_id)
            if not journey or not journey.get("active"):
                await query.message.reply_text("No active journey found.")
                return
            tip_prompt = build_daily_tip_prompt(journey, profile)
            try:
                ai_tip = await ollama_query_fn(tip_prompt)
            except Exception:
                ai_tip = None
            md, tts = build_daily_card(journey, name, ollama_tip=ai_tip)
            await query.message.reply_text(
                md,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=_journey_action_keyboard(),
            )
            if speak_fn:
                try:
                    await speak_fn(query.message, tts, lang, "Daily Crop Card 🌾")
                except Exception:
                    pass
            return

        # ── Full timeline ─────────────────────────────────────────
        if data == "journey_timeline":
            journey = get_journey(user_id)
            if not journey or not journey.get("active"):
                await query.message.reply_text("No active journey.")
                return
            crop_key  = journey["crop_key"]
            day       = get_current_day(journey)
            lifecycle = CROP_LIFECYCLES[crop_key]
            stages    = lifecycle["stages"]
            total     = lifecycle["total_days"]
            lines = [f"🗺 *{journey['crop_name']} Timeline* — Day {day} of {total}\n"]
            for s in stages:
                is_current = s["start"] <= day < s["end"]
                is_done    = day >= s["end"]
                marker = "▶ *NOW*" if is_current else ("✓ Done" if is_done else f"○ In {s['start']-day}d")
                lines.append(f"{s['emoji']} {s['name']} (Day {s['start']+1}–{s['end']}) — {marker}")
            await query.message.reply_text(
                "\n".join(lines),
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        # ── End journey confirm ───────────────────────────────────
        if data == "journey_end_confirm":
            journey = get_journey(user_id)
            if journey:
                crop = journey["crop_name"]
                day  = get_current_day(journey)
                end_journey(user_id)
                await query.edit_message_text(
                    f"🛑 *{crop} Journey ended.*\n\n"
                    f"You completed {day} of {journey['total_days']} days.\n\n"
                    f"Start a new journey anytime with _'Start <crop> journey'_.",
                    parse_mode=ParseMode.MARKDOWN,
                )
            else:
                await query.edit_message_text("No active journey to end.")
            return

        # ── Cancel ────────────────────────────────────────────────
        if data == "journey_cancel":
            await query.edit_message_text("❌ Cancelled.")
            return

    return journey_callback


# ══════════════════════════════════════════════════════════════════
# MORNING ALARM FIRE — called by the alarm scheduler in bot.py
# ══════════════════════════════════════════════════════════════════

async def _fire_journey_card(
    bot,
    user_id:         int,
    journey:         dict,
    ollama_query_fn,
    sarvam_tts_fn,           # synchronous sarvam_tts(text, lang) → path
    tts_executor,
) -> None:
    """
    Called every morning from the alarm scheduler for each active journey.
    Sends the daily card with AI tip and TTS voice.
    """
    import asyncio, os, base64
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    name    = profile.get("name", "Farmer")
    day     = get_current_day(journey)
    crop    = journey["crop_name"]
    total   = journey["total_days"]

    log.info("[journey-fire] Sending day %s/%s card to user %s (%s)", day, total, user_id, crop)

    # ── Ring message first ────────────────────────────────────────
    try:
        stage = get_stage_for_day(journey["crop_key"], day)
        stage_name = stage["name"] if stage else "Complete"
        ring_msg = (
            f"🌾 *Good morning, {name}!*\n"
            f"🔔 Your *{crop}* Daily Crop Card is ready.\n"
            f"📅 Day {day} of {total} — {stage_name}"
        )
        await bot.send_message(chat_id=user_id, text=ring_msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        log.warning("[journey-fire] Ring failed: %s", e)
        return

    # ── Build AI tip ──────────────────────────────────────────────
    ai_tip = None
    try:
        tip_prompt = build_daily_tip_prompt(journey, profile)
        ai_tip     = await ollama_query_fn(tip_prompt)
    except Exception as e:
        log.warning("[journey-fire] AI tip failed: %s", e)

    # ── Full card ─────────────────────────────────────────────────
    try:
        md, tts_text = build_daily_card(journey, name, ollama_tip=ai_tip)
        await bot.send_message(
            chat_id=user_id,
            text=md,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Timeline",   callback_data="journey_timeline"),
                InlineKeyboardButton("🛑 End Journey", callback_data="journey_end_confirm"),
            ]]),
        )
    except Exception as e:
        log.warning("[journey-fire] Card send failed: %s", e)
        return

    # ── TTS voice ─────────────────────────────────────────────────
    audio_path = None
    try:
        loop       = asyncio.get_running_loop()
        audio_path = await loop.run_in_executor(tts_executor, sarvam_tts_fn, tts_text[:500], lang)
        if audio_path:
            with open(audio_path, "rb") as fh:
                await bot.send_voice(chat_id=user_id, voice=fh, caption="🌾 Daily Crop Card")
    except Exception as e:
        log.warning("[journey-fire] TTS failed: %s", e)
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass

    log.info("[journey-fire] ✅ Card sent to user %s — %s Day %s", user_id, crop, day)


# ══════════════════════════════════════════════════════════════════
# REGISTRATION
# ══════════════════════════════════════════════════════════════════

def register_journey_handlers(
    app:             Application,
    ollama_query_fn,
    speak_fn,
) -> None:
    """
    Register the journey callback handler.
    Call this from build_app() in bot.py after other handlers.

    The message-based triggers (start journey, crop status, end journey)
    are handled inline in bot.py's main_menu / global_fallback using the
    is_*_request() helpers — no extra MessageHandler needed here.
    """
    callback_handler = make_journey_callback_handler(ollama_query_fn, speak_fn)
    app.add_handler(CallbackQueryHandler(callback_handler, pattern=r"^journey_"))
    log.info("[journey] Handlers registered.")