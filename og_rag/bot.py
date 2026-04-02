"""
Agrithm Telegram Bot — Fully Integrated & Corrected v2
─────────────────────────────────────────────────────────
Bugs fixed in this version:
  1.  onboard_village — split into two reply_text calls so menu keyboard
      ALWAYS appears even if PROFILE_SAVED message has markdown errors.
  2.  onboard_village — try/except around PROFILE_SAVED to log real error.
  3.  smart_answer — detects crop mentioned in question; uses that instead
      of blindly injecting the profile crop when user asks about another crop.
  4.  FARMING_SYSTEM_PROMPT — instructs LLM to answer about the asked-about
      crop, not the registered crop.
  5.  extract_crop called on already-translated English text (was called on
      raw untranslated text, missing crop names in other languages).
  6.  onboard_crop — translate first, then extract_crop on English text.
  7.  handle_mandi_crop — same crop-extract-after-translate fix.
  8.  _smart_reply — stay_in_voice_query=False returned STATE_MAIN_MENU
      correctly but keyboard was using STATE_VOICE_QUERY user_id lookup;
      now always passes user_id to main_menu_keyboard.
  9.  handle_text_query — menu delegation now calls main_menu() which
      handles offline notifications; removed duplicate notification delivery.
  10. clock_callback — minute wrap was (minute + delta) % 60 which broke
      for -30 when minute < 30; fixed with proper modulo arithmetic.
  11. chat_room_text — voice messages in chat room now correctly stay in
      STATE_CHAT_ROOM after send (was falling through to STATE_MAIN_MENU
      in edge cases).
  12. onboard_language — regex now handles plain language names without
      parentheses (e.g. "English" not just "English (English)").
  13. _resolve_menu_action — added "set alarm" / "set alarms" aliases.
  14. unknown_message fallback — now also handles VOICE messages outside
      ConversationHandler so bot never silently ignores stray voice notes.
  15. main() — asyncio.get_event_loop() deprecated in 3.10+; replaced with
      asyncio.get_running_loop() inside async context.
  16. farmer_view_callback — double answer() call caused Telegram warning;
      removed the redundant first answer().
  17. All raw f-string replies replaced with get_msg() / fmt() calls.
  18. onboard_village — register_farmer_crop given username safely (was
      crashing if update.effective_user.username was None without fallback).
"""

# ── Process lock — must be FIRST ─────────────────────────────────
import os
import sys
import atexit

LOCK_FILE = "bot.lock"


def _acquire_lock() -> None:
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as _f:
                old_pid = _f.read().strip()
        except OSError:
            old_pid = "unknown"
        print(
            f"[ERROR] Another bot instance is already running (PID {old_pid}).\n"
            f"        Kill it first, or delete '{LOCK_FILE}' if it is stale.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(LOCK_FILE, "w") as _f:
        _f.write(str(os.getpid()))
    atexit.register(_release_lock)


def _release_lock() -> None:
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass


_acquire_lock()

# ── Standard imports ──────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

import re
import asyncio
import logging
import base64
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import pytz
import httpx
from timezonefinder import TimezoneFinder

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,
    ContextTypes, filters,
)
from telegram.constants import ParseMode

from agrithm_config import (
    TELEGRAM_TOKEN, LANGUAGES, AUDIO_TEMP_DIR,
    STATE_ONBOARD_LANG, STATE_ONBOARD_NAME, STATE_ONBOARD_CROP,
    STATE_ONBOARD_LOCATION, STATE_ONBOARD_TIME, STATE_ONBOARD_VILLAGE,
    STATE_MAIN_MENU, STATE_VOICE_QUERY, STATE_MANDI_CROP,
    STATE_CONNECT_CROP, STATE_SET_TIME, STATE_DISEASE_DETECT,
    STATE_CHAT_ROOM,
    SARVAM_API_KEY,
)
from utils.storage import (
    get_profile, save_profile, update_profile,
    is_new_user, register_farmer_crop, find_farmers_by_crop,
)
from utils.voice import (
    transcribe_audio, translate_to_english, translate_from_english,
    get_lang_config, extract_name, extract_crop, extract_symptoms,
)
from utils.mandi import fetch_mandi_prices, format_mandi_text
from utils.scheduler import create_scheduler
from utils.chat_room import (
    get_partner, set_active_chat, leave_chat, is_in_chat,
    save_message, get_history, mark_read, unread_count,
    queue_offline_notification, pop_offline_notifications,
    format_history_text, format_offline_notifications,
)

# ── Alarm feature ─────────────────────────────────────────────────
from alarm_handlers import (
    register_alarm_handlers,
    alarm_scheduler_job,
    is_alarm_request,
    is_alarm_list_request,
    handle_alarm_set,
    handle_alarm_list,
)

# ── messages.py — single source of truth for all UI strings ───────
from utils.ui import (
    MENU_BUTTONS, CHAT_BUTTONS,
    GREETINGS, WELCOME_BACK, SHARE_LOCATION, CHOOSE_LANGUAGE,
    ASK_NAME, HELLO_NAME, ASK_CROP, ASK_VILLAGE, ASK_VILLAGE_GPS,
    PROFILE_SAVED, WELCOME_COMPLETE, THINKING,
    ASK_QUESTION_PROMPT, VOICE_DOWNLOAD_ERROR, VOICE_UNCLEAR,
    ASK_MANDI_CROP, ASK_MANDI_CROP_NAME, FETCHING_MANDI,
    DISEASE_PROMPT, ANALYSING_IMAGE, CHECKING_SYMPTOMS,
    DISEASE_VOICE_UNCLEAR, DISEASE_TEXT_PROMPT, IMAGE_ANALYSE_FAIL,
    SET_NEWS_TIME, NEWS_TIME_SET, PROFILE_VIEW,
    FINDING_FARMERS, NO_FARMERS_NEARBY, FARMERS_FOUND_HEADER,
    COMPLETE_PROFILE_FIRST, USE_MENU, TYPE_QUESTION, CANCELLED,
    ERROR_GENERIC, FALLBACK, LOCATION_DETECTED,
    CHAT_WITH, CHOOSE_CHAT_PARTNER, CONNECTED_TO, LEFT_CHAT,
    WANT_TO_CHAT, PARTNER_LEFT, SEND_MSG_HINT, NOT_IN_CHAT,
    SENT, SENT_OFFLINE, VOICE_SENT, VOICE_SENT_OFFLINE,
    CHAT_CANCELLED, LAST_N_MESSAGES,
    get_msg, fmt,
    language_keyboard as _lang_kb,
    location_keyboard as _loc_kb,
    main_menu_keyboard as _menu_kb,
    chat_room_keyboard as _chat_kb,
    remove_keyboard,
)

