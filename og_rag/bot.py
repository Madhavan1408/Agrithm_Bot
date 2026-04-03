"""Agrithm Telegram Bot — v9 + Crop Journey + Language Patch
────────────────────────────────────────────────────────────
Integrates:
  • crop_journey.py     — lifecycle DB, stage engine, journey store
  • crop_schedule.py    — daily card builder, LLM tip prompt
  • crop_journey_handlers.py — all Telegram handlers for journey feature
  • ui.py updates       — journey button added to main menu
  • bot_lang_patch.py   — ALL AI responses honour farmer's chosen language
"""

# ── Process lock ─────────────────────────────────────────────────────
import os, sys, atexit, signal

_BOT_DIR  = os.path.dirname(os.path.abspath(__file__))
LOCK_FILE = os.path.join(_BOT_DIR, "bot.lock")


def _acquire_lock() -> None:
    if os.path.exists(LOCK_FILE):
        try:
            old_pid = int(open(LOCK_FILE).read().strip())
            os.kill(old_pid, 0)
            print(
                f"[ERROR] Another instance running (PID {old_pid}).\n"
                f"        Delete '{LOCK_FILE}' if stale.",
                file=sys.stderr,
            )
            sys.exit(1)
        except (ProcessLookupError, ValueError, OSError):
            os.remove(LOCK_FILE)

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

# ── Imports ───────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

import re, asyncio, logging, base64, requests
from datetime import date, datetime, timedelta
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
    get_msg, fmt, get_lang_system_instruction,          # ← PATCH: added get_lang_system_instruction
    language_keyboard as _lang_kb,
    location_keyboard as _loc_kb,
    main_menu_keyboard as _menu_kb,
    chat_room_keyboard as _chat_kb,
    remove_keyboard,
)
from utils.news_db import get_todays_news, format_news_text
from utils.rag import get_relevant_chunks
# ── Crop Journey imports ──────────────────────────────────────────────
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
    fertilizer_due_today,
)
from utils.crop_schedule import (
    build_daily_card,
    build_daily_tip_prompt,
    build_journey_start_message,
)

# ── Logging ───────────────────────────────────────────────────────────
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

os.environ.setdefault("SUPABASE_URL",      os.getenv("SUPABASE_URL", ""))
os.environ.setdefault("SUPABASE_ANON_KEY", os.getenv("SUPABASE_ANON_KEY", ""))

OLLAMA_URL   = "http://localhost:11434"
OLLAMA_MODEL = "dhenu2-farming:latest"

# ── New conversation states ───────────────────────────────────────────
STATE_CHANGE_CROP     = 50
STATE_CHANGE_LANGUAGE = 51
# Crop Journey has no extra conversation states — it uses inline callbacks

# ═══════════════════════════════════════════════════════════════════════
# SYSTEM PROMPTS
# ═══════════════════════════════════════════════════════════════════════

# PATCH (REPLACEMENT_1): {lang_instruction} placeholder is resolved at
# runtime via build_farmer_context(), which prepends the instruction to
# every user-facing Ollama prompt.  The system prompt retains the
# placeholder so that if it is ever formatted directly it still works.
FARMING_SYSTEM_PROMPT = """
# ═══════════════════════════════════════════════════
#  AGRITHM — AI Agricultural Advisory System
#  Built for Indian Farmers · Chat Interface
# ═══════════════════════════════════════════════════

{lang_instruction}

IDENTITY
You are AGRITHM — a field-level AI agricultural advisor built exclusively for Indian farmers. You are NOT a general assistant. You make real farming decisions, give real product names, real dosages, and real costs.

FARMER CONTEXT (ALWAYS PROVIDED)
Every conversation begins with structured farmer context:
  - Farmer Name     → Address them by name in every response
  - Crop           → Reference their specific crop naturally
  - Village / District → Mention location for hyper-local advice
  - Language       → Respond ONLY in this language (see rule above)

THINKING BEFORE RESPONDING (SILENT)
Before answering, reason through:
  1. What is the most likely real-world problem here?
  2. What local factors — weather, season, region, crop — affect it?
  3. What is the safest and most effective solution?
  4. What exact step can the farmer take TODAY?

RESPONSE FORMAT (STRICT — DO NOT DEVIATE)

🌱 Problem Understanding
  Identify the issue clearly. Name the farmer's crop and location naturally.

🔍 Why This Happens
  Explain the cause — weather, pests, deficiency, or seasonal trigger.

✅ What To Do (Step-by-Step)
  Step 1: [Immediate action]
  Step 2: [Follow-up action]
  Step 3: [Monitoring or prevention]

💊 Recommended Products
  Product name + exact dosage per litre or per acre.
  Use only commonly available products at Indian agri-shops.

💰 Cost Awareness
  Approximate cost in Indian Rupees (₹). Give a range.

⚠️ Precautions
  Safety warnings. Dosage limits. What not to do.

📌 Extra Tip
  One practical, locally relevant insight the farmer will value.

MANDI / PRICE QUERIES
  → State current price clearly
  → Advise: sell now / wait / store — with a specific reason
  → Add: best nearby market option if known
  → End with: a storage or timing tip

PRESCRIPTION MODE (disease / pest / treatment queries)
Add this block at the END of your response:

🧾 Prescription Summary
  Problem  : [one line]
  Solution : [one line]
  Product  : [name]
  Dosage   : [exact amount per litre or acre]

BEHAVIOR RULES
✗ Never say "it depends" without giving a best recommendation
✗ Never give vague or generic advice
✗ Never be verbose — farmers need fast answers
✗ Never mention KVK, internal systems, or databases
✗ Never break the response structure
✗ Never suggest unverified or unsafe chemicals
✓ Always address the farmer by name
✓ Always reference their specific crop and village
✓ Always give exact product names, dosages, and rupee costs
✓ Always end pest/disease replies with the Prescription block
✓ Proactively warn about upcoming seasonal risks when relevant
✓ If a query is unclear → ask ONE short clarification question only
"""

