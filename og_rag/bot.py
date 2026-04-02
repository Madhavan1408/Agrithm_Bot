"""Agrithm Telegram Bot — v8 (RAG Disease + News DB Edition)
────────────────────────────
Changes vs v7:
  1. DISEASE CHECK → RAG pipeline:
       - Image/text disease queries now embed description → search disease knowledge base
       - Relevant chunks injected into Ollama prompt as context (RAG-augmented diagnosis)
       - Falls back to direct Ollama if no relevant chunks found
  2. NORMAL QUERY → Direct Ollama only (no RAG, faster response)
  3. MY PROFILE FIX:
       - parse_mode=MARKDOWN added
       - Profile data displayed with correct field mapping
  4. DAILY NEWS button now shows fake news DB (news_db.py) FIRST,
     then offers clock to set alarm time
  5. All v7 functionality otherwise unchanged.
"""

# ── Process lock ────────────────────────────────────────────────────
import os, sys, atexit, signal

_BOT_DIR  = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(_BOT_DIR, "bot.lock")


def _acquire_lock() -> None:
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE) as f:
                old_pid = f.read().strip()
        except OSError:
            old_pid = "unknown"
        print(
            f"[ERROR] Another instance running (PID {old_pid}).\n"
            f"        Delete '{LOCK_FILE}' if stale.",
            file=sys.stderr,
        )
        sys.exit(1)
    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    atexit.register(_release_lock)
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))


def _release_lock() -> None:
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except OSError:
        pass


_acquire_lock()

# ── Imports ──────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

import re, asyncio, logging, base64, requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import pytz, httpx
from timezonefinder import TimezoneFinder

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler,
    ContextTypes, filters, PicklePersistence,
)
from telegram.constants import ParseMode

from agrithm_config import (
    TELEGRAM_TOKEN, LANGUAGES, AUDIO_TEMP_DIR,
    STATE_ONBOARD_LANG, STATE_ONBOARD_NAME, STATE_ONBOARD_CROP,
    STATE_ONBOARD_LOCATION, STATE_ONBOARD_TIME, STATE_ONBOARD_VILLAGE,
    STATE_MAIN_MENU, STATE_VOICE_QUERY, STATE_MANDI_CROP,
    STATE_SET_TIME, STATE_DISEASE_DETECT,
    STATE_CHAT_ROOM, SARVAM_API_KEY,
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
from utils.mandi_db import (
    query_mandi_db, format_mandi_db_text,
    detect_state, extract_location_from_query,
    COMMODITY_ALIASES as MANDI_CROP_ALIASES,
    MANDI_DB_AVAILABLE,
)
from utils.scheduler import create_scheduler
from utils.chat_room import (
    get_partner, set_active_chat, leave_chat, is_in_chat,
    save_message, get_history, mark_read, unread_count,
    queue_offline_notification, pop_offline_notifications,
    format_history_text, format_offline_notifications,
)
from alarm_handlers import (
    register_alarm_handlers,
    is_alarm_request, is_alarm_list_request,
    handle_alarm_set, handle_alarm_list,
    make_alarm_scheduler_job,
)
from utils.alarm import (
    get_all_active_alarms, should_fire_now, mark_alarm_fired,
)
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

# ── v8: News DB import ────────────────────────────────────────────────
from utils.news_db import (
    get_todays_news, format_news_text, search_disease_knowledge,
)

# ── Logging ──────────────────────────────────────────────────────────
os.makedirs(os.path.join(_BOT_DIR, "logs"), exist_ok=True)
os.makedirs(os.path.join(_BOT_DIR, "data"), exist_ok=True)
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(_BOT_DIR, "logs", "bot.log"), encoding="utf-8"
        ),
    ],
)
log = logging.getLogger(__name__)
os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)
tf = TimezoneFinder()

SARVAM_LANG_MAP = {k: v["code"]        for k, v in LANGUAGES.items()}
SARVAM_SPEAKERS = {k: v["tts_speaker"] for k, v in LANGUAGES.items()}

_tts_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="tts")
_geo_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="geo")

# ── Supabase env defaults ─────────────────────────────────────────────
os.environ.setdefault("SUPABASE_URL",      os.getenv("SUPABASE_URL", ""))
os.environ.setdefault("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

# ── Ollama ────────────────────────────────────────────────────────────
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "dhenu2-farming:latest")

FARMING_SYSTEM_PROMPT = (
    """
    You are **Agrithm v2**, an advanced AI agricultural assistant designed for Indian farmers, especially in South India.

You provide practical, accurate, and easy-to-understand guidance on:

* Crops, pests, diseases
* Soil health and fertilizers
* Irrigation and weather impact
* Market prices (mandi) and selling decisions
* Government schemes
* General farming advice

---

## 🌾 USER UNDERSTANDING (VERY IMPORTANT)

Farmers may:

* Use **voice input (speech-to-text errors likely)**
* Ask **short, unclear, or mixed-language queries**
* Mention **local crop names or incomplete symptoms**

### You MUST:

* Interpret intent intelligently
* Correct obvious speech/text mistakes silently
* Handle **multiple crops in one query**
* If unclear → ask **only ONE short follow-up question**

---

## 🔗 RAG + DATA USAGE

If external data (RAG) is provided:

* Prioritize that information
* Blend it naturally into the answer
* Do NOT say "according to database" or "RAG"

For mandi/price queries:

* Give price clearly
* Add **actionable advice** (sell now / wait / where demand is better)

---

## 🌍 LOCALIZATION (INDIA-FOCUSED)

Always consider:

* South Indian climate
* Seasonal cycles (Kharif / Rabi / Zaid)
* Water availability
* Cost constraints of small farmers

Recommend:

* Locally available fertilizers/pesticides
* Practical field-level solutions (not lab theory)

---

## 🧠 DECISION SUPPORT MODE

Don't just give information — help farmers decide.

Examples:

* "Should I spray now?" → give YES/NO + reason
* "Which fertilizer is better?" → compare + recommend
* "When to sell?" → suggest timing

---

## 💬 RESPONSE STYLE

* Use **simple English**
* Short sentences (good for voice output)
* No repetition of user question
* No technical jargon (or explain simply)
* Keep it **clean, spaced, and readable**

---

## 📊 OUTPUT STRUCTURE (SMART + FLEXIBLE)

### 🌿 Crop Problem / Disease

Problem: (1 line)
Cause: (simple reason)
Solution:

1. Step 1
2. Step 2
3. Step 3
   Note: (dosage / safety if needed)

---

### 💰 Mandi / Price Query

Answer: (current price clearly)
Advice:

1. Sell / wait / store
2. Best market option (if known)
   Tip: (storage or timing tip)

---

### 🌱 General Farming Question

Answer: (2–4 lines clear explanation)
Steps (if needed):

1. Step
2. Step
   Tip: (practical advice)

---

### ⚖️ Comparison / Decision

Options:

* Option 1: short
* Option 2: short
  Recommendation: best choice with reason

---

### ❓ If Question is Unclear

Ask:

* One short clarification question only

---

## ⚠️ SAFETY RULES

* Never suggest banned or dangerous chemicals
* Always include **safe usage guidance** for sprays
* Prefer **low-cost and locally available solutions**
* Avoid risky or unverified advice

---

## 🚫 STRICT RESTRICTIONS

* No long paragraphs
* No repeating the question
* No unnecessary headings
* No mention of KVK or external institutes
* No raw/unexplained data dumps

---

## 🎯 FINAL GOAL

Give **clear, actionable, and trustworthy advice** that a farmer can:

* Understand instantly
* Apply in the field
* Use to make better decisions

Even with limited knowledge, time, and resources.

    
    """
)

