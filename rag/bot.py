"""
Agrithm Telegram Bot — Full Featured
──────────────────────────────────────
Features:
  ✅ Auto location detection at start
  ✅ Ollama (dhenu2-farming:latest) for RAG
  ✅ Sarvam AI TTS for Indian language voice
  ✅ Farmer connect (same crop + village/district)
  ✅ Daily digest at user-set time (interactive clock UI via inline keyboard)
  ✅ Mandi prices
  ✅ Crop disease detection (image upload)
  ✅ Multilingual support

Run: python bot.py
Requires:
  pip install python-telegram-bot langchain-community faiss-cpu
              sentence-transformers httpx apscheduler python-dotenv
              requests timezonefinder pytz
"""
# ── Load .env first ───────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
import logging
import base64
import requests
from datetime import datetime, timedelta

import pytz
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
    STATE_ONBOARD_LOCATION, STATE_ONBOARD_VILLAGE,
    STATE_MAIN_MENU, STATE_VOICE_QUERY, STATE_MANDI_CROP,
    STATE_CONNECT_CROP, STATE_SET_TIME, STATE_DISEASE_DETECT,
    SARVAM_API_KEY, OLLAMA_URL,
)
from utils.storage import (
    get_profile, save_profile, update_profile,
    is_new_user, register_farmer_crop, find_farmers_by_crop,
)
from utils.voice import transcribe_audio, translate_to_english, translate_from_english, get_lang_config
from utils.rag import query_agrithm, generate_daily_digest
from utils.mandi import fetch_mandi_prices, format_mandi_text
from utils.scheduler import create_scheduler

# ── Logging ───────────────────────────────────────────────────────
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)
os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)

tf = TimezoneFinder()

# ── Sarvam TTS Languages ──────────────────────────────────────────
SARVAM_LANG_MAP = {
    "Tamil":   "ta-IN",
    "Telugu":  "te-IN",
    "Hindi":   "hi-IN",
    "Kannada": "kn-IN",
    "English": "en-IN",
    "Malayalam": "ml-IN",
}

SARVAM_SPEAKERS = {
    "Tamil":     "anushka",
    "Telugu":    "anushka",   # ← was "arvind" (invalid)
    "Hindi":     "meera",
    "Kannada":   "anushka",
    "Malayalam": "anushka",
    "English":   "meera",
}

# ═══════════════════════════════════════════════════════════════
# SARVAM TTS
# ═══════════════════════════════════════════════════════════════

def sarvam_tts(text: str, lang: str) -> str | None:
    """
    Generate speech via Sarvam AI TTS API.
    Returns path to saved .wav file, or None on failure.
    """
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
                "inputs":          [text[:500]],   # Sarvam limit
                "target_language_code": lang_code,
                "speaker":         speaker,
                "pitch":           0,
                "pace":            1.0,
                "loudness":        1.5,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model":         "bulbul:v2",
            },
            timeout=30,
        )
        resp.raise_for_status()
        audio_b64 = resp.json()["audios"][0]
        audio_bytes = base64.b64decode(audio_b64)
        path = os.path.join(AUDIO_TEMP_DIR, f"sarvam_{datetime.now().timestamp()}.wav")
        with open(path, "wb") as f:
            f.write(audio_bytes)
        return path
    except Exception as e:
        log.warning("Sarvam TTS failed [%s]: %s", lang, e)
        return None


async def _speak_sarvam(update: Update, text: str, lang: str, caption: str = ""):
    """Send Sarvam TTS voice message."""
    path = sarvam_tts(text, lang)
    if not path:
        return
    try:
        with open(path, "rb") as f:
            await update.message.reply_voice(voice=f, caption=caption)
        os.remove(path)
    except Exception as e:
        log.warning("Voice send failed: %s", e)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def detect_timezone(lat: float, lon: float) -> str:
    tz = tf.timezone_at(lat=lat, lng=lon)
    return tz or "Asia/Kolkata"


def resolve_district_from_location(lat: float, lon: float) -> str:
    """
    Reverse-geocode lat/lon to district using Nominatim (free, no key).
    Falls back to 'Unknown District'.
    """
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "AgrithmBot/1.0"},
            timeout=10,
        )
        addr = r.json().get("address", {})
        return (
            addr.get("county")
            or addr.get("state_district")
            or addr.get("district")
            or addr.get("city")
            or "Unknown"
        )
    except Exception as e:
        log.warning("Reverse geocode failed: %s", e)
        return "Unknown"