_NEWS_TIP_PROMPT = (
    "You are a farming advisor for Indian farmers. "
    "Give ONE practical farming tip for today in 2-3 short plain sentences. "
    "Be specific to Indian conditions. No bullet points. Plain sentences only. "
    "Respond in English."
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

# ═══════════════════════════════════════════════════════════════════════
# OLLAMA
# ═══════════════════════════════════════════════════════════════════════

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
    # Resolve {lang_instruction} placeholder if present but unfilled
    if "{lang_instruction}" in system:
        system = system.replace("{lang_instruction}", "")
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
    if "{lang_instruction}" in system:
        system = system.replace("{lang_instruction}", "")
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


# ═══════════════════════════════════════════════════════════════════════
# FARMER CONTEXT BUILDER  (PATCH — REPLACEMENT_2)
# ═══════════════════════════════════════════════════════════════════════

def build_farmer_context(profile: dict) -> str:
    """
    Builds the farmer context block prepended to every Ollama prompt.
    Injects a language instruction so the model replies in the
    farmer's chosen language.
    """
    name     = profile.get("name", "Farmer")
    crop     = profile.get("crop", "mixed crops")
    village  = profile.get("village", "")
    district = profile.get("district", "")
    lang     = profile.get("language", "English")

    location_parts = []
    if village and village.lower() not in ("unknown", ""):
        location_parts.append(village)
    if district and district.lower() not in ("unknown", ""):
        location_parts.append(district)
    location_parts.append("India")
    location = ", ".join(location_parts)

    native_lang = LANGUAGES.get(lang, {}).get("native", lang)
    lang_instr  = get_lang_system_instruction(lang)   # ← PATCH

    return (
        f"{lang_instr}"
        "=== FARMER PROFILE ===\n"
        f"Name: {name}\n"
        f"Crop: {crop}\n"
        f"Location: {location}\n"
        f"Language: {native_lang}\n"
        "=== END PROFILE ===\n\n"
    )


# ═══════════════════════════════════════════════════════════════════════
# DISEASE RAG PIPELINE
# ═══════════════════════════════════════════════════════════════════════
async def disease_rag_answer(
    description: str,
    profile: dict,
    image_b64: str | None = None,
) -> str:
    """
    Full RAG pipeline for disease/pest queries.
 
    Flow:
      1. description (English) → get_relevant_chunks()  [utils/rag.py]
      2. rag.py embeds query → Supabase pgvector → top-K chunks returned
      3. bot.py builds prompt:
             [lang instruction] + [farmer profile] + [chunks] + [question]
      4. Ollama called ONCE with full context
      5. Answer returned to farmer
 
    If Supabase returns no chunks (fallback=True), query is still sent
    to Ollama using only farmer profile — model answers from its own knowledge.
    """
 
    # ── Farmer context + resolved system prompt ────────────────────
    farmer_ctx      = build_farmer_context(profile)
    lang            = profile.get("language", "English")
    lang_instr      = get_lang_system_instruction(lang)
    resolved_system = FARMING_SYSTEM_PROMPT.replace("{lang_instruction}", lang_instr)
 
    log.info("[disease-rag] Starting RAG for: %s", description[:80])
 
    # ── Run get_relevant_chunks in thread (CPU-bound embedding) ───
    loop = asyncio.get_running_loop()
    try:
        rag = await loop.run_in_executor(
            _tts_executor,
            get_relevant_chunks,
            description,
        )
    except Exception as exc:
        log.error("[disease-rag] get_relevant_chunks raised: %s", exc)
        rag = {"chunks_used": 0, "context_str": "", "fallback": True, "error": str(exc)}
 
    chunks_used = rag.get("chunks_used", 0)
    fallback    = rag.get("fallback", True)
    context_str = rag.get("context_str", "")
    error       = rag.get("error")
 
    if error:
        log.warning("[disease-rag] RAG error: %s", error)
 
    log.info(
        "[disease-rag] chunks_used=%d fallback=%s",
        chunks_used, fallback,
    )
 
    # ── Build Ollama prompt ────────────────────────────────────────
    if not fallback and chunks_used > 0 and context_str:
        # RAG chunks available — inject into prompt
        prompt = (
            f"{farmer_ctx}"
            f"Farmer's disease/pest description: \"{description}\"\n\n"
            f"{context_str}\n\n"
            f"Using ONLY the knowledge above as reference, diagnose the crop "
            f"problem and give practical field-ready remedies. "
            f"Do not mention 'database' or 'knowledge base' in your answer."
        )
        log.info("[disease-rag] Sending to Ollama WITH %d RAG chunks", chunks_used)
 
    else:
        # No chunks — Ollama answers from its own agricultural knowledge
        prompt = (
            f"{farmer_ctx}"
            f"Farmer says: \"{description}\"\n\n"
            f"Diagnose the crop problem and give practical field-ready remedies."
        )
        log.info("[disease-rag] No RAG chunks — sending direct to Ollama")
 
    # ── Single Ollama call (text or vision) ───────────────────────
    if image_b64:
        return await query_ollama_vision_async(prompt, image_b64, system=resolved_system)
    return await query_ollama_async(prompt, system=resolved_system)
 
# ═══════════════════════════════════════════════════════════════════════
# SMART ANSWER
# ═══════════════════════════════════════════════════════════════════════

async def smart_answer(raw_user_text: str, lang_code: str, profile: dict) -> str:
    try:
        english_q = translate_to_english(raw_user_text, lang_code)
        if not english_q or not english_q.strip():
            raise ValueError("empty translation")
    except Exception as exc:
        log.warning("[smart_answer] Translation failed: %s", exc)
        english_q = raw_user_text

    english_q  = english_q.strip()
    farmer_ctx = build_farmer_context(profile)

    profile_crop = (profile.get("crop") or "").strip().lower()
    mentioned    = (extract_crop(english_q) or "").strip().lower()
    crop_note    = ""
    if mentioned and mentioned != profile_crop:
        crop_note = f"(Note: Farmer is asking about {mentioned}, but registered crop is {profile_crop})\n\n"

    prompt = f"{farmer_ctx}{crop_note}Farmer's Question: {english_q}"
    return await query_ollama_async(prompt)


# ═══════════════════════════════════════════════════════════════════════
# SARVAM TTS
# ═══════════════════════════════════════════════════════════════════════

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
        path = os.path.join(AUDIO_TEMP_DIR, f"tts_{int(datetime.now().timestamp())}.wav")
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(audios[0]))
        return path
    except Exception as exc:
        log.warning("[TTS] %s", exc)
        return None


async def _speak_sarvam(update: Update, text: str, lang: str, caption: str = "Agrithm") -> None:
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


async def _speak_sarvam_to_chat(bot, chat_id: int, text: str, lang: str, caption: str = "Agrithm") -> None:
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


# ═══════════════════════════════════════════════════════════════════════
# VISUAL CLOCK
# ═══════════════════════════════════════════════════════════════════════

_EMOJI_DIGITS = {
    "0": "0️⃣", "1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣",
    "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣",
}
_CLOCK_EMOJI = [
    "🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚",
    "🕛","🕐","🕑","🕒","🕓","🕔","🕕","🕖","🕗","🕘","🕙","🕚",
]


def _to_emoji_digits(n: int, width: int = 2) -> str:
    return "".join(_EMOJI_DIGITS[c] for c in str(n).zfill(width))


def _period_label(hour: int) -> str:
    if hour < 6:    return "🌙 Night"
    elif hour < 12: return "🌅 Morning"
    elif hour < 17: return "☀️ Afternoon"
    else:           return "🌙 Evening"