MODEL_OFFLINE_MSG = (
    "⚠️ *Farming assistant is currently offline.*\n\n"
    "The AI model is not reachable right now. "
    "Please try again in a few minutes.\n\n"
    "You can still use:\n"
    "🌾 Mandi Prices\n"
    "👥 Connect Farmers\n"
    "💬 Chat Room\n"
    "⏰ Alarms"
)

_NEWS_TIP_PROMPT = (
    "Give ONE practical farming tip for today in 2-3 short sentences. "
    "Make it specific to Indian farmers. No bullet points. "
    "Plain sentences only. Respond in English."
)


# ═══════════════════════════════════════════════════════════════════
# OLLAMA
# ═══════════════════════════════════════════════════════════════════

async def check_ollama_health() -> tuple[bool, bool]:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_URL}/api/tags")
            if resp.status_code != 200:
                return False, False
            models = [m.get("name", "") for m in resp.json().get("models", [])]
            model_ok = any(OLLAMA_MODEL in m for m in models)
            return True, model_ok
    except Exception:
        return False, False


async def query_ollama_async(prompt: str, system: str = FARMING_SYSTEM_PROMPT) -> str:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt},
                    ],
                    "stream": False,
                },
            )
        resp.raise_for_status()
        content = resp.json().get("message", {}).get("content", "").strip()
        return content or "I could not generate a response. Please try again."
    except httpx.TimeoutException:
        return "⏳ The farming assistant is taking too long. Please try again."
    except httpx.ConnectError:
        log.error("[Ollama] Connection refused")
        return MODEL_OFFLINE_MSG
    except Exception as exc:
        log.error("[Ollama] Error: %s", exc)
        return MODEL_OFFLINE_MSG


async def query_ollama_vision_async(
    prompt: str, image_b64: str, system: str = FARMING_SYSTEM_PROMPT,
) -> str:
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{OLLAMA_URL}/api/chat",
                json={
                    "model": OLLAMA_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": prompt, "images": [image_b64]},
                    ],
                    "stream": False,
                },
            )
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "").strip()
    except Exception as exc:
        log.warning("[Ollama-vision] %s — falling back to text", exc)
        return await query_ollama_async(prompt, system)


# ═══════════════════════════════════════════════════════════════════
# v8: DISEASE RAG PIPELINE
# ═══════════════════════════════════════════════════════════════════

def _build_disease_rag_context(description: str) -> str:
    """
    Search the disease knowledge base for relevant chunks using
    keyword matching (local RAG demo — no Supabase needed for disease).

    Returns a formatted context string to inject into the Ollama prompt,
    or an empty string if nothing relevant is found.
    """
    chunks = search_disease_knowledge(description, top_k=3)
    if not chunks:
        return ""

    parts = ["--- Relevant disease knowledge from Agrithm database ---"]
    for i, chunk in enumerate(chunks, 1):
        parts.append(f"[{i}] Topic: {chunk['topic']}\n{chunk['content']}")
    parts.append("--- End of knowledge context ---")
    context = "\n\n".join(parts)

    log.info(
        "[disease-RAG] ✅ Found %d relevant chunks for query: '%s...'",
        len(chunks), description[:60],
    )
    return context


async def disease_rag_answer(
    description: str,
    crop: str,
    district: str,
    image_b64: str | None = None,
) -> str:
    """
    Full RAG-augmented disease diagnosis pipeline.

    Flow:
      1. Search local disease knowledge base for relevant chunks
      2. If chunks found → inject as context into Ollama prompt
      3. If no chunks → send plain prompt to Ollama
      4. If image provided → use vision model; else text model
    """
    # Step 1: Get RAG context from disease knowledge base
    rag_context = _build_disease_rag_context(description)

    # Step 2: Build the prompt
    farmer_ctx = f"Farmer context: crop={crop}, district={district}, India.\n"

    if rag_context:
        # RAG-augmented prompt
        prompt = (
            f"{farmer_ctx}"
            f"Farmer's disease description: \"{description}\"\n\n"
            f"{rag_context}\n\n"
            f"Using the knowledge above as reference, diagnose the crop problem "
            f"and give practical, field-ready remedies. "
            f"Do not mention 'database' or 'knowledge base' in your answer."
        )
    else:
        # Fallback: direct Ollama without RAG
        prompt = (
            f"{farmer_ctx}"
            f"Farmer says: \"{description}\"\n"
            f"Diagnose the crop problem and give practical remedies."
        )

    log.info(
        "[disease-RAG] Using %s for diagnosis",
        "RAG+Ollama" if rag_context else "direct Ollama (no RAG match)",
    )

    # Step 3: Query Ollama (vision or text)
    if image_b64:
        return await query_ollama_vision_async(prompt, image_b64)
    else:
        return await query_ollama_async(prompt)