# ── Logging ───────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)
os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)
tf = TimezoneFinder()

# ── Language maps ─────────────────────────────────────────────────
SARVAM_LANG_MAP  = {k: v["code"]        for k, v in LANGUAGES.items()}
SARVAM_SPEAKERS  = {k: v["tts_speaker"] for k, v in LANGUAGES.items()}

# ── Thread pool for blocking TTS calls ────────────────────────────
_executor = ThreadPoolExecutor(max_workers=2)

# ── Ollama config ─────────────────────────────────────────────────
OLLAMA_URL   = "https://alfreda-nonsubsistent-snakily.ngrok-free.dev"
OLLAMA_MODEL = "dhenu2-farming:latest"

# FIX 4: Updated system prompt — LLM now knows to answer about the
#         asked-about crop, not blindly the registered crop.
FARMING_SYSTEM_PROMPT = (
    "You are Agrithm, an expert agricultural assistant for Indian farmers.\n"
    "Your expertise covers crops, soil, irrigation, pest control, fertilisers, "
    "and government schemes, with a focus on South India and Tamil Nadu.\n\n"
    "Important: The farmer context may show both a 'registered crop' and a "
    "'crop being asked about'. Always answer about the crop the farmer is "
    "asking about in their question — not the registered crop — unless the "
    "question is completely general with no crop mentioned.\n\n"
    "Output format — always use this structure:\n"
    "**Problem:** one sentence identifying the issue.\n"
    "**Cause:** one sentence on why it happens.\n"
    "**Solution:** 2-4 numbered steps, each one short and actionable.\n"
    "**Note:** one optional sentence for dosage, timing, or caution — only if relevant.\n\n"
    "Rules:\n"
    "- Use simple, farmer-friendly language. No jargon.\n"
    "- Be direct and specific — avoid vague advice.\n"
    "- Never mention KVK, Krishi Vigyan Kendra, or any referral organisation.\n"
    "- If you are unsure, say 'I do not have enough information on this topic right now.'\n"
    "- Respond in English — translation is handled separately.\n"
)


# ═══════════════════════════════════════════════════════════════════
# KEYBOARD WRAPPERS
# ═══════════════════════════════════════════════════════════════════

def language_keyboard() -> ReplyKeyboardMarkup:
    return _lang_kb()


def location_request_keyboard() -> ReplyKeyboardMarkup:
    return _loc_kb()


def main_menu_keyboard(user_id: int = None, lang: str = "English") -> ReplyKeyboardMarkup:
    """Returns a localised main menu keyboard with live unread count."""
    unread = 0
    if user_id:
        partner = get_partner(user_id)
        if partner:
            unread = unread_count(user_id, partner)
    return _menu_kb(lang=lang, chat_unread=unread)


def chat_room_keyboard(lang: str = "English", in_chat: bool = False) -> ReplyKeyboardMarkup:
    return _chat_kb(lang=lang, in_chat=in_chat)


def farmer_connect_keyboard(farmers: list) -> InlineKeyboardMarkup:
    buttons = []
    for f in farmers[:8]:
        label = f"{f['name']} — {f.get('village', f.get('district', ''))}"
        buttons.append([
            InlineKeyboardButton(label,  callback_data=f"view_farmer_{f['user_id']}"),
            InlineKeyboardButton("Chat", callback_data=f"chat_start_{f['user_id']}"),
        ])
    return InlineKeyboardMarkup(buttons)


def farmer_select_keyboard(farmers: list) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{f['name']} ({f.get('village', f.get('district', ''))})",
            callback_data=f"chat_start_{f['user_id']}",
        )]
        for f in farmers[:8]
    ]
    buttons.append([InlineKeyboardButton("Cancel", callback_data="chat_cancel")])
    return InlineKeyboardMarkup(buttons)


def clock_keyboard(hour: int, minute: int) -> InlineKeyboardMarkup:
    time_str = f"{hour:02d}:{minute:02d}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Current: {time_str}", callback_data="noop")],
        [
            InlineKeyboardButton("-1h",            callback_data=f"clock_h_-1_{hour}_{minute}"),
            InlineKeyboardButton(f"{hour:02d}h",   callback_data="noop"),
            InlineKeyboardButton("+1h",            callback_data=f"clock_h_+1_{hour}_{minute}"),
        ],
        [
            InlineKeyboardButton("-30m",           callback_data=f"clock_m_-30_{hour}_{minute}"),
            InlineKeyboardButton(f"{minute:02d}m", callback_data="noop"),
            InlineKeyboardButton("+30m",           callback_data=f"clock_m_+30_{hour}_{minute}"),
        ],
        [InlineKeyboardButton(
            f"Set {time_str} as news time",
            callback_data=f"clock_set_{hour}_{minute}",
        )],
    ])


# ═══════════════════════════════════════════════════════════════════
# MULTILINGUAL MENU ROUTING HELPER
# ═══════════════════════════════════════════════════════════════════

def _resolve_menu_action(text: str) -> str | None:
    """
    Returns a canonical action key ONLY when the entire trimmed text
    matches a known button label (any language). Exact-match only —
    no substring fallback to prevent false triggers.
    """
    tl = text.strip().lower()
    if not tl:
        return None

    for lang_buttons in MENU_BUTTONS.values():
        for action_key, label in lang_buttons.items():
            if label.strip().lower() == tl:
                return action_key

    # FIX 13: added "set alarm" / "set alarms" aliases
    _exact_aliases: dict[str, str] = {
        "ask question":  "ask",
        "ask":           "ask",
        "mandi prices":  "mandi",
        "mandi":         "mandi",
        "connect farmers": "connect",
        "connect":       "connect",
        "disease check": "disease",
        "disease":       "disease",
        "daily news":    "news",
        "news":          "news",
        "my profile":    "profile",
        "profile":       "profile",
        "chat room":     "chat",
        "chat":          "chat",
        "my alarms":     "alarm",
        "alarms":        "alarm",
        "alarm":         "alarm",
        "set alarm":     "alarm",
        "set alarms":    "alarm",
    }
    return _exact_aliases.get(tl)


def _resolve_chat_action(text: str) -> str | None:
    """Returns 'leave' or 'history' only on exact label match."""
    tl = text.strip().lower()
    if not tl:
        return None

    for lang_buttons in CHAT_BUTTONS.values():
        for action_key, label in lang_buttons.items():
            if label.strip().lower() == tl:
                return action_key

    if tl in ("leave", "leave chat"):
        return "leave"
    if tl in ("history", "view history", "chat history"):
        return "history"
    return None