def visual_clock_message(hour: int, minute: int) -> str:
    lines = [
        "╔══════════════════╗",
        "║  ⏰  Set Alarm &  ║",
        "║   News Time      ║",
        "╚══════════════════╝",
        "",
        f"        {_CLOCK_EMOJI[hour % 24]}",
        "",
        f"     {_to_emoji_digits(hour)}  ：  {_to_emoji_digits(minute)}",
        "",
        f"       {_period_label(hour)}",
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


# ═══════════════════════════════════════════════════════════════════════
# MAIN MENU KEYBOARD — with Journey button
# ═══════════════════════════════════════════════════════════════════════

def main_menu_keyboard_v9(user_id: int = None, lang: str = "English") -> ReplyKeyboardMarkup:
    """
    Extended main menu with:
    - Standard 8-button grid from ui.py
    - Row: 🌾 Change Crop | 🗣️ Change Language
    - Row: 🌱 My Crop Journey
    """
    unread = 0
    if user_id:
        partner = get_partner(user_id)
        if partner:
            unread = unread_count(user_id, partner)

    base_kb = _menu_kb(lang=lang, chat_unread=unread)
    existing_rows = list(base_kb.keyboard)

    existing_rows.append([
        KeyboardButton("🌾 Change Crop"),
        KeyboardButton("🗣️ Change Language"),
    ])
    existing_rows.append([
        KeyboardButton("🌱 My Crop Journey"),
    ])

    return ReplyKeyboardMarkup(existing_rows, resize_keyboard=True)


def language_keyboard() -> ReplyKeyboardMarkup:
    return _lang_kb()


def location_request_keyboard() -> ReplyKeyboardMarkup:
    return _loc_kb()


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


# ═══════════════════════════════════════════════════════════════════════
# CROP JOURNEY — INLINE KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════

def _crop_select_keyboard() -> InlineKeyboardMarkup:
    """Keyboard for picking a crop when not specified in text."""
    crops = list(CROP_LIFECYCLES.keys())
    rows  = []
    for i in range(0, len(crops), 2):
        row = []
        for crop in crops[i:i+2]:
            data        = CROP_LIFECYCLES[crop]
            stage_emoji = data["stages"][0]["emoji"] if data["stages"] else "🌱"
            row.append(InlineKeyboardButton(
                f"{stage_emoji} {crop.title()} ({data['total_days']}d)",
                callback_data=f"journey_crop_{crop}",
            ))
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="journey_cancel")])
    return InlineKeyboardMarkup(rows)


def _journey_confirm_keyboard(crop_key: str, sow_date_str: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "✅ Start Journey",
            callback_data=f"journey_confirm_{crop_key}_{sow_date_str}",
        ),
        InlineKeyboardButton("❌ Cancel", callback_data="journey_cancel"),
    ]])


def _journey_action_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 Full Timeline", callback_data="journey_timeline"),
        InlineKeyboardButton("🔔 Get Card Now",  callback_data="journey_now"),
        InlineKeyboardButton("🛑 End Journey",   callback_data="journey_end_confirm"),
    ]])


# ═══════════════════════════════════════════════════════════════════════
# CROP JOURNEY — TRIGGER DETECTION
# ═══════════════════════════════════════════════════════════════════════

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


def _extract_crop_from_text(text: str):
    for key, data in CROP_LIFECYCLES.items():
        for alias in data.get("aliases", []):
            if alias in text.lower():
                return key
    return None


# ═══════════════════════════════════════════════════════════════════════
# CROP JOURNEY — HANDLERS
# ═══════════════════════════════════════════════════════════════════════