# ═══════════════════════════════════════════════════════════════════
# SMART ANSWER  —  NORMAL QUERIES GO DIRECT TO OLLAMA (no RAG)
# ═══════════════════════════════════════════════════════════════════

async def smart_answer(raw_user_text: str, lang_code: str, profile: dict) -> str:
    """
    Normal query pipeline → DIRECT Ollama only (no RAG).

    RAG is reserved for disease detection only.
    This keeps normal Q&A fast and simple.
    """
    # Translate to English
    try:
        english_q = translate_to_english(raw_user_text, lang_code)
        if not english_q or not english_q.strip():
            raise ValueError("empty translation")
    except Exception as exc:
        log.warning("[smart_answer] Translation failed: %s", exc)
        english_q = raw_user_text

    english_q = english_q.strip()

    # Build farmer context
    profile_crop = (profile.get("crop") or "").strip().lower()
    village      = (profile.get("village") or "").strip()
    district     = (profile.get("district") or "").strip()
    mentioned    = (extract_crop(english_q) or "").strip().lower()

    if mentioned and mentioned != profile_crop:
        crop_note = (
            f"Crop being asked about: {mentioned} "
            f"(registered crop: {profile_crop or 'not set'})"
        )
    elif profile_crop:
        crop_note = f"Crop grown: {profile_crop}"
    else:
        crop_note = None

    parts = []
    if crop_note:
        parts.append(crop_note)
    if village:
        parts.append(f"Village: {village}")
    if district:
        parts.append(f"District: {district}, India")

    context_header = "Farmer context:\n" + "\n".join(parts) + "\n\n" if parts else ""

    # Direct Ollama — no RAG for normal queries
    prompt = context_header + f"Question: {english_q}" if parts else english_q
    log.info("[smart_answer] Direct Ollama query (no RAG): '%s...'", english_q[:60])
    return await query_ollama_async(prompt)


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
                "inputs": [text[:500]],
                "target_language_code": lang_code,
                "speaker": speaker,
                "pitch": 0, "pace": 0.75, "loudness": 1.5,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model": "bulbul:v2",
            },
            timeout=60,
        )
        resp.raise_for_status()
        audios = resp.json().get("audios", [])
        if not audios:
            return None
        path = os.path.join(
            AUDIO_TEMP_DIR, f"tts_{int(datetime.now().timestamp())}.wav"
        )
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(audios[0]))
        return path
    except Exception as exc:
        log.warning("[TTS] %s", exc)
        return None


async def _speak_sarvam(
    update: Update, text: str, lang: str, caption: str = "Agrithm",
) -> None:
    if not text or not text.strip():
        return
    audio_path = None
    try:
        audio_path = await asyncio.get_running_loop().run_in_executor(
            _tts_executor, sarvam_tts, text, lang
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


async def _speak_sarvam_to_chat(
    bot, chat_id: int, text: str, lang: str, caption: str = "Agrithm"
) -> None:
    if not text or not text.strip():
        return
    audio_path = None
    try:
        loop = asyncio.get_running_loop()
        audio_path = await loop.run_in_executor(_tts_executor, sarvam_tts, text, lang)
        if not audio_path:
            return
        with open(audio_path, "rb") as fh:
            await bot.send_voice(chat_id=chat_id, voice=fh, caption=caption)
    except Exception as exc:
        log.warning("[_speak_sarvam_to_chat] %s", exc)
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════════
# VISUAL CLOCK FACE
# ═══════════════════════════════════════════════════════════════════

_EMOJI_DIGITS = {
    "0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣",
    "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣",
}

_CLOCK_EMOJI = [
    "🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚",
    "🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚",
]


def _to_emoji_digits(n: int, width: int = 2) -> str:
    s = str(n).zfill(width)
    return "".join(_EMOJI_DIGITS[c] for c in s)


def _period_label(hour: int) -> str:
    if hour < 6:
        return "🌙 Night"
    elif hour < 12:
        return "🌅 Morning"
    elif hour < 17:
        return "☀️ Afternoon"
    else:
        return "🌙 Evening"


def visual_clock_message(hour: int, minute: int) -> str:
    clock_icon = _CLOCK_EMOJI[hour % 24]
    h_emoji    = _to_emoji_digits(hour,   2)
    m_emoji    = _to_emoji_digits(minute, 2)
    period     = _period_label(hour)

    lines = [
        "╔══════════════════╗",
        "║  ⏰  Set Alarm &  ║",
        "║   News Time      ║",
        "╚══════════════════╝",
        "",
        f"        {clock_icon}",
        "",
        f"     {h_emoji}  ：  {m_emoji}",
        "",
        f"       {period}",
        "",
        "───────────────────",
        "Use the buttons below",
        "to set your time ⬇️",
    ]
    return "\n".join(lines)


def clock_buttons(hour: int, minute: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬆️ +1 Hour",  callback_data=f"clk_h_p1_{hour}_{minute}"),
            InlineKeyboardButton("⬇️ -1 Hour",  callback_data=f"clk_h_m1_{hour}_{minute}"),
        ],
        [
            InlineKeyboardButton("⬆️ +10 Min",  callback_data=f"clk_m_p10_{hour}_{minute}"),
            InlineKeyboardButton("⬇️ -10 Min",  callback_data=f"clk_m_m10_{hour}_{minute}"),
        ],
        [
            InlineKeyboardButton("⬆️ +1 Min",   callback_data=f"clk_m_p1_{hour}_{minute}"),
            InlineKeyboardButton("⬇️ -1 Min",   callback_data=f"clk_m_m1_{hour}_{minute}"),
        ],
        [InlineKeyboardButton(
            f"✅  Confirm  {hour:02d}:{minute:02d}  as my alarm time",
            callback_data=f"clk_set_{hour}_{minute}",
        )],
    ])