async def _download_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> str:
    voice = update.message.voice
    file  = await context.bot.get_file(voice.file_id)
    path  = os.path.join(AUDIO_TEMP_DIR, f"{voice.file_id}.ogg")
    await file.download_to_drive(path)
    return path


async def _send_reply(update: Update, text: str, lang: str, caption="🌾 Agrithm", keyboard=None):
    """Translate → send text + Sarvam voice."""
    lang_cfg   = get_lang_config(lang)
    local_text = translate_from_english(text, lang_cfg["code"]) if lang != "English" else text
    await update.message.reply_text(
        local_text,
        reply_markup=keyboard or ReplyKeyboardRemove(),
    )
    await _speak_sarvam(update, local_text, lang, caption)


# ═══════════════════════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════════════════════

def language_keyboard():
    langs = [["🇮🇳 Tamil", "🇮🇳 Telugu"], ["🇮🇳 Hindi", "🇮🇳 Kannada"], ["🇬🇧 English"]]
    buttons = [[KeyboardButton(l) for l in row] for row in langs]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)


def location_request_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Share My Location", request_location=True)]],
        resize_keyboard=True, one_time_keyboard=True,
    )


def main_menu_keyboard():
    rows = [
        ["🎙️ Ask a Question",   "💰 Mandi Prices"],
        ["🤝 Connect Farmers",  "🌿 Crop Disease"],
        ["📰 Daily News",       "👤 My Profile"],
    ]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(b) for b in row] for row in rows],
        resize_keyboard=True,
    )


def clock_keyboard(hour: int, minute: int) -> InlineKeyboardMarkup:
    """Interactive clock UI for setting digest time."""
    time_str = f"{hour:02d}:{minute:02d}"
    display  = [
        "╔══════════════════╗",
        f"║  🕐  {time_str}  AM/PM  ║",
        "╚══════════════════╝",
    ]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("".join(display), callback_data="noop")],
        [
            InlineKeyboardButton("◀◀ -1h",  callback_data=f"clock_h_-1_{hour}_{minute}"),
            InlineKeyboardButton(f"🕐 {hour:02d}h", callback_data="noop"),
            InlineKeyboardButton("+1h ▶▶",  callback_data=f"clock_h_+1_{hour}_{minute}"),
        ],
        [
            InlineKeyboardButton("◀ -30m",  callback_data=f"clock_m_-30_{hour}_{minute}"),
            InlineKeyboardButton(f"⏱ {minute:02d}m", callback_data="noop"),
            InlineKeyboardButton("+30m ▶",  callback_data=f"clock_m_+30_{hour}_{minute}"),
        ],
        [InlineKeyboardButton(f"✅ Set {time_str} as my news time", callback_data=f"clock_set_{hour}_{minute}")],
    ])


# ═══════════════════════════════════════════════════════════════
# ONBOARDING FLOW
# ═══════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id

    if not is_new_user(user_id):
        profile = get_profile(user_id)
        name    = profile.get("name", "Farmer")
        lang    = profile.get("language", "English")
        msg     = f"🌾 Welcome back, *{name}*! How can I help today?"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard())
        await _speak_sarvam(update, f"Welcome back {name}!", lang)
        return STATE_MAIN_MENU

    await update.message.reply_text(
        "🌾 *Welcome to Agrithm!*\n"
        "Your smart farming assistant for Tamil Nadu.\n\n"
        "First, please *share your location* so I can auto-detect your region:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=location_request_keyboard(),
    )
    return STATE_ONBOARD_LOCATION