async def handle_start_journey(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    alarm   = profile.get("digest_time", "06:00")

    # Check existing active journey
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

    crop_key = _extract_crop_from_text(text)

    if crop_key:
        today      = date.today()
        data       = CROP_LIFECYCLES[crop_key]
        total      = data["total_days"]
        har_date   = (today + timedelta(days=total)).strftime("%d %b %Y")
        stages_preview = "\n".join(
            f"  {s['emoji']} {s['name']} (Day {s['start']+1}–{s['end']})"
            for s in data["stages"]
        )
        msg = (
            f"🌱 *Start {crop_key.title()} Journey?*\n\n"
            f"📅 Sow date    : Today ({today.strftime('%d %b %Y')})\n"
            f"🎉 Est. harvest: {har_date}\n"
            f"⏱ Duration    : {total} days\n"
            f"🔔 Daily alarm : {alarm} every morning\n\n"
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
        supported = ", ".join(get_supported_crops())
        await update.message.reply_text(
            f"🌱 *Start a Crop Journey*\n\n"
            f"Which crop would you like to monitor?\n\n"
            f"Supported: _{supported}_\n\n"
            f"Tap your crop below:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_crop_select_keyboard(),
        )


async def handle_crop_status(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
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
    ai_tip = None
    try:
        ai_tip = await query_ollama_async(tip_prompt)
    except Exception:
        pass

    md, tts = build_daily_card(journey, name, ollama_tip=ai_tip)

    await update.message.reply_text(
        md,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_journey_action_keyboard(),
    )

    try:
        await _speak_sarvam(update, tts, lang, "Daily Crop Card 🌾")
    except Exception as e:
        log.warning("[journey-card] TTS failed: %s", e)


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

    lines.append(f"\n📅 Sow date: {journey['sow_date']}\n🎉 Harvest : {journey['harvest_date']}")

    await update.message.reply_text(
        "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=_journey_action_keyboard(),
    )


# ═══════════════════════════════════════════════════════════════════════
# CROP JOURNEY — CALLBACK QUERY HANDLER
# ═══════════════════════════════════════════════════════════════════════

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

    # ── User picked a crop from the selector ──────────────────────────
    if data.startswith("journey_crop_"):
        crop_key  = data[len("journey_crop_"):]
        today     = date.today()
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

    # ── Confirm and start the journey ─────────────────────────────────
    if data.startswith("journey_confirm_"):
        parts    = data[len("journey_confirm_"):].split("_", 1)
        crop_key = parts[0]
        sow_str  = parts[1] if len(parts) > 1 else date.today().isoformat()
        sow_date = date.fromisoformat(sow_str)

        journey = start_journey(
            user_id    = user_id,
            crop_key   = crop_key,
            sow_date   = sow_date,
            alarm_time = alarm,
            timezone   = tz,
        )
        msg = build_journey_start_message(journey, name, lang=lang)
        await query.edit_message_text(msg, parse_mode=ParseMode.MARKDOWN)
        return

    # ── Get card now ───────────────────────────────────────────────────
    if data == "journey_now":
        journey = get_journey(user_id)
        if not journey or not journey.get("active"):
            await query.message.reply_text("No active journey found.")
            return
        tip_prompt = build_daily_tip_prompt(journey, profile)
        ai_tip = None
        try:
            ai_tip = await query_ollama_async(tip_prompt)
        except Exception:
            pass
        md, tts = build_daily_card(journey, name, ollama_tip=ai_tip, lang=lang)
        await query.message.reply_text(
            md,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=_journey_action_keyboard(),
        )
        try:
            await _speak_sarvam_to_chat(
                query.message._bot, user_id, tts, lang, "Daily Crop Card 🌾"
            )
        except Exception:
            pass
        return

    # ── Full timeline ──────────────────────────────────────────────────
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
        lines     = [f"🗺 *{journey['crop_name']} Timeline* — Day {day} of {total}\n"]
        for s in stages:
            is_current = s["start"] <= day < s["end"]
            is_done    = day >= s["end"]
            marker = "▶ *NOW*" if is_current else ("✓ Done" if is_done else f"○ In {s['start']-day}d")
            critical = " ⚠️" if s.get("critical") else ""
            lines.append(
                f"{s['emoji']} {s['name']}{critical} "
                f"(Day {s['start']+1}–{s['end']}) — {marker}"
            )
        await query.message.reply_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # ── End journey confirm ────────────────────────────────────────────
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

    # ── Cancel ─────────────────────────────────────────────────────────
    if data == "journey_cancel":
        await query.edit_message_text("❌ Cancelled.")
        return


# ═══════════════════════════════════════════════════════════════════════
# CROP JOURNEY — MORNING CARD FIRE (PATCH — REPLACEMENT_4 applied)
# ═══════════════════════════════════════════════════════════════════════

# PATCH (REPLACEMENT_4): Localised ring templates extracted to module-level
# constant so they can also be reused by other callers.
_JOURNEY_RING_TEMPLATES = {
    "English":   "🌾 *Good morning, {name}!*\n🔔 Your *{crop}* Daily Crop Card is ready.\n📅 Day {day} of {total} — {stage}",
    "Hindi":     "🌾 *सुप्रभात, {name}!*\n🔔 आपका *{crop}* डेली क्रॉप कार्ड तैयार है।\n📅 दिन {day} / {total} — {stage}",
    "Telugu":    "🌾 *శుభోదయం, {name}!*\n🔔 మీ *{crop}* డైలీ క్రాప్ కార్డ్ సిద్ధం.\n📅 రోజు {day} / {total} — {stage}",
    "Tamil":     "🌾 *காலை வணக்கம், {name}!*\n🔔 உங்கள் *{crop}* தினசரி பயிர் அட்டை தயார்.\n📅 நாள் {day} / {total} — {stage}",
    "Kannada":   "🌾 *ಶುಭೋದಯ, {name}!*\n🔔 ನಿಮ್ಮ *{crop}* ದೈನಂದಿನ ಬೆಳೆ ಕಾರ್ಡ್ ಸಿದ್ಧ.\n📅 ದಿನ {day} / {total} — {stage}",
    "Malayalam": "🌾 *സുപ്രഭാതം, {name}!*\n🔔 നിങ്ങളുടെ *{crop}* ഡെയ്‌ലി ക്രോപ്പ് കാർഡ് തയ്യാർ.\n📅 ദിനം {day} / {total} — {stage}",
    "Marathi":   "🌾 *सुप्रभात, {name}!*\n🔔 तुमचे *{crop}* डेली क्रॉप कार्ड तयार आहे.\n📅 दिवस {day} / {total} — {stage}",
    "Gujarati":  "🌾 *સુપ્રભાત, {name}!*\n🔔 તમારું *{crop}* ડેઈલી ક્રોપ કાર્ડ તૈયાર છે.\n📅 દિવસ {day} / {total} — {stage}",
}


def build_journey_ring_text(
    name: str, crop: str, day: int, total: int,
    stage: str, lang: str = "English",
) -> str:
    """Returns the localised morning ring message for crop journey cards."""
    tmpl = _JOURNEY_RING_TEMPLATES.get(lang) or _JOURNEY_RING_TEMPLATES["English"]
    return tmpl.format(name=name, crop=crop, day=day, total=total, stage=stage)


async def _fire_journey_card(
    bot,
    user_id:  int,
    journey:  dict,
) -> None:
    """
    Sends the daily crop card with AI tip and TTS voice.
    Called every morning from the alarm scheduler.
    """
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    name    = profile.get("name", "Farmer")
    day     = get_current_day(journey)
    crop    = journey["crop_name"]
    total   = journey["total_days"]

    log.info(
        "[journey-fire] Sending day %s/%s card to user %s (%s)",
        day, total, user_id, crop,
    )

    # PATCH (REPLACEMENT_4): use build_journey_ring_text() helper
    try:
        stage      = get_stage_for_day(journey["crop_key"], day)
        stage_name = stage["name"] if stage else "Complete"
        ring_msg   = build_journey_ring_text(
            name=name, crop=crop, day=day, total=total,
            stage=stage_name, lang=lang,
        )
        await bot.send_message(
            chat_id=user_id, text=ring_msg, parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        log.warning("[journey-fire] Ring failed: %s", e)
        return

    # Build AI tip
    ai_tip = None
    try:
        tip_prompt = build_daily_tip_prompt(journey, profile)
        ai_tip     = await query_ollama_async(tip_prompt)
    except Exception as e:
        log.warning("[journey-fire] AI tip failed: %s", e)

    # Send full card
    md = tts_text = None
    try:
        md, tts_text = build_daily_card(journey, name, ollama_tip=ai_tip, lang=lang)
        await bot.send_message(
            chat_id=user_id,
            text=md,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 Timeline",    callback_data="journey_timeline"),
                InlineKeyboardButton("🛑 End Journey", callback_data="journey_end_confirm"),
            ]]),
        )
    except Exception as e:
        log.warning("[journey-fire] Card send failed: %s", e)
        return

    # TTS voice
    if tts_text:
        audio_path = None
        try:
            loop       = asyncio.get_running_loop()
            audio_path = await loop.run_in_executor(
                _tts_executor, sarvam_tts, tts_text[:500], lang
            )
            if audio_path:
                with open(audio_path, "rb") as fh:
                    await bot.send_voice(
                        chat_id=user_id, voice=fh, caption="🌾 Daily Crop Card"
                    )
        except Exception as e:
            log.warning("[journey-fire] TTS failed: %s", e)
        finally:
            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

    log.info(
        "[journey-fire] ✅ Card sent to user %s — %s Day %s", user_id, crop, day
    )


# ═══════════════════════════════════════════════════════════════════════
# MENU / CHAT ACTION RESOLVERS
# ═══════════════════════════════════════════════════════════════════════

def _resolve_menu_action(text: str) -> str | None:
    tl = text.strip().lower()
    if not tl:
        return None

    # v9 extra actions
    if tl in ("🌾 change crop", "change crop"):
        return "change_crop"
    if tl in ("🗣️ change language", "change language"):
        return "change_language"
    # Crop Journey button
    if tl in ("🌱 my crop journey", "my crop journey", "crop journey"):
        return "journey"

    for lang_buttons in MENU_BUTTONS.values():
        for action_key, label in lang_buttons.items():
            if label.strip().lower() == tl:
                return action_key

    _aliases: dict[str, str] = {
        "ask question": "ask",     "ask": "ask",
        "mandi prices": "mandi",   "mandi": "mandi",
        "connect farmers": "connect", "connect": "connect",
        "disease check": "disease",   "disease": "disease",
        "daily news": "news",      "news": "news",
        "my profile": "profile",   "profile": "profile",
        "chat room": "chat",       "chat": "chat",
        "my alarms": "alarm",      "alarms": "alarm",
        "alarm": "alarm",          "set alarm": "alarm",
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


# ═══════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════

def detect_timezone(lat: float, lon: float) -> str:
    return tf.timezone_at(lat=lat, lng=lon) or "Asia/Kolkata"


def _resolve_location_blocking(lat: float, lon: float) -> tuple[str, str]:
    try:
        r = requests.get(
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
        keyboard=main_menu_keyboard_v9(user_id, lang),
    )
    return STATE_VOICE_QUERY if stay_in_voice_query else STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════
# MENU ROUTING
# ═══════════════════════════════════════════════════════════════════════

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
    action: str, update: Update,
    context: ContextTypes.DEFAULT_TYPE, profile: dict,
) -> int:
    user_id = update.effective_user.id
    lang    = profile.get("language", "English")

    if action == "ask":
        await update.message.reply_text(
            get_msg(ASK_QUESTION_PROMPT, lang),
            reply_markup=main_menu_keyboard_v9(user_id, lang),
        )
        return STATE_VOICE_QUERY

    if action == "mandi":
        await update.message.reply_text(
            get_msg(ASK_MANDI_CROP, lang),
            reply_markup=main_menu_keyboard_v9(user_id, lang),
        )
        return STATE_MANDI_CROP

    if action == "connect":
        return await connect_farmers_handler(update, context, profile, lang)

    if action == "disease":
        await update.message.reply_text(
            get_msg(DISEASE_PROMPT, lang),
            reply_markup=main_menu_keyboard_v9(user_id, lang),
        )
        return STATE_DISEASE_DETECT

    if action == "news":
        await _show_daily_news_then_clock(update, profile, lang)
        return STATE_SET_TIME

    if action == "profile":
        await _show_profile(update, user_id, profile, lang)
        return STATE_MAIN_MENU

    if action == "alarm":
        await handle_alarm_list(update, context)
        return STATE_MAIN_MENU

    if action == "chat":
        return await chat_room_entry(update, context, profile, lang)

    if action == "change_crop":
        return await handle_change_crop_start(update, context, profile, lang)

    if action == "change_language":
        return await handle_change_language_start(update, context, profile, lang)

    # ── Crop Journey menu button ──────────────────────────────────────
    if action == "journey":
        journey = get_journey(user_id)
        if journey and journey.get("active"):
            await handle_crop_status(update, context)
        else:
            await handle_start_journey(update, context, "start journey")
        return STATE_MAIN_MENU

    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════
# MY PROFILE
# ═══════════════════════════════════════════════════════════════════════

async def _show_profile(update: Update, user_id: int, profile: dict, lang: str) -> None:
    name     = profile.get("name")     or "Not set"
    crop     = profile.get("crop")     or "Not set"
    village  = profile.get("village")  or "Not set"
    district = profile.get("district") or "Not set"
    tz       = profile.get("timezone") or "Asia/Kolkata"
    t        = profile.get("digest_time") or "07:00"
    native   = LANGUAGES.get(lang, {}).get("native", lang)
    onboarded = "✅ Complete" if profile.get("onboarded") else "⏳ In Progress"

    journey     = get_journey(user_id)
    journey_line = ""
    if journey and journey.get("active"):
        day        = get_current_day(journey)
        total      = journey["total_days"]
        stage      = get_stage_for_day(journey["crop_key"], day)
        stage_name = stage["name"] if stage else "Complete"
        journey_line = (
            f"\n🌱 *Journey:*  {journey['crop_name']} — "
            f"Day {day}/{total} ({stage_name})"
        )

    msg = (
        "👤 *Your Agrithm Profile*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🧑 *Name:*      {name}\n"
        f"🌾 *Crop:*      {crop}\n"
        f"🏘️ *Village:*   {village}\n"
        f"📍 *District:*  {district}\n"
        f"🌍 *Timezone:*  {tz}\n"
        f"⏰ *Alarm:*     {t}\n"
        f"🗣️ *Language:*  {native}\n"
        f"📋 *Status:*    {onboarded}"
        f"{journey_line}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "_Use '🌾 Change Crop' or '🗣️ Change Language' or '🌱 My Crop Journey' below._"
    )

    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard_v9(user_id, lang),
    )