async def send_visual_clock(
    update: Update, hour: int, minute: int, lang: str,
    intro: str = "⏰ *Set your daily alarm & news time:*"
) -> None:
    await update.message.reply_text(intro, parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text(visual_clock_message(hour, minute))
    await update.message.reply_text(
        "👆 This is your current alarm time.\nUse buttons below to change it:",
        reply_markup=clock_buttons(hour, minute),
    )


# ═══════════════════════════════════════════════════════════════════
# KEYBOARD WRAPPERS
# ═══════════════════════════════════════════════════════════════════

def language_keyboard() -> ReplyKeyboardMarkup:
    return _lang_kb()


def location_request_keyboard() -> ReplyKeyboardMarkup:
    return _loc_kb()


def main_menu_keyboard(user_id: int = None, lang: str = "English") -> ReplyKeyboardMarkup:
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
            InlineKeyboardButton(label, callback_data=f"view_farmer_{f['user_id']}"),
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


# ═══════════════════════════════════════════════════════════════════
# MENU / CHAT ACTION RESOLVERS
# ═══════════════════════════════════════════════════════════════════

def _resolve_menu_action(text: str) -> str | None:
    tl = text.strip().lower()
    if not tl:
        return None
    for lang_buttons in MENU_BUTTONS.values():
        for action_key, label in lang_buttons.items():
            if label.strip().lower() == tl:
                return action_key
    _aliases: dict[str, str] = {
        "ask question": "ask",   "ask": "ask",
        "mandi prices": "mandi", "mandi": "mandi",
        "connect farmers": "connect", "connect": "connect",
        "disease check": "disease",   "disease": "disease",
        "daily news": "news",   "news": "news",
        "my profile": "profile", "profile": "profile",
        "chat room": "chat",    "chat": "chat",
        "my alarms": "alarm",   "alarms": "alarm",
        "alarm": "alarm",       "set alarm": "alarm",
        "set alarms": "alarm",
    }
    return _aliases.get(tl)


def _resolve_chat_action(text: str) -> str | None:
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
# HELPERS
# ═══════════════════════════════════════════════════════════════════

def detect_timezone(lat: float, lon: float) -> str:
    return tf.timezone_at(lat=lat, lng=lon) or "Asia/Kolkata"


def _resolve_location_blocking(lat: float, lon: float) -> tuple[str, str]:
    try:
        r    = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lon, "format": "json"},
            headers={"User-Agent": "AgrithmBot/1.0"},
            timeout=10,
        )
        addr = r.json().get("address", {})
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


def _query_mandi_db_sync(commodity, district, state, latest_only=True):
    return query_mandi_db(
        commodity=commodity, district=district,
        state=state, latest_only=latest_only,
    )


async def resolve_location_details(lat: float, lon: float) -> tuple[str, str]:
    return await asyncio.get_running_loop().run_in_executor(
        _geo_executor, _resolve_location_blocking, lat, lon
    )


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
    update: Update, text: str, lang: str,
    caption: str = "Agrithm", keyboard=None,
) -> None:
    lang_cfg   = get_lang_config(lang)
    local_text = (
        translate_from_english(text, lang_cfg["code"])
        if lang != "English" else text
    )
    await update.message.reply_text(
        local_text,
        reply_markup=keyboard if keyboard is not None else remove_keyboard(),
    )
    await _speak_sarvam(update, local_text, lang, caption)


async def _deliver_offline_notifications(update: Update, user_id: int) -> None:
    notifs = pop_offline_notifications(user_id)
    if notifs:
        await update.message.reply_text(
            format_offline_notifications(notifs),
            parse_mode=ParseMode.MARKDOWN,
        )


async def _smart_reply(
    update: Update, raw_user_text: str, lang: str,
    lang_cfg: dict, profile: dict, *, stay_in_voice_query: bool = True,
) -> int:
    user_id = update.effective_user.id
    try:
        answer = await smart_answer(raw_user_text, lang_cfg["code"], profile)
    except Exception as exc:
        log.error("[_smart_reply] %s", exc)
        answer = get_msg(ERROR_GENERIC, lang)

    await _send_reply(
        update, answer, lang, "Agrithm",
        keyboard=main_menu_keyboard(user_id, lang),
    )
    return STATE_VOICE_QUERY if stay_in_voice_query else STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════
# MENU ROUTING
# ═══════════════════════════════════════════════════════════════════

async def _route_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int | None:
    text   = (update.message.text or "").strip()
    action = _resolve_menu_action(text)
    if action is None:
        return None

    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    if not profile:
        await update.message.reply_text("Please type /start to set up your profile first.")
        return STATE_MAIN_MENU

    return await _dispatch_menu_action(action, update, context, profile)


async def _dispatch_menu_action(
    action: str,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    profile: dict,
) -> int:
    user_id  = update.effective_user.id
    lang     = profile.get("language", "English")

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

    # ── v8: DAILY NEWS — show news first, then offer alarm clock ─────
    if action == "news":
        await _show_daily_news_then_clock(update, profile, lang)
        return STATE_SET_TIME

    # ── v8: MY PROFILE — fixed rendering ─────────────────────────────
    if action == "profile":
        await _show_profile(update, user_id, profile, lang)
        return STATE_MAIN_MENU

    if action == "alarm":
        await handle_alarm_list(update, context)
        return STATE_MAIN_MENU

    if action == "chat":
        return await chat_room_entry(update, context, profile, lang)

    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════
# v8: MY PROFILE — clean fixed display
# ═══════════════════════════════════════════════════════════════════