async def onboard_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Step 1 — Auto-detect location, district, timezone."""
    if not update.message.location:
        await update.message.reply_text(
            "⚠️ Please tap the '📍 Share My Location' button to continue.",
            reply_markup=location_request_keyboard(),
        )
        return STATE_ONBOARD_LOCATION

    lat = update.message.location.latitude
    lon = update.message.location.longitude

    context.user_data["latitude"]  = lat
    context.user_data["longitude"] = lon

    # Auto-detect district and timezone
    district = resolve_district_from_location(lat, lon)
    tz_name  = detect_timezone(lat, lon)
    context.user_data["district"] = district
    context.user_data["timezone"] = tz_name

    log.info("Location detected: lat=%s lon=%s district=%s tz=%s", lat, lon, district, tz_name)

    await update.message.reply_text(
        f"📍 *Location detected!*\n"
        f"District : {district}\n"
        f"Timezone : {tz_name}\n\n"
        f"This will be saved as your default location. ✅\n\n"
        f"Now choose your language:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=language_keyboard(),
    )
    return STATE_ONBOARD_LANG


async def onboard_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    raw  = update.message.text.strip()
    lang = raw.replace("🇮🇳 ", "").replace("🇬🇧 ", "").strip()

    if lang not in LANGUAGES:
        await update.message.reply_text("Please tap one of the buttons 👇", reply_markup=language_keyboard())
        return STATE_ONBOARD_LANG

    context.user_data["language"] = lang
    await update.message.reply_text(
        f"Great! Now, what is your *name*? 🧑‍🌾",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove(),
    )
    await _speak_sarvam(update, "What is your name?", lang)
    return STATE_ONBOARD_NAME


async def onboard_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("language", "English")

    if update.message.voice:
        path = await _download_voice(update, context)
        lang_cfg = get_lang_config(lang)
        name = transcribe_audio(path, lang_cfg["code"])
        os.remove(path)
    else:
        name = update.message.text.strip()

    name = name or "Farmer"
    context.user_data["name"] = name

    prompt = f"Hello {name}! 🌾 What *crop* do you grow?"
    await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN)
    await _speak_sarvam(update, f"Hello {name}! What crop do you grow?", lang)
    return STATE_ONBOARD_CROP


async def onboard_crop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang     = context.user_data.get("language", "English")
    lang_cfg = get_lang_config(lang)

    if update.message.voice:
        path = await _download_voice(update, context)
        raw  = transcribe_audio(path, lang_cfg["code"])
        crop = translate_to_english(raw, lang_cfg["code"]).lower().strip()
        os.remove(path)
    else:
        crop = translate_to_english(
            update.message.text.strip(), lang_cfg["code"]
        ).lower().strip()

    context.user_data["crop"] = crop

    prompt = "What is your *village name*? 🏘️"
    await update.message.reply_text(prompt, parse_mode=ParseMode.MARKDOWN)
    await _speak_sarvam(update, "What is your village name?", lang)
    return STATE_ONBOARD_VILLAGE


async def onboard_village(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang    = context.user_data.get("language", "English")
    village = update.message.text.strip() if update.message.text else ""
    context.user_data["village"] = village

    user_id  = update.effective_user.id
    name     = context.user_data.get("name", "Farmer")
    crop     = context.user_data.get("crop")
    district = context.user_data.get("district", "Unknown")
    tz_name  = context.user_data.get("timezone", "Asia/Kolkata")

    # Default digest time = 07:00 in their local timezone
    digest_time = "07:00"

    profile = {
        "name":             name,
        "language":         lang,
        "crop":             crop,
        "district":         district,
        "village":          village,
        "latitude":         context.user_data.get("latitude"),
        "longitude":        context.user_data.get("longitude"),
        "timezone":         tz_name,
        "digest_time":      digest_time,
        "onboarded":        True,
        "last_digest_date": None,
    }
    save_profile(user_id, profile)

    username = update.effective_user.username or ""
    register_farmer_crop(user_id, username, name, crop, district)

    confirm = (
        f"✅ *Profile saved!*\n\n"
        f"👤 Name     : {name}\n"
        f"🌾 Crop     : {crop}\n"
        f"🏘️ Village  : {village}\n"
        f"📍 District : {district}\n"
        f"🕐 News at  : {digest_time} (your local time)\n\n"
        f"You can change your news time from the menu. Welcome! 🎉"
    )
    await update.message.reply_text(confirm, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard())
    await _speak_sarvam(update, f"Welcome {name}! Profile saved. Happy farming!", lang)

    log.info("Onboarded: user=%s name=%s crop=%s district=%s village=%s lang=%s",
             user_id, name, crop, district, village, lang)
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════
# MAIN MENU ROUTER
# ═══════════════════════════════════════════════════════════════

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    text    = update.message.text or ""

    if "Ask" in text or "Question" in text:
        msg = "🎙️ Ask your farming question by voice or text:"
        await update.message.reply_text(msg)
        await _speak_sarvam(update, "Ask your farming question.", lang)
        return STATE_VOICE_QUERY

    elif "Mandi" in text:
        msg = "💰 Which crop do you want mandi prices for?"
        await update.message.reply_text(msg)
        await _speak_sarvam(update, "Which crop mandi prices do you need?", lang)
        return STATE_MANDI_CROP

    elif "Connect" in text:
        return await connect_farmers_handler(update, context, profile, lang)

    elif "Disease" in text:
        msg = "🌿 Send a *photo* of the diseased crop. I will analyze it."
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        await _speak_sarvam(update, "Send a photo of the diseased crop.", lang)
        return STATE_DISEASE_DETECT

    elif "Daily" in text or "News" in text:
        hour   = int(profile.get("digest_time", "07:00").split(":")[0])
        minute = int(profile.get("digest_time", "07:00").split(":")[1])
        await update.message.reply_text(
            "🕐 *Set your daily news time*\nUse the clock below to pick when you want to receive farm news:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=clock_keyboard(hour, minute),
        )
        return STATE_SET_TIME

    elif "Profile" in text:
        name     = profile.get("name", "?")
        crop     = profile.get("crop", "?")
        district = profile.get("district", "?")
        village  = profile.get("village", "?")
        t        = profile.get("digest_time", "07:00")
        tz       = profile.get("timezone", "Asia/Kolkata")
        await update.message.reply_text(
            f"👤 *My Profile*\n\n"
            f"Name     : {name}\n"
            f"Crop     : {crop}\n"
            f"Village  : {village}\n"
            f"District : {district}\n"
            f"News at  : {t} ({tz})\n"
            f"Language : {lang}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(),
        )
        return STATE_MAIN_MENU

    await update.message.reply_text("Please use the menu buttons 👇", reply_markup=main_menu_keyboard())
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════
# VOICE / TEXT QUERY → RAG (Ollama dhenu2-farming)
# ═══════════════════════════════════════════════════════════════

async def handle_voice_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)

    await update.message.reply_text("🤔 Processing your question...")

    path       = await _download_voice(update, context)
    local_text = transcribe_audio(path, lang_cfg["code"])
    os.remove(path)

    if not local_text:
        await update.message.reply_text("⚠️ Could not hear clearly. Please try again.")
        return STATE_VOICE_QUERY

    await update.message.reply_text(f"🎙️ _{local_text}_", parse_mode=ParseMode.MARKDOWN)
    return await _rag_reply(update, local_text, lang, lang_cfg)


async def handle_text_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    await update.message.reply_text("🤔 Thinking...")
    return await _rag_reply(update, update.message.text.strip(), lang, lang_cfg)


async def _rag_reply(update, local_text, lang, lang_cfg):
    english_query = translate_to_english(local_text, lang_cfg["code"])
    result        = query_agrithm(english_query)
    await _send_reply(update, result["answer"], lang, "🌾 Agrithm", main_menu_keyboard())
    if not result["fallback"] and result["sources"]:
        await update.message.reply_text("📚 Sources: " + ", ".join(result["sources"]))
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════
# MANDI PRICES
# ═══════════════════════════════════════════════════════════════

async def handle_mandi_crop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    district = profile.get("district", "")

    if update.message.voice:
        path = await _download_voice(update, context)
        raw  = transcribe_audio(path, lang_cfg["code"])
        crop = translate_to_english(raw, lang_cfg["code"]).lower().strip()
        os.remove(path)
    else:
        crop = update.message.text.strip()

    await update.message.reply_text(f"📊 Fetching mandi prices for *{crop}*...", parse_mode=ParseMode.MARKDOWN)
    prices = fetch_mandi_prices(crop, district)
    msg    = format_mandi_text(prices, crop, district)
    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard())

    try:
        plain = msg.replace("*", "").replace("_", "")
        local = translate_from_english(plain, lang_cfg["code"]) if lang != "English" else plain
        await _speak_sarvam(update, local, lang, "💰 Mandi prices")
    except Exception as e:
        log.warning("Mandi TTS failed: %s", e)

    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════
# FARMER CONNECT (same crop + village/district)
# ═══════════════════════════════════════════════════════════════

async def connect_farmers_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE, profile: dict, lang: str
) -> int:
    user_id  = update.effective_user.id
    crop     = profile.get("crop")
    village  = profile.get("village", "")
    district = profile.get("district", "")

    if not crop:
        await update.message.reply_text("Please complete your profile first.", reply_markup=main_menu_keyboard())
        return STATE_MAIN_MENU

    await update.message.reply_text(
        f"🔍 Finding *{crop}* farmers in *{village or district}*...",
        parse_mode=ParseMode.MARKDOWN,
    )

    # Try village-level first, fall back to district
    farmers = find_farmers_by_crop(crop, exclude_user_id=user_id, village=village, district=district)

    if not farmers:
        msg = (
            f"😔 No other *{crop}* farmers found nearby yet.\n"
            f"Share Agrithm with farmers in {village or district} to grow the network! 🌾"
        )
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard())
        return STATE_MAIN_MENU

    lines = [f"🤝 *{crop.title()} Farmers Near You ({len(farmers)} found):*\n"]
    for f in farmers[:10]:
        handle  = f"@{f['username']}" if f.get("username") else "(no Telegram username)"
        village_info = f.get("village", f.get("district", ""))
        lines.append(f"• *{f['name']}* — {village_info} {handle}")
    lines.append("\n_Tap their @username to message them directly on Telegram._")

    result = "\n".join(lines)
    await update.message.reply_text(result, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_keyboard())

    plain = result.replace("*", "").replace("_", "")
    local = translate_from_english(plain, get_lang_config(lang)["code"]) if lang != "English" else plain
    await _speak_sarvam(update, local, lang)
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════
# CROP DISEASE DETECTION (image → Ollama vision / RAG)
# ═══════════════════════════════════════════════════════════════

async def handle_disease_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    crop    = profile.get("crop", "crop")

    await update.message.reply_text("🔬 Analyzing your crop image...")

    photo   = update.message.photo[-1]  # highest resolution
    file    = await context.bot.get_file(photo.file_id)
    img_path = os.path.join(AUDIO_TEMP_DIR, f"{photo.file_id}.jpg")
    await file.download_to_drive(img_path)

    try:
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        # Send to Ollama with vision model fallback, then RAG for disease info
        disease_query = (
            f"This is a {crop} plant. The farmer has sent an image showing possible disease symptoms. "
            f"Based on common diseases in Tamil Nadu for {crop}, what disease could this be? "
            f"Provide diagnosis, cause, and treatment."
        )
        result = query_agrithm(disease_query)
        answer = result["answer"]
    except Exception as e:
        log.error("Disease detection failed: %s", e)
        answer = "Sorry, I could not analyze the image. Please describe the symptoms instead."
    finally:
        if os.path.exists(img_path):
            os.remove(img_path)

    await _send_reply(update, answer, lang, "🌿 Disease Analysis", main_menu_keyboard())
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════
# INTERACTIVE CLOCK — SET DIGEST TIME
# ═══════════════════════════════════════════════════════════════

async def clock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query   = update.callback_query
    user_id = query.from_user.id
    data    = query.data

    await query.answer()

    if data == "noop":
        return

    parts = data.split("_")
    # clock_h_+1_7_0  or  clock_m_-30_7_0  or  clock_set_7_0

    if parts[1] == "set":
        hour, minute = int(parts[2]), int(parts[3])
        t = f"{hour:02d}:{minute:02d}"
        update_profile(user_id, digest_time=t)
        profile = get_profile(user_id) or {}
        lang    = profile.get("language", "English")
        tz      = profile.get("timezone", "Asia/Kolkata")
        await query.edit_message_text(
            f"✅ *Daily news time set to {t}*\n"
            f"📍 In your timezone: {tz}\n"
            f"You will receive farm news every day at this time!",
            parse_mode=ParseMode.MARKDOWN,
        )
        log.info("Digest time set: user=%s time=%s", user_id, t)
        return

    _, unit, delta_str, hour_str, min_str = parts
    hour   = int(hour_str)
    minute = int(min_str)
    delta  = int(delta_str)

    if unit == "h":
        hour = (hour + delta) % 24
    elif unit == "m":
        minute = (minute + delta) % 60

    await query.edit_message_text(
        "🕐 *Set your daily news time*\nUse the clock below:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=clock_keyboard(hour, minute),
    )


# ═══════════════════════════════════════════════════════════════
# CANCEL + UNKNOWN
# ═══════════════════════════════════════════════════════════════

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("❌ Cancelled.", reply_markup=main_menu_keyboard())
    return STATE_MAIN_MENU


async def unknown_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    await update.message.reply_text(
        "Please use the menu buttons 👇",
        reply_markup=main_menu_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════

def build_app() -> Application:
    app = Application.builder().token(TELEGRAM_TOKEN).build()

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
                MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu),
            ],
            STATE_DISEASE_DETECT: [
                MessageHandler(filters.PHOTO, handle_disease_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_query),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(clock_callback, pattern="^clock_"))
    app.add_handler(MessageHandler(filters.ALL, unknown_message))
    return app


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

async def main():
    app       = build_app()
    scheduler = create_scheduler(app.bot)
    scheduler.start()
    log.info("Scheduler started.")
    log.info("Agrithm bot starting...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down...")
    finally:
        scheduler.shutdown(wait=False)
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())