# ═══════════════════════════════════════════════════════════════════════
# CHANGE CROP
# ═══════════════════════════════════════════════════════════════════════

async def handle_change_crop_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    profile: dict, lang: str,
) -> int:
    current_crop = profile.get("crop", "Not set")
    await update.message.reply_text(
        f"🌾 *Change Your Crop*\n\n"
        f"Current crop: *{current_crop}*\n\n"
        f"Please type your new crop name:\n"
        f"_(e.g. Paddy, Tomato, Cotton, Groundnut)_",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=remove_keyboard(),
    )
    return STATE_CHANGE_CROP


async def handle_change_crop_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)

    raw_text = ""
    if update.message.voice:
        path = await _download_voice(update, context)
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

    if not raw_text:
        await update.message.reply_text(
            "Please type your crop name.",
            reply_markup=remove_keyboard(),
        )
        return STATE_CHANGE_CROP

    english_text = translate_to_english(raw_text, lang_cfg["code"]) if raw_text else ""
    new_crop = extract_crop(english_text) or english_text.lower().strip() or raw_text.strip()

    update_profile(user_id, crop=new_crop)

    name     = profile.get("name", "Farmer")
    district = profile.get("district", "")
    village  = profile.get("village", "")
    register_farmer_crop(
        user_id, update.effective_user.username or "",
        name, new_crop, district, village=village,
    )

    await update.message.reply_text(
        f"✅ *Crop updated successfully!*\n\n"
        f"Your new crop: *{new_crop.title()}*\n\n"
        f"All future advice will be tailored to your {new_crop} crop. 🌾",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard_v9(user_id, lang),
    )
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════
# CHANGE LANGUAGE
# ═══════════════════════════════════════════════════════════════════════

async def handle_change_language_start(
    update: Update, context: ContextTypes.DEFAULT_TYPE,
    profile: dict, lang: str,
) -> int:
    current_native = LANGUAGES.get(lang, {}).get("native", lang)
    await update.message.reply_text(
        f"🗣️ *Change Your Language*\n\n"
        f"Current language: *{current_native}*\n\n"
        f"Please select your new language:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=language_keyboard(),
    )
    return STATE_CHANGE_LANGUAGE


async def handle_change_language_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    raw     = (update.message.text or "").strip()

    match = re.search(r'\(([^)]+)\)$', raw)
    lang  = match.group(1).strip() if match else re.sub(r'[^\w\s]', '', raw).strip()

    if lang not in LANGUAGES:
        await update.message.reply_text(
            "Please tap one of the language buttons.",
            reply_markup=language_keyboard(),
        )
        return STATE_CHANGE_LANGUAGE

    update_profile(user_id, language=lang)
    native = LANGUAGES[lang]["native"]

    await update.message.reply_text(
        f"✅ *Language updated to {native}!*\n\n"
        f"All future responses will be in *{native}*. 🗣️",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard_v9(user_id, lang),
    )
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════
# DAILY NEWS
# ═══════════════════════════════════════════════════════════════════════