async def _show_profile(
    update: Update, user_id: int, profile: dict, lang: str
) -> None:
    """Display the farmer's profile cleanly. Fixed in v8."""
    name     = profile.get("name") or "Not set"
    crop     = profile.get("crop") or "Not set"
    village  = profile.get("village") or "Not set"
    district = profile.get("district") or "Not set"
    tz       = profile.get("timezone") or "Asia/Kolkata"
    t        = profile.get("digest_time") or "07:00"
    native   = LANGUAGES.get(lang, {}).get("native", lang)

    # Try fmt() first (uses PROFILE_VIEW template); if it fails, use hardcoded safe format
    try:
        msg = fmt(
            PROFILE_VIEW, lang,
            name=name, crop=crop, village=village,
            district=district, time=t, tz=tz, lang_name=native,
        )
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(user_id, lang),
        )
    except Exception as exc:
        log.warning("[_show_profile] fmt() failed (%s), using fallback display", exc)
        # Safe hardcoded fallback that always works
        msg = (
            "👤 *Your Profile*\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🧑 *Name:* {name}\n"
            f"🌾 *Crop:* {crop}\n"
            f"🏘️ *Village:* {village}\n"
            f"📍 *District:* {district}\n"
            f"🌍 *Timezone:* {tz}\n"
            f"⏰ *Alarm Time:* {t}\n"
            f"🗣️ *Language:* {native}\n"
            "━━━━━━━━━━━━━━━━━━━━"
        )
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(user_id, lang),
        )


# ═══════════════════════════════════════════════════════════════════
# v8: DAILY NEWS — show news items, then clock
# ═══════════════════════════════════════════════════════════════════

async def _show_daily_news_then_clock(
    update: Update, profile: dict, lang: str
) -> None:
    """
    v8: Daily News button now:
      1. Shows today's top 5 farming news from the news DB
      2. Then shows the alarm clock so user can set/change their digest time
    """
    user_id = update.effective_user.id

    # Step 1: Fetch and display today's news
    try:
        news_items = get_todays_news(max_items=5)
        news_text  = format_news_text(news_items)
        await update.message.reply_text(
            news_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_keyboard(user_id, lang),
        )
    except Exception as exc:
        log.warning("[daily-news] Could not load news DB: %s", exc)
        await update.message.reply_text(
            "📰 *Today's farming news is loading...*\n\n"
            "_Could not fetch news right now. Please try again later._",
            parse_mode=ParseMode.MARKDOWN,
        )

    # Step 2: Show clock to let user set/change their alarm time
    hour, minute = map(int, profile.get("digest_time", "07:00").split(":"))
    await update.message.reply_text(
        "⏰ *Want to change your daily alarm time?*\n"
        "Use the buttons below to adjust when you receive this news every day:",
        parse_mode=ParseMode.MARKDOWN,
    )
    await update.message.reply_text(visual_clock_message(hour, minute))
    await update.message.reply_text(
        "👆 Current alarm time shown above. Adjust or confirm:",
        reply_markup=clock_buttons(hour, minute),
    )


# ═══════════════════════════════════════════════════════════════════
# CLOCK CALLBACK
# ═══════════════════════════════════════════════════════════════════

async def clock_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query   = update.callback_query
    user_id = query.from_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    data    = query.data or ""
    await query.answer()

    try:
        parts = data.split("_")
        kind  = parts[1]
        if kind == "set":
            hour, minute = int(parts[2]), int(parts[3])
            t  = f"{hour:02d}:{minute:02d}"
            update_profile(user_id, digest_time=t)
            tz = profile.get("timezone", "Asia/Kolkata")
            await query.edit_message_text(
                f"✅ *Alarm & news time set to {t}*\n"
                f"🌍 Timezone: {tz}\n\n"
                f"I will ring you every day at *{t}* and share a farming tip! 🌾",
                parse_mode=ParseMode.MARKDOWN,
            )
            return STATE_MAIN_MENU

        sign  = 1 if parts[2][0] == "p" else -1
        delta = int(parts[2][1:]) * sign
        hour  = int(parts[3])
        minute= int(parts[4])

        if kind == "h":
            hour   = (hour + delta) % 24
        else:
            minute = (minute + delta) % 60

        await query.message.reply_text(visual_clock_message(hour, minute))
        await query.edit_message_text(
            "👆 Updated time shown above.\nUse buttons to keep adjusting:",
            reply_markup=clock_buttons(hour, minute),
        )
        return STATE_SET_TIME

    except Exception as exc:
        log.error("[clock_callback] data=%s error=%s", data, exc)
        await query.edit_message_text(get_msg(ERROR_GENERIC, lang))
        return STATE_MAIN_MENU


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

    district, village_gps = await resolve_location_details(lat, lon)
    tz_name = detect_timezone(lat, lon)
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
    raw   = update.message.text.strip()
    match = re.search(r'\(([^)]+)\)$', raw)
    lang  = match.group(1).strip() if match else re.sub(r'[^\w\s]', '', raw).strip()

    if lang not in LANGUAGES:
        await update.message.reply_text(
            "Please tap one of the language buttons.",
            reply_markup=language_keyboard(),
        )
        return STATE_ONBOARD_LANG

    context.user_data["language"] = lang
    user_id = update.effective_user.id
    save_profile(user_id, {
        "name": "Farmer", "language": lang, "crop": "",
        "district": context.user_data.get("district", "Unknown"),
        "village":  context.user_data.get("village_gps", ""),
        "latitude": context.user_data.get("latitude"),
        "longitude":context.user_data.get("longitude"),
        "timezone": context.user_data.get("timezone", "Asia/Kolkata"),
        "digest_time": "07:00", "onboarded": False, "last_digest_date": None,
    })
    await update.message.reply_text(
        f"Language set to *{LANGUAGES[lang]['native']}*\n\n{get_msg(ASK_NAME, lang)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=remove_keyboard(),
    )
    await _speak_sarvam(update, get_msg(ASK_NAME, lang), lang)
    return STATE_ONBOARD_NAME


async def onboard_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang     = context.user_data.get("language", "English")
    lang_cfg = get_lang_config(lang)
    if update.message.voice:
        path = await _download_voice(update, context)
        raw_text = ""
        if path:
            try:
                raw_text, _ = _safe_transcribe(path, lang_cfg["code"])
            finally:
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
    await update.message.reply_text(get_msg(ASK_CROP, lang), reply_markup=remove_keyboard())
    await _speak_sarvam(update, get_msg(ASK_CROP, lang), lang)
    return STATE_ONBOARD_CROP