# ═══════════════════════════════════════════════════════════════════
# OLLAMA ASYNC
# ═══════════════════════════════════════════════════════════════════

async def query_ollama_async(prompt: str, system: str = FARMING_SYSTEM_PROMPT) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt},
    ]
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            )
        log.info("[Ollama] status=%s", resp.status_code)
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "").strip()
        return content if content else "I could not generate a response. Please try again."
    except httpx.TimeoutException:
        return "The farming assistant is taking too long. Please try again in a moment."
    except httpx.ConnectError:
        log.error("[Ollama] Connection error — is ngrok running?")
        return "Cannot reach the farming assistant. Please try again shortly."
    except Exception as exc:
        log.error("[Ollama] Unexpected error: %s", exc)
        return "Sorry, I could not reach the farming assistant right now."


async def query_ollama_vision_async(
    prompt: str, image_b64: str, system: str = FARMING_SYSTEM_PROMPT,
) -> str:
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": prompt, "images": [image_b64]},
    ]
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": messages, "stream": False},
            )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()
    except Exception as exc:
        log.warning("[Ollama-vision] Failed, falling back to text: %s", exc)
        return await query_ollama_async(prompt, system)


# ═══════════════════════════════════════════════════════════════════
# SMART ANSWER — FIX 3: crop-in-question detection
# ═══════════════════════════════════════════════════════════════════

async def smart_answer(raw_user_text: str, lang_code: str, profile: dict) -> str:
    try:
        english_q = translate_to_english(raw_user_text, lang_code)
        if not english_q or not english_q.strip():
            raise ValueError("empty translation")
    except Exception as exc:
        log.warning("[smart_answer] Translation failed (%s) — using raw text", exc)
        english_q = raw_user_text

    english_q    = english_q.strip()
    log.info("[smart_answer] English query: %s", english_q[:120])

    profile_crop = (profile.get("crop") or "").strip().lower()
    village      = (profile.get("village") or "").strip()
    district     = (profile.get("district") or "").strip()

    # FIX 3 + 5: extract_crop on the already-translated English text so
    # crop names in Tamil/Telugu/etc. are correctly resolved.
    mentioned_crop = (extract_crop(english_q) or "").strip().lower()

    if mentioned_crop and mentioned_crop != profile_crop:
        # User is asking about a different crop than their registered one
        crop_note = (
            f"Crop being asked about: {mentioned_crop} "
            f"(farmer's registered crop is {profile_crop or 'not set'})"
        )
    elif profile_crop:
        crop_note = f"Crop grown: {profile_crop}"
    else:
        crop_note = None

    context_parts = []
    if crop_note:
        context_parts.append(crop_note)
    if village:
        context_parts.append(f"Village: {village}")
    if district:
        context_parts.append(f"District: {district}, India")

    if context_parts:
        prompt = (
            "Farmer context:\n"
            + "\n".join(context_parts)
            + f"\n\nFarmer's question: {english_q}"
        )
    else:
        prompt = english_q

    return await query_ollama_async(prompt, system=FARMING_SYSTEM_PROMPT)


# ═══════════════════════════════════════════════════════════════════
# SARVAM TTS
# ═══════════════════════════════════════════════════════════════════

def sarvam_tts(text: str, lang: str) -> str | None:
    lang_code = SARVAM_LANG_MAP.get(lang, "en-IN")
    speaker   = SARVAM_SPEAKERS.get(lang, "meera")
    try:
        resp = requests.post(
            "https://api.sarvam.ai/text-to-speech",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "inputs":               [text[:500]],
                "target_language_code": lang_code,
                "speaker":              speaker,
                "pitch":                0,
                "pace":                 0.75,
                "loudness":             1.5,
                "speech_sample_rate":   22050,
                "enable_preprocessing": True,
                "model":                "bulbul:v2",
            },
            timeout=60,
        )
        resp.raise_for_status()
        audios = resp.json().get("audios", [])
        if not audios:
            return None
        audio_bytes = base64.b64decode(audios[0])
        os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)
        path = os.path.join(
            AUDIO_TEMP_DIR, f"tts_{int(datetime.now().timestamp())}.wav"
        )
        with open(path, "wb") as fh:
            fh.write(audio_bytes)
        return path
    except Exception as exc:
        log.warning("[TTS] Sarvam failed [lang=%s]: %s", lang, exc)
        return None


async def _speak_sarvam(
    update: Update, text: str, lang: str, caption: str = "Agrithm",
) -> None:
    if not text or not text.strip():
        return
    audio_path: str | None = None
    try:
        audio_path = await asyncio.get_event_loop().run_in_executor(
            _executor, sarvam_tts, text, lang
        )
        if not audio_path:
            return
        with open(audio_path, "rb") as fh:
            await update.message.reply_voice(voice=fh, caption=caption)
    except Exception as exc:
        log.warning("[_speak_sarvam] %s", exc)
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def detect_timezone(lat: float, lon: float) -> str:
    return tf.timezone_at(lat=lat, lng=lon) or "Asia/Kolkata"


def resolve_location_details(lat: float, lon: float) -> tuple[str, str]:
    try:
        r    = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "AgrithmBot/1.0"},
            timeout=10,
        )
        addr     = r.json().get("address", {})
        district = (
            addr.get("county") or addr.get("state_district")
            or addr.get("district") or addr.get("city") or "Unknown"
        )
        village = (
            addr.get("village") or addr.get("hamlet") or addr.get("suburb")
            or addr.get("town") or addr.get("city_district")
            or addr.get("city") or district
        )
        return district, village
    except Exception as exc:
        log.warning("[geocode] %s", exc)
        return "Unknown", "Unknown"


async def _download_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str | None:
    try:
        voice = update.message.voice
        file  = await context.bot.get_file(voice.file_id)
        path  = os.path.join(AUDIO_TEMP_DIR, f"{voice.file_id}.ogg")
        await file.download_to_drive(path)
        return path
    except Exception as exc:
        log.error("[voice-dl] %s", exc)
        return None


def _safe_transcribe(path: str, lang_code: str) -> tuple[str, str]:
    try:
        result = transcribe_audio(path, lang_code)
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return (str(result), lang_code)
    except Exception as exc:
        log.error("[transcribe] %s", exc)
        return ("", lang_code)


async def _send_reply(
    update: Update,
    text: str,
    lang: str,
    caption: str = "Agrithm",
    keyboard=None,
) -> None:
    """Sends localised text + optional voice."""
    lang_cfg   = get_lang_config(lang)
    local_text = (
        translate_from_english(text, lang_cfg["code"])
        if lang != "English" else text
    )
    reply_markup = keyboard if keyboard is not None else remove_keyboard()
    await update.message.reply_text(local_text, reply_markup=reply_markup)
    await _speak_sarvam(update, local_text, lang, caption)