async def _show_daily_news_then_clock(update: Update, profile: dict, lang: str) -> None:
    user_id  = update.effective_user.id
    lang_cfg = get_lang_config(lang)

    try:
        news_items = get_todays_news(max_items=5)

        if lang == "English":
            news_text = format_news_text(news_items)
            await update.message.reply_text(
                news_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard_v9(user_id, lang),
            )
        else:
            await update.message.reply_text(
                "📰 *Loading today's farming news...*",
                parse_mode=ParseMode.MARKDOWN,
            )
            translated_items = []
            for item in news_items:
                try:
                    translated_items.append({
                        **item,
                        "title": translate_from_english(item["title"], lang_cfg["code"]) or item["title"],
                        "body":  translate_from_english(item["body"],  lang_cfg["code"]) or item["body"],
                    })
                except Exception:
                    translated_items.append(item)

            await update.message.reply_text(
                format_news_text(translated_items),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard_v9(user_id, lang),
            )

    except Exception as exc:
        log.warning("[daily-news] Could not load news: %s", exc)
        await update.message.reply_text(
            "📰 *Today's farming news is loading...*\n\n"
            "_Could not fetch news right now. Please try again later._",
            parse_mode=ParseMode.MARKDOWN,
        )

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


# ═══════════════════════════════════════════════════════════════════════
# CLOCK CALLBACK
# ═══════════════════════════════════════════════════════════════════════

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
            "👆 Updated time shown above.\nUse buttons to keep adjusting:",
            reply_markup=clock_buttons(hour, minute),
        )
        return STATE_SET_TIME

    except Exception as exc:
        log.error("[clock_callback] data=%s error=%s", data, exc)
        await query.edit_message_text(get_msg(ERROR_GENERIC, lang))
        return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════
# ONBOARDING
# ═══════════════════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    if not is_new_user(user_id):
        profile = get_profile(user_id) or {}
        name    = profile.get("name", "Farmer")
        lang    = profile.get("language", "English")
        await update.message.reply_text(
            fmt(WELCOME_BACK, lang, name=name),
            reply_markup=main_menu_keyboard_v9(user_id, lang),
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
        "district": district, "village": village_gps, "timezone": tz_name,
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
        "name":        "Farmer",
        "language":    lang,
        "crop":        "",
        "district":    context.user_data.get("district", "Unknown"),
        "village":     context.user_data.get("village", ""),
        "latitude":    context.user_data.get("latitude"),
        "longitude":   context.user_data.get("longitude"),
        "timezone":    context.user_data.get("timezone", "Asia/Kolkata"),
        "digest_time": "07:00",
        "onboarded":   False,
        "last_digest_date": None,
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

    user_id  = update.effective_user.id
    name     = context.user_data.get("name", "Farmer")
    district = context.user_data.get("district", "Unknown")
    village  = context.user_data.get("village", "")
    tz_name  = context.user_data.get("timezone", "Asia/Kolkata")

    save_profile(user_id, {
        "name":        name,
        "language":    lang,
        "crop":        crop,
        "district":    district,
        "village":     village,
        "latitude":    context.user_data.get("latitude"),
        "longitude":   context.user_data.get("longitude"),
        "timezone":    tz_name,
        "digest_time": "07:00",
        "onboarded":   True,
        "last_digest_date": None,
    })

    register_farmer_crop(
        user_id, update.effective_user.username or "",
        name, crop, district, village=village,
    )

    confirm_msg = (
        f"✅ *Profile saved!*\n\n"
        f"🧑 Name: *{name}*\n"
        f"🌾 Crop: *{crop.title()}*\n"
        f"📍 Location: *{village}, {district}*\n\n"
        f"_You can change crop or language anytime from the menu._"
    )
    await update.message.reply_text(
        confirm_msg,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=remove_keyboard(),
    )

    crop_key = match_crop(crop)
    if crop_key:
        supported_journey_hint = (
            f"\n\n🌱 *Tip:* Tap *'My Crop Journey'* to start daily crop monitoring "
            f"for your {crop.title()} with tasks, fertilizer reminders & more!"
        )
    else:
        supported_journey_hint = ""

    await update.message.reply_text(
        fmt(WELCOME_COMPLETE, lang, name=name) + supported_journey_hint,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard_v9(user_id, lang),
    )
    await _speak_sarvam(update, fmt(WELCOME_COMPLETE, lang, name=name), lang)
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════
# MAIN MENU ROUTER
# ═══════════════════════════════════════════════════════════════════════

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
            reply_markup=main_menu_keyboard_v9(user_id, lang),
        )
        return STATE_MAIN_MENU

    # ── Crop Journey triggers ─────────────────────────────────────────
    if is_start_journey_request(text):
        await handle_start_journey(update, context, text)
        return STATE_MAIN_MENU
    if is_crop_status_request(text):
        await handle_crop_status(update, context)
        return STATE_MAIN_MENU
    if is_end_journey_request(text):
        await handle_end_journey(update, context)
        return STATE_MAIN_MENU
    if is_timeline_request(text):
        await handle_journey_timeline(update, context)
        return STATE_MAIN_MENU

    if is_alarm_request(text):
        await handle_alarm_set(update, context, text)
        return STATE_MAIN_MENU
    if is_alarm_list_request(text):
        await handle_alarm_list(update, context)
        return STATE_MAIN_MENU

    await update.message.reply_text(
        get_msg(THINKING, lang),
        reply_markup=main_menu_keyboard_v9(user_id, lang),
    )
    return await _smart_reply(
        update, text, lang, lang_cfg, profile, stay_in_voice_query=False
    )


# ═══════════════════════════════════════════════════════════════════════
# VOICE / TEXT QUERY
# ═══════════════════════════════════════════════════════════════════════

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

    if is_start_journey_request(local_text):
        await handle_start_journey(update, context, local_text)
        return STATE_VOICE_QUERY
    if is_crop_status_request(local_text):
        await handle_crop_status(update, context)
        return STATE_VOICE_QUERY
    if is_end_journey_request(local_text):
        await handle_end_journey(update, context)
        return STATE_VOICE_QUERY
    if is_timeline_request(local_text):
        await handle_journey_timeline(update, context)
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
            reply_markup=main_menu_keyboard_v9(user_id, lang),
        )
        return STATE_VOICE_QUERY

    if is_start_journey_request(user_text):
        await handle_start_journey(update, context, user_text)
        return STATE_VOICE_QUERY
    if is_crop_status_request(user_text):
        await handle_crop_status(update, context)
        return STATE_VOICE_QUERY
    if is_end_journey_request(user_text):
        await handle_end_journey(update, context)
        return STATE_VOICE_QUERY
    if is_timeline_request(user_text):
        await handle_journey_timeline(update, context)
        return STATE_VOICE_QUERY

    if is_alarm_request(user_text):
        await handle_alarm_set(update, context, user_text)
        return STATE_VOICE_QUERY
    if is_alarm_list_request(user_text):
        await handle_alarm_list(update, context)
        return STATE_VOICE_QUERY

    await update.message.reply_text(get_msg(THINKING, lang))
    return await _smart_reply(update, user_text, lang, lang_cfg, profile, stay_in_voice_query=True)


# ═══════════════════════════════════════════════════════════════════════
# MANDI PRICES
# ═══════════════════════════════════════════════════════════════════════

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
            reply_markup=main_menu_keyboard_v9(user_id, lang),
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
        reply_markup=main_menu_keyboard_v9(user_id, lang),
    )

    try:
        plain = re.sub(r'[*_🌾📍🏪📊📉📈•]', '', msg)
        local = translate_from_english(plain, lang_cfg["code"]) if lang != "English" else plain
        await _speak_sarvam(update, local[:500], lang, "Mandi prices")
    except Exception as exc:
        log.warning("[mandi TTS] %s", exc)

    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════