async def onboard_crop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang     = context.user_data.get("language", "English")
    lang_cfg = get_lang_config(lang)
    if update.message.voice:
        path = await _download_voice(update, context)
        raw_text = ""
        if path:
            try:
                raw_text, _ = _safe_transcribe(path, lang_cfg["code"])
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
    else:
        raw_text = (update.message.text or "").strip()

    english_text = translate_to_english(raw_text, lang_cfg["code"]) if raw_text else ""
    crop = extract_crop(english_text) or english_text.lower().strip() or "mixed"
    context.user_data["crop"] = crop
    gps_village = context.user_data.get("village_gps", "")
    msg = fmt(ASK_VILLAGE_GPS, lang, village=gps_village) if gps_village else get_msg(ASK_VILLAGE, lang)
    await update.message.reply_text(msg)
    await _speak_sarvam(update, get_msg(ASK_VILLAGE, lang), lang)
    return STATE_ONBOARD_VILLAGE


async def onboard_village(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang     = context.user_data.get("language", "English")
    lang_cfg = get_lang_config(lang)

    typed = ""
    if update.message.voice:
        path = await _download_voice(update, context)
        if path:
            try:
                typed, _ = _safe_transcribe(path, lang_cfg["code"])
                if typed:
                    typed = translate_to_english(typed, lang_cfg["code"]) or typed
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
    else:
        typed = (update.message.text or "").strip()

    village = typed or context.user_data.get("village_gps", "")
    context.user_data["village"] = village

    user_id  = update.effective_user.id
    name     = context.user_data.get("name", "Farmer")
    crop     = context.user_data.get("crop", "")
    district = context.user_data.get("district", "Unknown")
    tz_name  = context.user_data.get("timezone", "Asia/Kolkata")

    save_profile(user_id, {
        "name": name, "language": lang, "crop": crop,
        "district": district, "village": village,
        "latitude":  context.user_data.get("latitude"),
        "longitude": context.user_data.get("longitude"),
        "timezone": tz_name, "digest_time": "07:00",
        "onboarded": True, "last_digest_date": None,
    })
    register_farmer_crop(
        user_id, update.effective_user.username or "",
        name, crop, district, village=village,
    )
    try:
        await update.message.reply_text(
            fmt(PROFILE_SAVED, lang, name=name, crop=crop,
                village=village, district=district),
            reply_markup=remove_keyboard(),
        )
    except Exception as exc:
        log.warning("[onboard_village] PROFILE_SAVED failed: %s", exc)

    await update.message.reply_text(
        fmt(WELCOME_COMPLETE, lang, name=name),
        reply_markup=main_menu_keyboard(user_id, lang),
    )
    await _speak_sarvam(update, fmt(WELCOME_COMPLETE, lang, name=name), lang)
    return STATE_MAIN_MENU


async def onboard_time(update, context) -> int:
    lang = context.user_data.get("language", "English")
    if update.message and update.message.text:
        routed = await _route_menu(update, context)
        if routed is not None:
            return routed
    hour, minute = 7, 0
    await send_visual_clock(update, hour, minute, lang)
    return STATE_ONBOARD_TIME


async def onboard_time_clock_callback(update, context) -> int:
    query   = update.callback_query
    user_id = query.from_user.id
    lang    = context.user_data.get("language", "English")
    data    = query.data or ""
    await query.answer()

    try:
        parts = data.split("_")
        kind  = parts[1]
        if kind == "set":
            hour, minute = int(parts[2]), int(parts[3])
            t = f"{hour:02d}:{minute:02d}"
            context.user_data["digest_time"] = t
            update_profile(user_id, digest_time=t)
            gps_village = context.user_data.get("village_gps", "")
            msg = fmt(ASK_VILLAGE_GPS, lang, village=gps_village) if gps_village \
                  else get_msg(ASK_VILLAGE, lang)
            await query.edit_message_text(
                f"✅ Alarm time set to *{t}*.",
                parse_mode=ParseMode.MARKDOWN,
            )
            await context.bot.send_message(chat_id=user_id, text=msg)
            return STATE_ONBOARD_VILLAGE

        sign   = 1 if parts[2][0] == "p" else -1
        delta  = int(parts[2][1:]) * sign
        hour   = int(parts[3])
        minute = int(parts[4])

        if kind == "h":
            hour   = (hour + delta) % 24
        else:
            minute = (minute + delta) % 60

        await query.message.reply_text(visual_clock_message(hour, minute))
        await query.edit_message_text(
            "👆 Updated time shown above. Keep adjusting or confirm:",
            reply_markup=clock_buttons(hour, minute),
        )
        return STATE_ONBOARD_TIME

    except Exception as exc:
        log.error("[onboard_time_clock_callback] %s", exc)
        await query.edit_message_text(get_msg(ERROR_GENERIC, lang))
        return STATE_ONBOARD_VILLAGE


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
    if action is not None:
        return await _dispatch_menu_action(action, update, context, profile)

    if not text:
        await update.message.reply_text(
            get_msg(TYPE_QUESTION, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MAIN_MENU

    if is_alarm_request(text):
        await handle_alarm_set(update, context, text)
        return STATE_MAIN_MENU
    if is_alarm_list_request(text):
        await handle_alarm_list(update, context)
        return STATE_MAIN_MENU

    await update.message.reply_text(
        get_msg(THINKING, lang),
        reply_markup=main_menu_keyboard(user_id, lang),
    )
    return await _smart_reply(
        update, text, lang, lang_cfg, profile, stay_in_voice_query=False
    )


# ═══════════════════════════════════════════════════════════════════
# VOICE / TEXT QUERY
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

    local_text = ""
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
    routed = await _route_menu(update, context)
    if routed is not None:
        return routed

    user_id   = update.effective_user.id
    profile   = get_profile(user_id) or {}
    lang      = profile.get("language", "English")
    lang_cfg  = get_lang_config(lang)
    user_text = (update.message.text or "").strip()

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
# MANDI PRICES
# ═══════════════════════════════════════════════════════════════════

async def handle_mandi_crop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text:
        routed = await _route_menu(update, context)
        if routed is not None:
            return routed

    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)

    farmer_district = profile.get("district", "").strip()
    farmer_state    = detect_state(farmer_district) if farmer_district else None

    raw = ""
    if update.message.voice:
        path = await _download_voice(update, context)
        if path:
            try:
                raw, _ = _safe_transcribe(path, lang_cfg["code"])
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
    else:
        raw = (update.message.text or "").strip()

    english_raw = translate_to_english(raw, lang_cfg["code"]) if raw else ""
    crop        = extract_crop(english_raw) or english_raw.lower().strip()

    if not crop:
        await update.message.reply_text(
            get_msg(ASK_MANDI_CROP_NAME, lang),
            reply_markup=main_menu_keyboard(user_id, lang),
        )
        return STATE_MANDI_CROP

    await update.message.reply_text(fmt(FETCHING_MANDI, lang, crop=crop))

    try:
        loc_result = extract_location_from_query(english_raw)
        query_district, query_state = loc_result if loc_result else (None, None)
    except Exception:
        query_district, query_state = None, None

    use_district = query_district or farmer_district or None
    use_state    = query_state    or farmer_state    or None

    db_rows   = []
    used_dist = None

    loop = asyncio.get_running_loop()
    if MANDI_DB_AVAILABLE and use_district:
        db_rows = await loop.run_in_executor(
            _geo_executor, _query_mandi_db_sync, crop, use_district, use_state, True,
        )
        if db_rows:
            used_dist = use_district

    if MANDI_DB_AVAILABLE and not db_rows and use_state:
        db_rows = await loop.run_in_executor(
            _geo_executor, _query_mandi_db_sync, crop, None, use_state, True,
        )

    if MANDI_DB_AVAILABLE and not db_rows:
        db_rows = await loop.run_in_executor(
            _geo_executor, _query_mandi_db_sync, crop, None, None, True,
        )

    if db_rows:
        result_state = db_rows[0].get("state", use_state)
        msg = format_mandi_db_text(db_rows, crop, used_dist, result_state)
    else:
        prices = fetch_mandi_prices(crop, farmer_district, farmer_state, query_text=english_raw)
        msg    = format_mandi_text(prices, crop, farmer_district, farmer_state)

    await update.message.reply_text(
        msg, parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard(user_id, lang),
    )

    try:
        plain = re.sub(r'[*_🌾📍🏪📊📉📈•]', '', msg)
        local = translate_from_english(plain, lang_cfg["code"]) if lang != "English" else plain
        await _speak_sarvam(update, local[:500], lang, "Mandi prices")
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
    farmers = find_farmers_by_crop(crop, exclude_user_id=user_id, village=village, district=district)

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
    if not query.data.startswith("view_farmer_"):
        await query.answer()
        return
    target_id   = int(query.data.split("view_farmer_")[1])
    target_prof = get_profile(target_id) or {}
    await query.answer(
        f"{target_prof.get('name','Farmer')}\n"
        f"Crop: {target_prof.get('crop','?')}\n"
        f"Village: {target_prof.get('village','?')}\n"
        f"District: {target_prof.get('district','?')}",
        show_alert=True,
    )


# ═══════════════════════════════════════════════════════════════════
# v8: DISEASE DETECTION — RAG-augmented pipeline
# ═══════════════════════════════════════════════════════════════════

async def handle_disease_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    v8: Disease image → embed description → RAG knowledge lookup → Ollama vision answer.
    """
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

        # Build description string for RAG keyword search
        caption_text = update.message.caption or ""
        description = (
            f"{crop} plant disease. {caption_text}{symptom_note}".strip()
        )

        # v8: Use RAG-augmented disease diagnosis pipeline
        answer = await disease_rag_answer(
            description=description,
            crop=crop,
            district=district,
            image_b64=img_b64,
        )

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
        update, answer, lang, "Disease Analysis 🔬",
        main_menu_keyboard(user_id, lang),
    )
    return STATE_MAIN_MENU


async def handle_disease_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    v8: Disease voice → transcribe → RAG knowledge lookup → Ollama text answer.
    """
    if update.message.text:
        routed = await _route_menu(update, context)
        if routed is not None:
            return routed

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
        try:
            raw_text, _ = _safe_transcribe(path, lang_cfg["code"])
        finally:
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
    description  = f"{english_desc}{symptom_note}".strip()

    # v8: Use RAG-augmented disease diagnosis pipeline (no image)
    answer = await disease_rag_answer(
        description=description,
        crop=crop,
        district=district,
        image_b64=None,
    )

    await _send_reply(
        update, answer, lang, "Disease Analysis 🔬",
        main_menu_keyboard(user_id, lang),
    )
    return STATE_MAIN_MENU


async def handle_disease_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    v8: Disease text → RAG knowledge lookup → Ollama text answer.
    """
    routed = await _route_menu(update, context)
    if routed is not None:
        return routed

    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    text     = (update.message.text or "").strip()

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
    description  = f"{english_desc}{symptom_note}".strip()

    # v8: Use RAG-augmented disease diagnosis pipeline (no image)
    answer = await disease_rag_answer(
        description=description,
        crop=crop,
        district=district,
        image_b64=None,
    )

    await _send_reply(
        update, answer, lang, "Disease Analysis 🔬",
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
            fmt(CHAT_WITH, lang, partner=partner_name, n=10, history=hist_text),
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

    farmers = find_farmers_by_crop(crop, exclude_user_id=user_id, village=village, district=district)
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
    routed = await _route_menu(update, context)
    if routed is not None:
        return routed

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


async def global_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)

    if profile:
        text = (update.message.text or "").strip() if update.message else ""

        if text:
            routed = await _route_menu(update, context)
            if routed is not None:
                return

        if update.message and update.message.voice:
            path = await _download_voice(update, context)
            transcribed = ""
            if path:
                try:
                    transcribed, _ = _safe_transcribe(path, lang_cfg["code"])
                finally:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            if transcribed.strip():
                await update.message.reply_text(
                    get_msg(THINKING, lang),
                    reply_markup=main_menu_keyboard(user_id, lang),
                )
                await _smart_reply(update, transcribed, lang, lang_cfg, profile)
                return

        if text:
            await update.message.reply_text(
                get_msg(THINKING, lang),
                reply_markup=main_menu_keyboard(user_id, lang),
            )
            await _smart_reply(update, text, lang, lang_cfg, profile)
        return

    await update.message.reply_text("Please type /start to begin using Agrithm 🌾")


# ═══════════════════════════════════════════════════════════════════
# ALARM FIRE — sends text + TTS voice + news tip
# ═══════════════════════════════════════════════════════════════════

async def _fire_alarm_with_news(bot, user_id: int, alarm: dict) -> None:
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    label    = alarm.get("label", "Alarm")
    time_str = alarm.get("time", "")
    crop     = profile.get("crop", "farming")
    district = profile.get("district", "India")
    name     = profile.get("name", "Farmer")

    ring_text = (
        f"🔔🔔🔔 *ALARM — {label}* 🔔🔔🔔\n\n"
        f"⏰ It is *{time_str}*\n"
        f"👋 Good morning, *{name}*!\n\n"
        f"🌾 Your daily farming tip is coming..."
    )
    try:
        await bot.send_message(
            chat_id=user_id, text=ring_text, parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        log.warning("[alarm-fire] Ring message failed user=%s: %s", user_id, exc)
        return

    # v8: Also send one news item from the news DB at alarm time
    try:
        news_items = get_todays_news(max_items=1)
        if news_items:
            item = news_items[0]
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"📰 *Today's Top Farming News:*\n\n"
                    f"{item['category']}\n"
                    f"*{item['title']}*\n\n"
                    f"{item['body']}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as exc:
        log.warning("[alarm-fire] News item send failed: %s", exc)

    tip_prompt = (
        f"Farmer: {name}, crop: {crop}, district: {district}, India.\n"
        f"Give ONE practical tip for today in 2-3 short plain sentences. "
        f"No bullet points. In English only."
    )
    try:
        tip_english = await query_ollama_async(tip_prompt, system=_NEWS_TIP_PROMPT)
    except Exception:
        tip_english = f"Today, check your {crop} plants for any pests or water stress. Good luck farming!"

    try:
        if lang != "English":
            tip_local = translate_from_english(tip_english, lang_cfg["code"]) or tip_english
        else:
            tip_local = tip_english
    except Exception:
        tip_local = tip_english

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🌱 *Today's Farming Tip:*\n\n{tip_local}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        log.warning("[alarm-fire] Tip text failed user=%s: %s", user_id, exc)

    tts_text = f"Good morning {name}. {tip_local}"
    await _speak_sarvam_to_chat(bot, user_id, tts_text, lang, caption="🔔 Alarm & Daily Tip")

    mark_alarm_fired(user_id, alarm["id"])
    log.info("[alarm-fire] ✅ Fired '%s' for user %s at %s", label, user_id, time_str)


# ═══════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════

def build_app() -> Application:
    persistence_path = os.path.join(_BOT_DIR, "data", "bot_persistence.pkl")
    persistence = PicklePersistence(filepath=persistence_path)

    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .persistence(persistence)
        .build()
    )

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
                MessageHandler(filters.VOICE, onboard_village),
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_village),
            ],
            STATE_ONBOARD_TIME: [
                CallbackQueryHandler(onboard_time_clock_callback, pattern="^clk_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, onboard_time),
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
                CallbackQueryHandler(clock_callback, pattern="^clk_"),
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
            CommandHandler("cancel",    cancel),
            CommandHandler("leavechat", leavechat_command),
            CommandHandler("start",     start),
            MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu),
        ],
        name="agrithm_main",
        persistent=True,
        allow_reentry=True,
    )
    app.add_handler(conv)

    app.add_handler(CallbackQueryHandler(farmer_view_callback, pattern="^view_farmer_"))
    register_alarm_handlers(app)

    app.add_handler(MessageHandler(
        (filters.TEXT | filters.VOICE) & ~filters.COMMAND,
        global_fallback,
    ))

    return app


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

async def main() -> None:
    app       = build_app()
    scheduler = create_scheduler(app.bot)
    scheduler.start()

    loop = asyncio.get_running_loop()

    def _alarm_job():
        for user_id, alarm in get_all_active_alarms():
            if should_fire_now(alarm):
                future = asyncio.run_coroutine_threadsafe(
                    _fire_alarm_with_news(app.bot, user_id, alarm),
                    loop,
                )
                try:
                    future.result(timeout=30)
                except Exception as exc:
                    log.warning("[alarm-job] user=%s error=%s", user_id, exc)

    scheduler.add_job(
        _alarm_job,
        "interval", minutes=1,
        id="alarm_checker", replace_existing=True,
    )

    log.info("Agrithm bot starting (PID %s)...", os.getpid())

    server_up, model_ok = await check_ollama_health()
    if server_up and model_ok:
        log.info("[Ollama] ✅ Model reachable at %s  model=%s", OLLAMA_URL, OLLAMA_MODEL)
    elif server_up and not model_ok:
        log.warning("[Ollama] ⚠️  Server up but model '%s' not found.", OLLAMA_MODEL)
    else:
        log.warning("[Ollama] ⚠️  Server NOT reachable at %s", OLLAMA_URL)

    supabase_url = os.getenv("SUPABASE_URL", "")
    if supabase_url:
        log.info("[RAG] ✅ Supabase URL configured — RAG enabled for Supabase queries")
    else:
        log.info("[RAG] Disease RAG uses local knowledge base (no Supabase needed)")

    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        log.info("Shutting down...")
    finally:
        _tts_executor.shutdown(wait=False)
        _geo_executor.shutdown(wait=False)
        scheduler.shutdown(wait=False)
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())