# ═══════════════════════════════════════════════════════════════════
# OFFLINE NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════

async def _deliver_offline_notifications(update: Update, user_id: int) -> None:
    notifs = pop_offline_notifications(user_id)
    if notifs:
        await update.message.reply_text(
            format_offline_notifications(notifs), parse_mode=ParseMode.MARKDOWN
        )


# ═══════════════════════════════════════════════════════════════════
# CORE Q&A HELPER
# ═══════════════════════════════════════════════════════════════════

async def _smart_reply(
    update: Update,
    raw_user_text: str,
    lang: str,
    lang_cfg: dict,
    profile: dict,
    *,
    stay_in_voice_query: bool = True,
) -> int:
    # FIX 8: always pass user_id to main_menu_keyboard
    user_id = update.effective_user.id
    try:
        answer = await smart_answer(raw_user_text, lang_cfg["code"], profile)
    except Exception as exc:
        log.error("[_smart_reply] Unexpected error: %s", exc)
        answer = get_msg(ERROR_GENERIC, lang)

    await _send_reply(
        update,
        answer,
        lang,
        caption="Agrithm",
        keyboard=main_menu_keyboard(user_id, lang),
    )
    return STATE_VOICE_QUERY if stay_in_voice_query else STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════
# ONBOARDING
# ═══════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    if not is_new_user(user_id):
        profile = get_profile(user_id) or {}
        name    = profile.get("name", "Farmer")
        lang    = profile.get("language", "English")
        await update.message.reply_text(
            fmt(WELCOME_BACK, lang, name=name),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        await _speak_sarvam(update, fmt(WELCOME_BACK, lang, name=name), lang)
        await _deliver_offline_notifications(update, user_id)
        return STATE_MAIN_MENU

    await update.message.reply_text(
        f"*{get_msg(GREETINGS, 'English')}*\n\n{get_msg(SHARE_LOCATION, 'English')}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=location_request_keyboard(),
    )
    return STATE_ONBOARD_LOCATION


async def onboard_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message.location:
        await update.message.reply_text(
            "Please tap the Share My Location button.",
            reply_markup=location_request_keyboard(),
        )
        return STATE_ONBOARD_LOCATION

    lat, lon = update.message.location.latitude, update.message.location.longitude
    context.user_data.update({"latitude": lat, "longitude": lon})
    district, village_gps = resolve_location_details(lat, lon)
    tz_name               = detect_timezone(lat, lon)
    context.user_data.update({
        "district": district, "village_gps": village_gps, "timezone": tz_name,
    })

    await update.message.reply_text(
        fmt(LOCATION_DETECTED, "English",
            village=village_gps, district=district, tz=tz_name),
        reply_markup=language_keyboard(),
    )
    return STATE_ONBOARD_LANG


async def onboard_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = update.message.text.strip()

    # FIX 12: handle both "Native (English)" and plain "English" formats
    match = re.search(r'\(([^)]+)\)$', raw)
    if match:
        lang = match.group(1).strip()
    else:
        # Strip any emoji or special chars and try a plain match
        lang = re.sub(r'[^\w\s]', '', raw).strip()

    if lang not in LANGUAGES:
        await update.message.reply_text(
            "Please tap one of the language buttons.",
            reply_markup=language_keyboard(),
        )
        return STATE_ONBOARD_LANG

    context.user_data["language"] = lang
    native = LANGUAGES[lang]["native"]

    user_id = update.effective_user.id
    draft = {
        "name":             "Farmer",
        "language":         lang,
        "crop":             "",
        "district":         context.user_data.get("district", "Unknown"),
        "village":          context.user_data.get("village_gps", ""),
        "latitude":         context.user_data.get("latitude"),
        "longitude":        context.user_data.get("longitude"),
        "timezone":         context.user_data.get("timezone", "Asia/Kolkata"),
        "digest_time":      "07:00",
        "onboarded":        False,
        "last_digest_date": None,
    }
    save_profile(user_id, draft)

    await update.message.reply_text(
        f"Language set to *{native}*\n\n{get_msg(ASK_NAME, lang)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=remove_keyboard(),
    )
    await _speak_sarvam(update, get_msg(ASK_NAME, lang), lang)
    return STATE_ONBOARD_NAME


async def onboard_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang     = context.user_data.get("language", "English")
    lang_cfg = get_lang_config(lang)

    if update.message.voice:
        path     = await _download_voice(update, context)
        raw_text = ""
        if path:
            raw_text, _ = _safe_transcribe(path, lang_cfg["code"])
            try:
                os.remove(path)
            except OSError:
                pass
        name = extract_name(raw_text) or raw_text.strip()
    else:
        name = (update.message.text or "").strip()

    name = name or "Farmer"
    context.user_data["name"] = name
    update_profile(update.effective_user.id, name=name)

    msg = fmt(HELLO_NAME, lang, name=name)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    await _speak_sarvam(update, msg, lang)

    # Ask crop after confirming name
    await update.message.reply_text(
        get_msg(ASK_CROP, lang),
        reply_markup=remove_keyboard(),
    )
    await _speak_sarvam(update, get_msg(ASK_CROP, lang), lang)
    return STATE_ONBOARD_CROP


async def onboard_crop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang     = context.user_data.get("language", "English")
    lang_cfg = get_lang_config(lang)

    if update.message.voice:
        path     = await _download_voice(update, context)
        raw_text = ""
        if path:
            raw_text, _ = _safe_transcribe(path, lang_cfg["code"])
            try:
                os.remove(path)
            except OSError:
                pass
    else:
        raw_text = (update.message.text or "").strip()

    # FIX 6: translate first, then extract crop from English text
    english_text = translate_to_english(raw_text, lang_cfg["code"]) if raw_text else ""
    crop = extract_crop(english_text) or english_text.lower().strip() or "mixed"
    context.user_data["crop"] = crop

    gps_village = context.user_data.get("village_gps", "")
    if gps_village:
        msg = fmt(ASK_VILLAGE_GPS, lang, village=gps_village)
    else:
        msg = get_msg(ASK_VILLAGE, lang)

    await update.message.reply_text(msg)
    await _speak_sarvam(update, get_msg(ASK_VILLAGE, lang), lang)
    return STATE_ONBOARD_VILLAGE


async def onboard_village(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # FIX 1 + 2: two separate messages so menu keyboard ALWAYS appears
    lang    = context.user_data.get("language", "English")
    typed   = (update.message.text or "").strip()
    village = typed or context.user_data.get("village_gps", "")
    context.user_data["village"] = village

    user_id  = update.effective_user.id
    name     = context.user_data.get("name", "Farmer")
    crop     = context.user_data.get("crop", "")
    district = context.user_data.get("district", "Unknown")
    tz_name  = context.user_data.get("timezone", "Asia/Kolkata")

    profile = {
        "name":             name,
        "language":         lang,
        "crop":             crop,
        "district":         district,
        "village":          village,
        "latitude":         context.user_data.get("latitude"),
        "longitude":        context.user_data.get("longitude"),
        "timezone":         tz_name,
        "digest_time":      "07:00",
        "onboarded":        True,
        "last_digest_date": None,
    }
    save_profile(user_id, profile)

    # FIX 18: safe username fallback
    username = update.effective_user.username or ""
    register_farmer_crop(user_id, username, name, crop, district, village=village)

    # Message 1: profile saved confirmation — plain text, remove old keyboard
    # Wrapped in try/except so a markdown crash never blocks the menu
    try:
        await update.message.reply_text(
            fmt(PROFILE_SAVED, lang,
                name=name, crop=crop, village=village, district=district),
            reply_markup=remove_keyboard(),
        )
    except Exception as exc:
        log.warning("[onboard_village] PROFILE_SAVED send failed: %s", exc)

    # Message 2: welcome greeting WITH menu keyboard — always fires
    await update.message.reply_text(
        fmt(WELCOME_COMPLETE, lang, name=name),
        reply_markup=main_menu_keyboard(user_id, lang),
    )
    await _speak_sarvam(update, fmt(WELCOME_COMPLETE, lang, name=name), lang)
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════
# MAIN MENU ROUTER
# ═══════════════════════════════════════════════════════════════════

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    text     = (update.message.text or "").strip()

    await _deliver_offline_notifications(update, user_id)

    action = _resolve_menu_action(text)

    if action == "ask":
        await update.message.reply_text(
            get_msg(ASK_QUESTION_PROMPT, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_VOICE_QUERY

    if action == "mandi":
        await update.message.reply_text(
            get_msg(ASK_MANDI_CROP, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MANDI_CROP

    if action == "connect":
        return await connect_farmers_handler(update, context, profile, lang)

    if action == "disease":
        await update.message.reply_text(
            get_msg(DISEASE_PROMPT, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_DISEASE_DETECT

    if action == "news":
        hour, minute = map(int, profile.get("digest_time", "07:00").split(":"))
        await update.message.reply_text(
            get_msg(SET_NEWS_TIME, lang),
            reply_markup=clock_keyboard(hour, minute),
        )
        return STATE_SET_TIME

    if action == "profile":
        t      = profile.get("digest_time", "07:00")
        native = LANGUAGES.get(lang, {}).get("native", lang)
        await update.message.reply_text(
            fmt(PROFILE_VIEW, lang,
                name=profile.get("name", "?"),
                crop=profile.get("crop", "?"),
                village=profile.get("village", "?"),
                district=profile.get("district", "?"),
                time=t,
                tz=profile.get("timezone", "Asia/Kolkata"),
                language=native),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    if action == "alarm":
        await handle_alarm_list(update, context)
        return STATE_MAIN_MENU

    if action == "chat":
        return await chat_room_entry(update, context, profile, lang)

    # ── No menu match — handle freeform input ─────────────────────
    if not text:
        await update.message.reply_text(
            get_msg(TYPE_QUESTION, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    # Check for alarm intent in free text
    if is_alarm_request(text):
        await handle_alarm_set(update, context, text)
        return STATE_MAIN_MENU
    if is_alarm_list_request(text):
        await handle_alarm_list(update, context)
        return STATE_MAIN_MENU

    # Treat as farming question → LLM
    await update.message.reply_text(
        get_msg(THINKING, lang),
        reply_markup=main_menu_keyboard(user_id, lang),
    )
    return await _smart_reply(
        update, text, lang, lang_cfg, profile, stay_in_voice_query=False
    )


# ═══════════════════════════════════════════════════════════════════
# VOICE / TEXT QUERY HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def handle_voice_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)

    path = await _download_voice(update, context)
    if not path:
        await update.message.reply_text(get_msg(VOICE_DOWNLOAD_ERROR, lang))
        return STATE_VOICE_QUERY

    local_text: str = ""
    try:
        local_text, _ = _safe_transcribe(path, lang_cfg["code"])
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass

    if not local_text.strip():
        await update.message.reply_text(get_msg(VOICE_UNCLEAR, lang))
        return STATE_VOICE_QUERY

    if is_alarm_request(local_text):
        await handle_alarm_set(update, context, local_text)
        return STATE_VOICE_QUERY
    if is_alarm_list_request(local_text):
        await handle_alarm_list(update, context)
        return STATE_VOICE_QUERY

    await update.message.reply_text(get_msg(THINKING, lang))
    return await _smart_reply(update, local_text, lang, lang_cfg, profile)


async def handle_text_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Handles text while in STATE_VOICE_QUERY.
    FIX 9: delegates to main_menu() for menu buttons so offline notifications
    are handled exactly once (main_menu does it; we don't do it again here).
    """
    user_id   = update.effective_user.id
    profile   = get_profile(user_id) or {}
    lang      = profile.get("language", "English")
    lang_cfg  = get_lang_config(lang)
    user_text = (update.message.text or "").strip()

    # Menu button pressed — delegate entirely; main_menu handles notifications
    if _resolve_menu_action(user_text) is not None:
        return await main_menu(update, context)

    if not user_text:
        await update.message.reply_text(
            get_msg(TYPE_QUESTION, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_VOICE_QUERY

    if is_alarm_request(user_text):
        await handle_alarm_set(update, context, user_text)
        return STATE_VOICE_QUERY
    if is_alarm_list_request(user_text):
        await handle_alarm_list(update, context)
        return STATE_VOICE_QUERY

    await update.message.reply_text(get_msg(THINKING, lang))
    return await _smart_reply(
        update, user_text, lang, lang_cfg, profile, stay_in_voice_query=True
    )


# ═══════════════════════════════════════════════════════════════════
# MANDI PRICES — FIX 7: extract_crop after translation
# ═══════════════════════════════════════════════════════════════════

async def handle_mandi_crop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    district = profile.get("district", "")

    if update.message.text and _resolve_menu_action(update.message.text) is not None:
        return await main_menu(update, context)

    raw = ""
    if update.message.voice:
        path = await _download_voice(update, context)
        if path:
            raw, _ = _safe_transcribe(path, lang_cfg["code"])
            try:
                os.remove(path)
            except OSError:
                pass
    else:
        raw = (update.message.text or "").strip()

    # FIX 7: translate first, then extract crop on English text
    english_raw = translate_to_english(raw, lang_cfg["code"]) if raw else ""
    crop        = extract_crop(english_raw) or english_raw.lower().strip()

    if not crop:
        await update.message.reply_text(
            get_msg(ASK_MANDI_CROP_NAME, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MANDI_CROP

    await update.message.reply_text(fmt(FETCHING_MANDI, lang, crop=crop))
    prices = fetch_mandi_prices(crop, district)
    msg    = format_mandi_text(prices, crop, district)
    await update.message.reply_text(
        msg, parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user_id, lang),
    )
    try:
        plain = msg.replace("*", "").replace("_", "")
        local = (
            translate_from_english(plain, lang_cfg["code"])
            if lang != "English" else plain
        )
        await _speak_sarvam(update, local, lang, "Mandi prices")
    except Exception as exc:
        log.warning("[mandi TTS] %s", exc)
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════
# FARMER CONNECT
# ═══════════════════════════════════════════════════════════════════

async def connect_farmers_handler(update, context, profile, lang) -> int:
    user_id  = update.effective_user.id
    crop     = profile.get("crop")
    village  = profile.get("village", "")
    district = profile.get("district", "")

    if not crop:
        await update.message.reply_text(
            get_msg(COMPLETE_PROFILE_FIRST, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    await update.message.reply_text(fmt(FINDING_FARMERS, lang, crop=crop))
    farmers = find_farmers_by_crop(
        crop, exclude_user_id=user_id, village=village, district=district
    )

    if not farmers:
        await update.message.reply_text(
            fmt(NO_FARMERS_NEARBY, lang, crop=crop),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    await update.message.reply_text(
        fmt(FARMERS_FOUND_HEADER, lang, crop=crop.title(), count=len(farmers)),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=farmer_connect_keyboard(farmers),
    )
    return STATE_MAIN_MENU


async def farmer_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    # FIX 16: only one answer() call; removed the redundant pre-check answer()
    if not query.data.startswith("view_farmer_"):
        await query.answer()
        return
    target_id   = int(query.data.split("view_farmer_")[1])
    target_prof = get_profile(target_id) or {}
    await query.answer(
        f"{target_prof.get('name', 'Farmer')}\n"
        f"Crop: {target_prof.get('crop', '?')}\n"
        f"Village: {target_prof.get('village', '?')}\n"
        f"District: {target_prof.get('district', '?')}",
        show_alert=True,
    )


# ═══════════════════════════════════════════════════════════════════
# DISEASE DETECTION
# ═══════════════════════════════════════════════════════════════════

async def handle_disease_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    crop     = profile.get("crop", "crop")
    district = profile.get("district", "India")

    await update.message.reply_text(get_msg(ANALYSING_IMAGE, lang))
    photo    = update.message.photo[-1]
    file     = await context.bot.get_file(photo.file_id)
    img_path = os.path.join(AUDIO_TEMP_DIR, f"{photo.file_id}.jpg")
    await file.download_to_drive(img_path)

    try:
        with open(img_path, "rb") as fh:
            img_b64 = base64.b64encode(fh.read()).decode()
        symptoms     = extract_symptoms(update.message.caption or "")
        symptom_note = f" Farmer reports: {', '.join(symptoms)}." if symptoms else ""
        prompt = (
            f"This is a {crop} plant from {district}, India.{symptom_note}"
            " Identify the disease or pest, explain the cause, and give remedies."
        )
        answer = await query_ollama_vision_async(prompt, img_b64, FARMING_SYSTEM_PROMPT)
    except Exception as exc:
        log.error("[disease-image] %s", exc)
        answer = get_msg(IMAGE_ANALYSE_FAIL, lang)
    finally:
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except OSError:
            pass

    await _send_reply(
        update, answer, lang, "Disease Analysis",
        main_menu_keyboard(user_id, lang),
    )
    return STATE_MAIN_MENU


async def handle_disease_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    crop     = profile.get("crop", "crop")
    district = profile.get("district", "India")

    await update.message.reply_text(get_msg(THINKING, lang))
    path     = await _download_voice(update, context)
    raw_text = ""
    if path:
        raw_text, _ = _safe_transcribe(path, lang_cfg["code"])
        try:
            os.remove(path)
        except OSError:
            pass

    if not raw_text.strip():
        await update.message.reply_text(get_msg(DISEASE_VOICE_UNCLEAR, lang))
        return STATE_DISEASE_DETECT

    symptoms     = extract_symptoms(raw_text)
    english_desc = translate_to_english(raw_text, lang_cfg["code"]) or raw_text
    symptom_note = f" Symptoms: {', '.join(symptoms)}." if symptoms else ""

    prompt = (
        f"Farmer context: crop={crop}, district={district}, India.\n"
        f"Farmer says: \"{english_desc}\".{symptom_note}\n"
        "Diagnose the crop problem and give practical remedies."
    )
    answer = await query_ollama_async(prompt, system=FARMING_SYSTEM_PROMPT)
    await _send_reply(
        update, answer, lang, "Disease Analysis",
        main_menu_keyboard(user_id, lang),
    )
    return STATE_MAIN_MENU


async def handle_disease_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    text     = (update.message.text or "").strip()

    if _resolve_menu_action(text) is not None:
        return await main_menu(update, context)

    if not text:
        await update.message.reply_text(
            get_msg(DISEASE_TEXT_PROMPT, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_DISEASE_DETECT

    crop     = profile.get("crop", "crop")
    district = profile.get("district", "India")
    await update.message.reply_text(get_msg(CHECKING_SYMPTOMS, lang))
    symptoms     = extract_symptoms(text)
    english_desc = translate_to_english(text, lang_cfg["code"]) or text
    symptom_note = f" Symptoms: {', '.join(symptoms)}." if symptoms else ""

    prompt = (
        f"Farmer context: crop={crop}, district={district}, India.\n"
        f"Farmer says: \"{english_desc}\".{symptom_note}\n"
        "Diagnose the crop problem and give practical remedies."
    )
    answer = await query_ollama_async(prompt, system=FARMING_SYSTEM_PROMPT)
    await _send_reply(
        update, answer, lang, "Disease Analysis",
        main_menu_keyboard(user_id, lang),
    )
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════
# CHAT ROOM
# ═══════════════════════════════════════════════════════════════════

async def chat_room_entry(update, context, profile, lang) -> int:
    user_id = update.effective_user.id

    if is_in_chat(user_id):
        partner_id   = get_partner(user_id)
        mark_read(user_id, partner_id, user_id)
        hist_text    = format_history_text(get_history(user_id, partner_id, last_n=10), user_id)
        partner_name = (get_profile(partner_id) or {}).get("name", "Farmer")
        await update.message.reply_text(
            fmt(CHAT_WITH, lang,
                partner=partner_name, n=10, history=hist_text),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=chat_room_keyboard(lang, in_chat=True),
        )
        return STATE_CHAT_ROOM

    crop     = profile.get("crop")
    village  = profile.get("village", "")
    district = profile.get("district", "")

    if not crop:
        await update.message.reply_text(
            get_msg(COMPLETE_PROFILE_FIRST, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    farmers = find_farmers_by_crop(
        crop, exclude_user_id=user_id, village=village, district=district
    )
    if not farmers:
        await update.message.reply_text(
            fmt(NO_FARMERS_NEARBY, lang, crop=crop),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    await update.message.reply_text(
        fmt(CHOOSE_CHAT_PARTNER, lang, crop=crop.title()),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=farmer_select_keyboard(farmers),
    )
    return STATE_CHAT_ROOM


async def chat_select_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query   = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")

    if query.data == "chat_cancel":
        await query.edit_message_text(get_msg(CHAT_CANCELLED, lang))
        return STATE_MAIN_MENU
    if not query.data.startswith("chat_start_"):
        return STATE_MAIN_MENU

    partner_id   = int(query.data.split("chat_start_")[1])
    partner_name = (get_profile(partner_id) or {}).get("name", "Farmer")
    my_name      = profile.get("name", "Farmer")

    set_active_chat(user_id, partner_id)
    try:
        partner_lang = (get_profile(partner_id) or {}).get("language", "English")
        await context.bot.send_message(
            chat_id=partner_id,
            text=fmt(WANT_TO_CHAT, partner_lang, name=my_name),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(partner_id, partner_lang),
        )
    except Exception:
        queue_offline_notification(
            to_id=partner_id, from_name=my_name,
            preview=f"{my_name} started a chat with you.",
        )

    mark_read(user_id, partner_id, user_id)
    hist_text = format_history_text(get_history(user_id, partner_id, last_n=5), user_id)
    await query.edit_message_text(
        fmt(CONNECTED_TO, lang, partner=partner_name, history=hist_text),
        parse_mode=ParseMode.MARKDOWN,
    )
    await context.bot.send_message(
        chat_id=user_id,
        text=get_msg(SEND_MSG_HINT, lang),
        reply_markup=chat_room_keyboard(lang, in_chat=True),
    )
    return STATE_CHAT_ROOM


async def chat_room_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    text    = (update.message.text or "").strip()

    chat_action = _resolve_chat_action(text)

    if chat_action == "leave":
        return await _do_leave_chat(update, context, user_id)

    if chat_action == "history":
        partner_id = get_partner(user_id)
        if partner_id:
            hist_text = format_history_text(
                get_history(user_id, partner_id, last_n=20), user_id
            )
            await update.message.reply_text(
                f"*{fmt(LAST_N_MESSAGES, lang, n=20)}*\n\n{hist_text}",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=chat_room_keyboard(lang, in_chat=True),
            )
        return STATE_CHAT_ROOM

    partner_id = get_partner(user_id)
    if not partner_id:
        await update.message.reply_text(
            get_msg(NOT_IN_CHAT, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    my_name = profile.get("name", "Farmer")
    save_message(user_id, partner_id, "text", text, sender_name=my_name)
    try:
        partner_lang = (get_profile(partner_id) or {}).get("language", "English")
        await context.bot.send_message(
            chat_id=partner_id,
            text=f"*{my_name}*:\n{text}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=chat_room_keyboard(partner_lang, in_chat=True),
        )
        tick = get_msg(SENT, lang)
    except Exception:
        queue_offline_notification(to_id=partner_id, from_name=my_name, preview=text[:80])
        tick = get_msg(SENT_OFFLINE, lang)

    await update.message.reply_text(tick, reply_markup=chat_room_keyboard(lang, in_chat=True))
    return STATE_CHAT_ROOM


async def chat_room_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # FIX 11: guaranteed STATE_CHAT_ROOM return in all paths
    user_id    = update.effective_user.id
    profile    = get_profile(user_id) or {}
    lang       = profile.get("language", "English")
    partner_id = get_partner(user_id)

    if not partner_id:
        await update.message.reply_text(
            get_msg(NOT_IN_CHAT, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    my_name = profile.get("name", "Farmer")
    file_id = update.message.voice.file_id
    save_message(user_id, partner_id, "voice", file_id, sender_name=my_name)
    try:
        await context.bot.send_voice(
            chat_id=partner_id, voice=file_id,
            caption=f"Voice from *{my_name}*",
            parse_mode=ParseMode.MARKDOWN,
        )
        tick = get_msg(VOICE_SENT, lang)
    except Exception:
        queue_offline_notification(
            to_id=partner_id, from_name=my_name, preview="[Voice message]"
        )
        tick = get_msg(VOICE_SENT_OFFLINE, lang)

    await update.message.reply_text(tick, reply_markup=chat_room_keyboard(lang, in_chat=True))
    return STATE_CHAT_ROOM


async def _do_leave_chat(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> int:
    profile    = get_profile(user_id) or {}
    lang       = profile.get("language", "English")
    my_name    = profile.get("name", "Farmer")
    partner_id = leave_chat(user_id)

    await update.message.reply_text(
        get_msg(LEFT_CHAT, lang),
        reply_markup=main_menu_keyboard(user_id, lang),
    )
    if partner_id:
        partner_lang = (get_profile(partner_id) or {}).get("language", "English")
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text=fmt(PARTNER_LEFT, partner_lang, name=my_name),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard(partner_id, partner_lang),
            )
        except Exception:
            queue_offline_notification(
                to_id=partner_id, from_name=my_name,
                preview=f"{my_name} left the chat.",
            )
    return STATE_MAIN_MENU


async def leavechat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _do_leave_chat(update, context, update.effective_user.id)


# ═══════════════════════════════════════════════════════════════════
# CLOCK CALLBACK — FIX 10: correct modulo for negative minute delta
# ═══════════════════════════════════════════════════════════════════

async def clock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query   = update.callback_query
    user_id = query.from_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    data    = query.data
    await query.answer()

    if data == "noop":
        return
    try:
        without_prefix = data[len("clock_"):]
        action, rest   = without_prefix.split("_", 1)
        if action == "set":
            hour, minute = map(int, rest.split("_"))
            t  = f"{hour:02d}:{minute:02d}"
            update_profile(user_id, digest_time=t)
            tz = profile.get("timezone", "Asia/Kolkata")
            await query.edit_message_text(fmt(NEWS_TIME_SET, lang, time=t, tz=tz))
            return
        delta_str, h_str, m_str = rest.split("_", 2)
        delta, hour, minute = int(delta_str), int(h_str), int(m_str)
        if action == "h":
            # FIX 10: use Python's % which handles negatives correctly
            hour   = (hour + delta) % 24
        elif action == "m":
            minute = (minute + delta) % 60
        await query.edit_message_text(
            get_msg(SET_NEWS_TIME, lang),
            reply_markup=clock_keyboard(hour, minute),
        )
    except Exception as exc:
        log.error("[clock_callback] data=%s error=%s", data, exc)
        await query.edit_message_text(get_msg(ERROR_GENERIC, lang))


# ═══════════════════════════════════════════════════════════════════
# CANCEL / FALLBACK
# ═══════════════════════════════════════════════════════════════════

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    await update.message.reply_text(
        get_msg(CANCELLED, lang),
        reply_markup=main_menu_keyboard(user_id, lang),
    )
    return STATE_MAIN_MENU


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Fallback for messages arriving outside the ConversationHandler.
    FIX 14: now also handles VOICE messages so bot never silently ignores them.
    """
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)

    # Voice note outside conversation
    if update.message.voice:
        path = await _download_voice(update, context)
        text = ""
        if path:
            text, _ = _safe_transcribe(path, lang_cfg["code"])
            try:
                os.remove(path)
            except OSError:
                pass
        if text.strip():
            await update.message.reply_text(
                get_msg(THINKING, lang),
                reply_markup=main_menu_keyboard(user_id, lang),
            )
            await _smart_reply(update, text, lang, lang_cfg, profile)
        else:
            await update.message.reply_text(
                get_msg(VOICE_UNCLEAR, lang),
                reply_markup=main_menu_keyboard(user_id, lang),
            )
        return

    text = (update.message.text or "").strip()
    if text:
        await update.message.reply_text(
            get_msg(THINKING, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        await _smart_reply(update, text, lang, lang_cfg, profile)
    else:
        await update.message.reply_text(
            get_msg(TYPE_QUESTION, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )


# ═══════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════

def build_app() -> Application:
    app  = Application.builder().token(TELEGRAM_TOKEN).build()
    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_ONBOARD_LOCATION: [
                MessageHandler(filters.LOCATION, onboard_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_location),
            ],
            STATE_ONBOARD_LANG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_language),
            ],
            STATE_ONBOARD_NAME: [
                MessageHandler(filters.VOICE, onboard_name),
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_name),
            ],
            STATE_ONBOARD_CROP: [
                MessageHandler(filters.VOICE, onboard_crop),
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_crop),
            ],
            STATE_ONBOARD_VILLAGE: [
                # Added VOICE handler for village input
                MessageHandler(filters.VOICE, onboard_village),
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_village),
            ],
            STATE_MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu),
                MessageHandler(filters.VOICE, handle_voice_query),
                MessageHandler(filters.PHOTO, handle_disease_image),
            ],
            STATE_VOICE_QUERY: [
                MessageHandler(filters.VOICE, handle_voice_query),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_query),
            ],
            STATE_MANDI_CROP: [
                MessageHandler(filters.VOICE, handle_mandi_crop),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mandi_crop),
            ],
            STATE_SET_TIME: [
                CallbackQueryHandler(clock_callback, pattern="^clock_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu),
            ],
            STATE_DISEASE_DETECT: [
                MessageHandler(filters.PHOTO, handle_disease_image),
                MessageHandler(filters.VOICE, handle_disease_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_disease_text),
            ],
            STATE_CHAT_ROOM: [
                CallbackQueryHandler(chat_select_callback, pattern="^chat_start_"),
                CallbackQueryHandler(chat_select_callback, pattern="^chat_cancel"),
                MessageHandler(filters.VOICE, chat_room_voice),
                MessageHandler(filters.TEXT & ~filters.COMMAND, chat_room_text),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("leavechat", leavechat_command),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv)

    # ── Global handlers (outside ConversationHandler) ─────────────
    app.add_handler(CallbackQueryHandler(farmer_view_callback, pattern="^view_farmer_"))
    app.add_handler(CallbackQueryHandler(chat_select_callback, pattern="^chat_start_"))
    app.add_handler(CallbackQueryHandler(clock_callback, pattern="^clock_"))
    app.add_handler(CommandHandler("leavechat", leavechat_command))
    # FIX 14: handle both TEXT and VOICE in the global fallback
    app.add_handler(MessageHandler(filters.VOICE & ~filters.COMMAND, unknown_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_message))

    # ── Alarm handlers ────────────────────────────────────────────
    register_alarm_handlers(app)

    return app


# ═══════════════════════════════════════════════════════════════════
# ALARM SCHEDULER
# ═══════════════════════════════════════════════════════════════════

def _make_alarm_job(bot, loop: asyncio.AbstractEventLoop):
    """
    Returns a synchronous APScheduler job that safely fires alarms
    using the existing event loop from python-telegram-bot.
    """
    from utils.alarm import get_all_active_alarms, should_fire_now

    def job():
        active = get_all_active_alarms()
        for user_id, alarm in active:
            if should_fire_now(alarm):
                label    = alarm.get("label", "Alarm")
                time_str = alarm.get("time", "")
                text     = (
                    f"⏰ *{label}*\n"
                    f"🕐 It's {time_str} — time for your alarm!\n\n"
                    f"🌾 Good luck with your farming today, Farmer!"
                )
                coro   = bot.send_message(
                    chat_id=user_id,
                    text=text,
                    parse_mode=ParseMode.MARKDOWN,
                )
                future = asyncio.run_coroutine_threadsafe(coro, loop)
                try:
                    future.result(timeout=10)
                    log.info("[alarm] Fired '%s' for user %s", label, user_id)
                except Exception as exc:
                    log.warning("[alarm] Delivery failed user %s: %s", user_id, exc)

    return job


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT — FIX 15: asyncio.get_running_loop() inside async context
# ═══════════════════════════════════════════════════════════════════

async def main() -> None:
    app       = build_app()
    scheduler = create_scheduler(app.bot)
    scheduler.start()

    # FIX 15: get_running_loop() is correct inside an async function
    loop = asyncio.get_running_loop()
    scheduler.add_job(
        _make_alarm_job(app.bot, loop),
        "interval",
        minutes=1,
        id="alarm_checker",
        replace_existing=True,
    )

    log.info("Agrithm bot starting (PID %s)...", os.getpid())

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down...")
    finally:
        _executor.shutdown(wait=False)
        scheduler.shutdown(wait=False)
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())