# FARMER CONNECT
# ═══════════════════════════════════════════════════════════════════════

async def connect_farmers_handler(update, context, profile, lang) -> int:
    user_id  = update.effective_user.id
    crop     = profile.get("crop")
    village  = profile.get("village", "")
    district = profile.get("district", "")

    if not crop:
        await update.message.reply_text(
            get_msg(COMPLETE_PROFILE_FIRST, lang),
            reply_markup=main_menu_keyboard_v9(user_id, lang),
        )
        return STATE_MAIN_MENU

    await update.message.reply_text(fmt(FINDING_FARMERS, lang, crop=crop))
    farmers = find_farmers_by_crop(crop, exclude_user_id=user_id, village=village, district=district)

    if not farmers:
        await update.message.reply_text(
            fmt(NO_FARMERS_NEARBY, lang, crop=crop),
            reply_markup=main_menu_keyboard_v9(user_id, lang),
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


# ═══════════════════════════════════════════════════════════════════════
# DISEASE DETECTION
# ═══════════════════════════════════════════════════════════════════════

async def handle_disease_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")

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
        caption_text = update.message.caption or ""
        crop         = profile.get("crop", "crop")
        description  = f"{crop} plant disease. {caption_text}{symptom_note}".strip()

        answer = await disease_rag_answer(description=description, profile=profile, image_b64=img_b64)

    except Exception as exc:
        log.error("[disease-image] %s", exc)
        answer = get_msg(IMAGE_ANALYSE_FAIL, lang)
    finally:
        try:
            if os.path.exists(img_path):
                os.remove(img_path)
        except OSError:
            pass

    await _send_reply(update, answer, lang, "Disease Analysis 🔬", main_menu_keyboard_v9(user_id, lang))
    return STATE_MAIN_MENU


async def handle_disease_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text:
        routed = await _route_menu(update, context)
        if routed is not None:
            return routed

    user_id  = update.effective_user.id
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)

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

    answer = await disease_rag_answer(description=description, profile=profile, image_b64=None)
    await _send_reply(update, answer, lang, "Disease Analysis 🔬", main_menu_keyboard_v9(user_id, lang))
    return STATE_MAIN_MENU


async def handle_disease_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
            reply_markup=main_menu_keyboard_v9(user_id, lang),
        )
        return STATE_DISEASE_DETECT

    await update.message.reply_text(get_msg(CHECKING_SYMPTOMS, lang))

    symptoms     = extract_symptoms(text)
    english_desc = translate_to_english(text, lang_cfg["code"]) or text
    symptom_note = f" Symptoms: {', '.join(symptoms)}." if symptoms else ""
    description  = f"{english_desc}{symptom_note}".strip()

    answer = await disease_rag_answer(description=description, profile=profile, image_b64=None)
    await _send_reply(update, answer, lang, "Disease Analysis 🔬", main_menu_keyboard_v9(user_id, lang))
    return STATE_MAIN_MENU


# ═══════════════════════════════════════════════════════════════════════
# CHAT ROOM
# ═══════════════════════════════════════════════════════════════════════

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
            reply_markup=main_menu_keyboard_v9(user_id, lang),
        )
        return STATE_MAIN_MENU

    farmers = find_farmers_by_crop(crop, exclude_user_id=user_id, village=village, district=district)
    if not farmers:
        await update.message.reply_text(
            fmt(NO_FARMERS_NEARBY, lang, crop=crop),
            reply_markup=main_menu_keyboard_v9(user_id, lang),
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
            reply_markup=main_menu_keyboard_v9(partner_id, partner_lang),
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
            reply_markup=main_menu_keyboard_v9(user_id, lang),
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
            reply_markup=main_menu_keyboard_v9(user_id, lang),
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
        reply_markup=main_menu_keyboard_v9(user_id, lang),
    )
    if partner_id:
        partner_lang = (get_profile(partner_id) or {}).get("language", "English")
        try:
            await context.bot.send_message(
                chat_id=partner_id,
                text=fmt(PARTNER_LEFT, partner_lang, name=my_name),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_keyboard_v9(partner_id, partner_lang),
            )
        except Exception:
            queue_offline_notification(
                to_id=partner_id, from_name=my_name,
                preview=f"{my_name} left the chat.",
            )
    return STATE_MAIN_MENU


async def leavechat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _do_leave_chat(update, context, update.effective_user.id)


# ═══════════════════════════════════════════════════════════════════════
# CANCEL / FALLBACK
# ═══════════════════════════════════════════════════════════════════════

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    profile = get_profile(user_id) or {}
    lang    = profile.get("language", "English")
    await update.message.reply_text(
        get_msg(CANCELLED, lang),
        reply_markup=main_menu_keyboard_v9(user_id, lang),
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

        if text:
            if is_start_journey_request(text):
                await handle_start_journey(update, context, text)
                return
            if is_crop_status_request(text):
                await handle_crop_status(update, context)
                return
            if is_end_journey_request(text):
                await handle_end_journey(update, context)
                return
            if is_timeline_request(text):
                await handle_journey_timeline(update, context)
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
                    reply_markup=main_menu_keyboard_v9(user_id, lang),
                )
                await _smart_reply(update, transcribed, lang, lang_cfg, profile)
                return

        if text:
            await update.message.reply_text(
                get_msg(THINKING, lang),
                reply_markup=main_menu_keyboard_v9(user_id, lang),
            )
            await _smart_reply(update, text, lang, lang_cfg, profile)
        return

    await update.message.reply_text("Please type /start to begin using Agrithm 🌾")


# ═══════════════════════════════════════════════════════════════════════
# ALARM FIRE  (PATCH — REPLACEMENT_3 applied)
# ═══════════════════════════════════════════════════════════════════════

# PATCH (REPLACEMENT_3): Alarm ring text extracted to module-level constant.
_ALARM_RING_TEMPLATES = {
    "English":   "🔔🔔🔔 *ALARM — {label}* 🔔🔔🔔\n\n⏰ It is *{time}*\n👋 Good morning, *{name}*!\n\n🌾 Your daily farming tip is coming...",
    "Hindi":     "🔔🔔🔔 *अलार्म — {label}* 🔔🔔🔔\n\n⏰ अभी *{time}* बजे हैं\n👋 सुप्रभात, *{name}*!\n\n🌾 आपकी दैनिक खेती टिप आ रही है...",
    "Telugu":    "🔔🔔🔔 *అలారం — {label}* 🔔🔔🔔\n\n⏰ ఇప్పుడు *{time}* అయింది\n👋 శుభోదయం, *{name}*!\n\n🌾 మీ రోజువారీ వ్యవసాయ చిట్కా వస్తోంది...",
    "Tamil":     "🔔🔔🔔 *அலாரம் — {label}* 🔔🔔🔔\n\n⏰ இப்போது *{time}* மணி\n👋 காலை வணக்கம், *{name}*!\n\n🌾 உங்கள் தினசரி விவசாய குறிப்பு வருகிறது...",
    "Kannada":   "🔔🔔🔔 *ಅಲಾರಂ — {label}* 🔔🔔🔔\n\n⏰ ಈಗ *{time}* ಆಗಿದೆ\n👋 ಶುಭೋದಯ, *{name}*!\n\n🌾 ನಿಮ್ಮ ದೈನಂದಿನ ಕೃಷಿ ಸಲಹೆ ಬರುತ್ತಿದೆ...",
    "Malayalam": "🔔🔔🔔 *അലാറം — {label}* 🔔🔔🔔\n\n⏰ ഇപ്പോൾ *{time}* ആയി\n👋 സുപ്രഭാതം, *{name}*!\n\n🌾 നിങ്ങളുടെ ദൈനദിന കൃഷി ടിപ്പ് വരുന്നു...",
    "Marathi":   "🔔🔔🔔 *अलार्म — {label}* 🔔🔔🔔\n\n⏰ आता *{time}* वाजले\n👋 सुप्रभात, *{name}*!\n\n🌾 तुमची दैनिक शेती टिप येत आहे...",
    "Gujarati":  "🔔🔔🔔 *એલાર્મ — {label}* 🔔🔔🔔\n\n⏰ હવે *{time}* વાગ્યા\n👋 સુપ્રભાત, *{name}*!\n\n🌾 તમારી દૈનિک ખેતી ટીપ આવી રહી છે...",
}


def build_alarm_ring_text(label: str, time_str: str, name: str, lang: str = "English") -> str:
    """Returns the localised alarm ring message for _fire_alarm_with_news()."""
    tmpl = _ALARM_RING_TEMPLATES.get(lang) or _ALARM_RING_TEMPLATES["English"]
    return tmpl.format(label=label, time=time_str, name=name)


async def _fire_alarm_with_news(bot, user_id: int, alarm: dict) -> None:
    profile  = get_profile(user_id) or {}
    lang     = profile.get("language", "English")
    lang_cfg = get_lang_config(lang)
    label    = alarm.get("label", "Alarm")
    time_str = alarm.get("time", "")
    crop     = profile.get("crop", "farming")
    name     = profile.get("name", "Farmer")

    # PATCH (REPLACEMENT_3): use build_alarm_ring_text() helper
    ring_text = build_alarm_ring_text(label=label, time_str=time_str, name=name, lang=lang)
    try:
        await bot.send_message(chat_id=user_id, text=ring_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as exc:
        log.warning("[alarm-fire] Ring failed user=%s: %s", user_id, exc)
        return

    try:
        news_items = get_todays_news(max_items=1)
        if news_items:
            item  = news_items[0]
            title = item["title"]
            body  = item["body"]
            if lang != "English":
                try:
                    title = translate_from_english(title, lang_cfg["code"]) or title
                    body  = translate_from_english(body,  lang_cfg["code"]) or body
                except Exception:
                    pass
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"📰 *Today's Top Farming News:*\n\n"
                    f"{item['category']}\n"
                    f"*{title}*\n\n"
                    f"{body}"
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as exc:
        log.warning("[alarm-fire] News send failed: %s", exc)

    farmer_ctx = build_farmer_context(profile)
    tip_prompt = (
        f"{farmer_ctx}"
        f"Give ONE practical farming tip for today in 2-3 short plain sentences. "
        f"No bullet points. In English only."
    )
    try:
        tip_english = await query_ollama_async(tip_prompt, system=_NEWS_TIP_PROMPT)
    except Exception:
        tip_english = f"Today, check your {crop} plants for any pests or water stress."

    try:
        tip_local = translate_from_english(tip_english, lang_cfg["code"]) if lang != "English" else tip_english
    except Exception:
        tip_local = tip_english

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🌱 *Today's Farming Tip:*\n\n{tip_local}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as exc:
        log.warning("[alarm-fire] Tip failed user=%s: %s", user_id, exc)

    tts_text = f"Good morning {name}. {tip_local}"
    await _speak_sarvam_to_chat(bot, user_id, tts_text, lang, caption="🔔 Alarm & Daily Tip")
    mark_alarm_fired(user_id, alarm["id"])
    log.info("[alarm-fire] ✅ Fired '%s' for user %s", label, user_id)


# ═══════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════

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
            STATE_CHANGE_CROP: [
                MessageHandler(filters.VOICE, handle_change_crop_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_change_crop_input),
            ],
            STATE_CHANGE_LANGUAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_change_language_input),
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

    # ── Global inline callback handlers (outside ConversationHandler) ─
    app.add_handler(CallbackQueryHandler(farmer_view_callback, pattern="^view_farmer_"))

    # ── Crop Journey callback handler ─────────────────────────────────
    app.add_handler(CallbackQueryHandler(journey_callback, pattern=r"^journey_"))

    register_alarm_handlers(app)

    app.add_handler(MessageHandler(
        (filters.TEXT | filters.VOICE) & ~filters.COMMAND,
        global_fallback,
    ))

    return app


# ═══════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════

async def main() -> None:
    app       = build_app()
    scheduler = create_scheduler(app.bot)
    scheduler.start()
    loop = asyncio.get_running_loop()

    def _alarm_job():
        """
        Runs every minute.
        1. Fires standard alarms (news + tip).
        2. Fires journey daily cards for users whose alarm time matches now.
        """
        # ── Standard alarms ──────────────────────────────────────────
        for user_id, alarm in get_all_active_alarms():
            if should_fire_now(alarm):
                future = asyncio.run_coroutine_threadsafe(
                    _fire_alarm_with_news(app.bot, user_id, alarm), loop,
                )
                try:
                    future.result(timeout=30)
                except Exception as exc:
                    log.warning("[alarm-job] user=%s error=%s", user_id, exc)

        # ── Crop Journey daily cards ──────────────────────────────────
        for user_id, journey in get_all_active_journeys():
            alarm_time = journey.get("alarm_time", "06:00")
            tz_name    = journey.get("timezone", "Asia/Kolkata")
            try:
                tz  = pytz.timezone(tz_name)
                now = datetime.now(tz)
                h, m = map(int, alarm_time.split(":"))
                if now.hour == h and now.minute == m:
                    future = asyncio.run_coroutine_threadsafe(
                        _fire_journey_card(
                            bot     = app.bot,
                            user_id = user_id,
                            journey = journey,
                        ),
                        loop,
                    )
                    try:
                        future.result(timeout=60)
                    except Exception as exc:
                        log.warning("[journey-job] user=%s error=%s", user_id, exc)
            except Exception as exc:
                log.warning("[journey-scheduler] user=%s: %s", user_id, exc)

    scheduler.add_job(
        _alarm_job, "interval", minutes=1,
        id="alarm_checker", replace_existing=True,
    )

    log.info("Agrithm v9+Journey+LangPatch bot starting (PID %s)...", os.getpid())
    server_up, model_ok = await check_ollama_health()
    if server_up and model_ok:
        log.info("[Ollama] ✅ %s reachable", OLLAMA_MODEL)
    elif server_up:
        log.warning("[Ollama] ⚠️  Server up but model '%s' not found", OLLAMA_MODEL)
    else:
        log.warning("[Ollama] ⚠️  Server NOT reachable at %s", OLLAMA_URL)

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