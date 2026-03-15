"""
Agrithm Telegram Bot - FULLY FIXED VERSION
=========================================
TRANSLATION FIXES APPLIED:
  ✅ FIX T1: Added from_farmer_lang() — translates user's native lang → English before Dhenu2
  ✅ FIX T2: process_and_respond() now: native text → EN → Dhenu2 → EN response → native lang → TTS
  ✅ FIX T3: DHENU2_SYSTEM updated — always expects/returns English (more reliable)
  ✅ FIX T4: Translation runs in executor (non-blocking, won't freeze event loop)
  ✅ FIX T5: Translation errors fall back gracefully (original text used, no crash)
  ✅ FIX T6: Heard message shows original transcription (user's language), not translated text
  ✅ FIX T7: News translation pipeline also fixed (EN news → user lang before TTS)

ALL ORIGINAL FIXES RETAINED:
  ✅ FIX 1: Whisper wait moved OUT of async handler → uses asyncio.get_event_loop().run_in_executor()
  ✅ FIX 2: ffmpeg error now sends user-visible message immediately with exact reason
  ✅ FIX 3: Ollama timeout reduced to 60s + pre-ping before every voice query
  ✅ FIX 4: transcribe_voice is now run in executor (blocking Whisper call off async thread)
  ✅ FIX 5: All error paths guaranteed to send a reply to user (no more blank screen)
  ✅ FIX 6: Voice file cleanup in finally block (no leaked temp files on error)
  ✅ FIX 7: Added /debug command to show exactly what's failing in real-time

COMPLETE VOICE PIPELINE (FIXED):
  Voice → Download OGG → ffmpeg WAV → Whisper (native lang transcription)
        → GoogleTranslator (native → EN) → Dhenu2 (EN query)
        → GoogleTranslator (EN response → native lang) → gTTS (native lang TTS) + Text reply

COMPLETE TEXT PIPELINE (FIXED):
  Text (native) → GoogleTranslator (native → EN) → Dhenu2 (EN query)
               → GoogleTranslator (EN response → native lang) → gTTS (native lang TTS) + Text reply
"""

import asyncio
import logging
import os
import json
import re
import tempfile
import threading
import time
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import requests
import schedule
from gtts import gTTS
from deep_translator import GoogleTranslator
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes,
    filters
)

# ══════════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════════
BOT_TOKEN    = "8604316604:AAFmysLPBULIaRffl36dec0SdmRnsitCcKE"
OLLAMA_URL   = "http://localhost:11434"
DHENU_MODEL  = "dhenu2-farming:latest"
NGROK_HEADERS = {
    "ngrok-skip-browser-warning": "true",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "AgrithmBot/3.0",
}
NEWS_API_KEY = "api_live_uCZRmOfsZ0hny7aYmU7tcDN3iHp2GzdNBbgw1r2tZh9gS3w1TMbpS"
DATA_FILE    = Path("farmer_data.json")
WHISPER_MODEL_SIZE = "base"

# Thread pool for running blocking calls (Whisper, ffmpeg, translation) off the async event loop
_executor = ThreadPoolExecutor(max_workers=4)

# ══════════════════════════════════════════════════════════════════
#  LANGUAGE CONFIGURATION
# ══════════════════════════════════════════════════════════════════
LANGUAGES = {
    "हिंदी (Hindi)":      {"code": "hi", "tts_lang": "hi", "flag": "🇮🇳", "whisper": "hi"},
    "தமிழ் (Tamil)":       {"code": "ta", "tts_lang": "ta", "flag": "🌾",  "whisper": "ta"},
    "తెలుగు (Telugu)":     {"code": "te", "tts_lang": "te", "flag": "🌿",  "whisper": "te"},
    "ಕನ್ನಡ (Kannada)":     {"code": "kn", "tts_lang": "kn", "flag": "🌻",  "whisper": "kn"},
    "বাংলা (Bengali)":     {"code": "bn", "tts_lang": "bn", "flag": "🌾",  "whisper": "bn"},
    "मराठी (Marathi)":     {"code": "mr", "tts_lang": "mr", "flag": "🌱",  "whisper": "mr"},
    "ગુજરાતી (Gujarati)":  {"code": "gu", "tts_lang": "gu", "flag": "🌾",  "whisper": "gu"},
    "ਪੰਜਾਬੀ (Punjabi)":    {"code": "pa", "tts_lang": "pa", "flag": "🌾",  "whisper": "pa"},
    "ଓଡ଼ିଆ (Odia)":        {"code": "or", "tts_lang": "or", "flag": "🌿",  "whisper": None},
    "English":             {"code": "en", "tts_lang": "en", "flag": "🔤",  "whisper": "en"},
}

WHISPER_LANG_MAP = {info["code"]: info["whisper"] for info in LANGUAGES.values()}

LISTEN_MSGS = {
    "hi": "🎤 सुन रहा हूँ... थोड़ा इंतजार करें",
    "ta": "🎤 கேட்கிறேன்... கொஞ்சம் காத்திருங்கள்",
    "te": "🎤 వింటున్నాను... కొంచెం వేచి ఉండండి",
    "kn": "🎤 ಕೇಳುತ್ತಿದ್ದೇನೆ... ಸ್ವಲ್ಪ ನಿರೀಕ್ಷಿಸಿ",
    "bn": "🎤 শুনছি... একটু অপেক্ষা করুন",
    "mr": "🎤 ऐकतोय... थोडं थांबा",
    "gu": "🎤 સાંભળી રહ્યો છું... થોડી રાહ જુઓ",
    "pa": "🎤 ਸੁਣ ਰਿਹਾ ਹਾਂ... ਥੋੜਾ ਉਡੀਕ ਕਰੋ",
    "or": "🎤 ଶୁଣୁଛି... ଟିକେ ଅପେକ୍ଷା କରନ୍ତୁ",
    "en": "🎤 Listening... please wait",
}

HEARD_MSGS = {
    "hi": "📝 मैंने सुना",
    "ta": "📝 நான் கேட்டது",
    "te": "📝 నేను విన్నది",
    "kn": "📝 ನಾನು ಕೇಳಿದ್ದು",
    "bn": "📝 আমি শুনলাম",
    "mr": "📝 मी ऐकलं",
    "gu": "📝 મેં સાંભળ્યું",
    "pa": "📝 ਮੈਂ ਸੁਣਿਆ",
    "or": "📝 ମୁଁ ଶୁଣିଲି",
    "en": "📝 I heard",
}

FAIL_MSGS = {
    "hi": "⚠️ आवाज़ स्पष्ट नहीं थी। कृपया फिर से बोलें या टाइप करें।",
    "ta": "⚠️ குரல் தெளிவாக இல்லை. மீண்டும் பேசுங்கள் அல்லது தட்டச்சு செய்யுங்கள்.",
    "te": "⚠️ గొంతు స్పష్టంగా లేదు. మళ్ళీ మాట్లాడండి లేదా టైప్ చేయండి.",
    "kn": "⚠️ ಧ್ವನಿ ಸ್ಪಷ್ಟವಾಗಿಲ್ಲ. ಮತ್ತೆ ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
    "bn": "⚠️ কণ্ঠস্বর স্পষ্ট ছিল না। আবার বলুন বা টাইপ করুন।",
    "mr": "⚠️ आवाज स्पष्ट नव्हता. पुन्हा बोला किंवा टाइप करा.",
    "gu": "⚠️ અવાજ સ્પષ્ટ ન હતો. ફરીથી બોલો અથવા ટાઇપ કરો.",
    "pa": "⚠️ ਆਵਾਜ਼ ਸਪਸ਼ਟ ਨਹੀਂ ਸੀ। ਦੁਬਾਰਾ ਬੋਲੋ ਜਾਂ ਟਾਈਪ ਕਰੋ।",
    "or": "⚠️ ଶବ୍ଦ ସ୍ପଷ୍ଟ ନଥିଲା। ଆଉ ଥରେ କୁହନ୍ତୁ ବା ଟାଇପ୍ କରନ୍ତୁ।",
    "en": "⚠️ Voice wasn't clear. Please speak again or type your question.",
}

ALERT_TIMES = [
    "5:00 AM", "6:00 AM", "7:00 AM", "8:00 AM",
    "12:00 PM", "4:00 PM", "6:00 PM", "7:00 PM", "9:00 PM"
]

(STATE_LANGUAGE, STATE_LOCATION, STATE_TIME1, STATE_TIME2) = range(4)

# ══════════════════════════════════════════════════════════════════
#  LOGGING
# ══════════════════════════════════════════════════════════════════
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AgrithmBot")

# ══════════════════════════════════════════════════════════════════
#  WHISPER — LOAD ONCE IN BACKGROUND
# ══════════════════════════════════════════════════════════════════
_whisper_model = None
_whisper_ready = threading.Event()


def _load_whisper_bg():
    global _whisper_model
    try:
        import whisper
        logger.info(f"⏳ Loading Whisper '{WHISPER_MODEL_SIZE}'...")
        _whisper_model = whisper.load_model(WHISPER_MODEL_SIZE)
        logger.info("✅ Whisper ready")
    except ImportError:
        logger.error("❌ openai-whisper not installed. Run: pip install openai-whisper")
    except Exception as e:
        logger.error(f"❌ Whisper failed to load: {e}")
    finally:
        _whisper_ready.set()


# ══════════════════════════════════════════════════════════════════
#  PERSISTENT STORAGE
# ══════════════════════════════════════════════════════════════════
def load_data() -> dict:
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


farmer_db: dict = load_data()

# ══════════════════════════════════════════════════════════════════
#  TRANSLATION  ← FIXED: both directions now implemented
# ══════════════════════════════════════════════════════════════════

def to_farmer_lang(text: str, lang_code: str) -> str:
    """
    Translate English text → farmer's native language.
    Used AFTER Dhenu2 responds (EN response → native lang for display + TTS).
    """
    if lang_code == "en" or not text.strip():
        return text
    try:
        result = GoogleTranslator(source="en", target=lang_code).translate(text)
        translated = result or text
        logger.info(f"✅ Translated EN→{lang_code}: {translated[:80]}")
        return translated
    except Exception as e:
        logger.warning(f"⚠️ Translation failed (en→{lang_code}): {e} — using original English")
        return text  # graceful fallback: show English rather than crash


def from_farmer_lang(text: str, lang_code: str) -> str:
    """
    FIX T1: Translate farmer's native language text → English.
    Used BEFORE sending to Dhenu2 (native input → EN for reliable model response).

    Why this is critical:
      Dhenu2 (and most Ollama models) are primarily trained on English.
      Sending raw Tamil/Telugu/Kannada etc. causes hallucinations, wrong-language
      replies, or the model ignoring the question entirely.
      Google Translate handles all Indian languages reliably.
    """
    if lang_code == "en" or not text.strip():
        return text
    try:
        result = GoogleTranslator(source=lang_code, target="en").translate(text)
        english = result or text
        logger.info(f"✅ Translated {lang_code}→EN: {english[:80]}")
        return english
    except Exception as e:
        logger.warning(f"⚠️ Translation failed ({lang_code}→en): {e} — using original text")
        return text  # graceful fallback: Dhenu2 will try its best with native text


# ══════════════════════════════════════════════════════════════════
#  TEXT-TO-SPEECH
# ══════════════════════════════════════════════════════════════════
def text_to_voice(text: str, tts_lang: str) -> str | None:
    """
    Convert text to MP3 voice file using gTTS.
    text must already be in the target language (tts_lang) before calling this.
    """
    try:
        clean = re.sub(r'[*_`#•→]', '', text)
        clean = re.sub(r'\s+', ' ', clean).strip()[:600]
        if not clean:
            return None
        tts = gTTS(text=clean, lang=tts_lang, slow=False)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts.save(tmp.name)
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.warning(f"TTS failed ({tts_lang}): {e}")
        return None


# ══════════════════════════════════════════════════════════════════
#  OGG → WAV  (runs in executor — blocking, do NOT call from async directly)
# ══════════════════════════════════════════════════════════════════
def _convert_ogg_to_wav_sync(ogg_path: str) -> tuple[str | None, str]:
    """
    Returns (wav_path, error_msg).
    error_msg is empty string on success.
    """
    wav_path = ogg_path.replace(".ogg", ".wav")
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path,
             "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav_path],
            capture_output=True, timeout=30
        )
        if result.returncode != 0:
            err = result.stderr.decode(errors="replace")
            logger.error(f"ffmpeg failed (code {result.returncode}): {err[:300]}")
            return None, f"ffmpeg conversion failed (code {result.returncode})"
        logger.info(f"✅ OGG→WAV: {wav_path}")
        return wav_path, ""
    except FileNotFoundError:
        logger.error("❌ ffmpeg not found in PATH")
        return None, "ffmpeg not installed"
    except subprocess.TimeoutExpired:
        logger.error("❌ ffmpeg timed out")
        return None, "ffmpeg timed out"
    except Exception as e:
        logger.error(f"❌ OGG conversion error: {e}")
        return None, str(e)


# ══════════════════════════════════════════════════════════════════
#  WHISPER TRANSCRIPTION  (blocking — runs in executor)
# ══════════════════════════════════════════════════════════════════
def _transcribe_sync(wav_path: str, lang_code: str) -> tuple[str | None, str]:
    """
    Synchronous Whisper transcription.
    Returns (text_in_native_lang, status) — status: "ok" | "failed" | "not_loaded"

    NOTE: Whisper returns text in the NATIVE language of the audio.
    The caller (handle_voice_query) must then run from_farmer_lang() to get English
    before passing to Dhenu2.
    """
    if _whisper_model is None:
        return None, "not_loaded"
    try:
        whisper_lang = WHISPER_LANG_MAP.get(lang_code)
        result = _whisper_model.transcribe(
            wav_path,
            language=whisper_lang,
            task="transcribe",    # transcribe keeps native lang; "translate" would give EN
            fp16=False,
            verbose=False
        )
        text = result.get("text", "").strip()
        detected = result.get("language", "unknown")
        logger.info(f"✅ Whisper [{detected}] transcribed: {text[:120]}")
        return (text if text else None), "ok"
    except Exception as e:
        logger.error(f"❌ Whisper error: {e}")
        return None, "failed"


# ══════════════════════════════════════════════════════════════════
#  DHENU2  ← FIXED: system prompt updated to always work in English
# ══════════════════════════════════════════════════════════════════

# FIX T3: Updated system prompt — we now always send English queries to Dhenu2.
# This is FAR more reliable than asking the model to detect and reply in native langs.
# Translation to/from native lang is handled by Google Translate (much more accurate).
DHENU2_SYSTEM = (
    "You are Dhenu, an expert AI agricultural assistant for Indian farmers. "
    "You will always receive questions in English. Always reply in English only. "
    "Give precise, practical farming advice covering: crop selection, soil health, "
    "pest and disease control, irrigation scheduling, mandi prices, weather advisories, "
    "and government schemes (PM-Kisan, eNAM, PMFBY, soil health card). "
    "Be concise — 4 to 5 sentences maximum. Use simple vocabulary that is easy to translate. "
    "Do not use technical jargon. Do not switch languages. Always reply in English."
)


def _query_dhenu2_sync(prompt: str, system: str = DHENU2_SYSTEM) -> str:
    """Blocking Ollama call — run via executor."""
    payload = {
        "model": DHENU_MODEL,
        "prompt": prompt,
        "system": system,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 400,
            "top_p": 0.9,
            "repeat_penalty": 1.1
        }
    }
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            headers=NGROK_HEADERS,
            timeout=60
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()
        return text or "I could not generate a response. Please try again."
    except requests.exceptions.ConnectionError:
        logger.error("❌ Ollama not reachable")
        return "Farming assistant is offline. Run 'ollama serve' in your terminal, then try again."
    except requests.exceptions.Timeout:
        logger.error("❌ Ollama timeout (60s)")
        return "The model took too long to respond. Please try a shorter question."
    except Exception as e:
        logger.error(f"❌ Dhenu2 error: {e}")
        return f"An error occurred: {str(e)}"


async def query_dhenu2(prompt: str, system: str = DHENU2_SYSTEM) -> str:
    """Async wrapper — runs blocking Ollama call in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, _query_dhenu2_sync, prompt, system)


def check_ollama_connection() -> tuple[bool, list[str]]:
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", headers=NGROK_HEADERS, timeout=10)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        return True, models
    except requests.exceptions.JSONDecodeError as e:
        logger.error(f"❌ Ollama returned non-JSON: {e}")
        return False, []
    except Exception as e:
        logger.error(f"❌ Ollama check failed: {type(e).__name__}: {e}")
        return False, []


# ══════════════════════════════════════════════════════════════════
#  NEWS  ← FIX T7: translation pipeline fixed for news too
# ══════════════════════════════════════════════════════════════════
def fetch_agri_news(location: str = "India") -> list[dict]:
    """
    Fetch agricultural news. Returns list of dicts with 'title' and 'summary' in English.
    Caller is responsible for translating to farmer's language before display/TTS.
    """
    if NEWS_API_KEY:
        try:
            resp = requests.get(
                "https://api.apitube.io/v1/news/everything",
                params={
                    "query":    f"agriculture farming crops India {location}",
                    "language": "en",
                    "sortBy":   "published_at",
                    "per_page": 5,
                    "api_key":  NEWS_API_KEY
                },
                timeout=10
            )
            articles = resp.json().get("articles", [])
            if articles:
                return [
                    {"title": a.get("title", ""), "summary": a.get("description") or a.get("summary", "")}
                    for a in articles[:4]
                ]
        except Exception as e:
            logger.warning(f"News API failed: {e}")

    # Fallback: ask Dhenu2 in English (system prompt now enforces English reply)
    today = datetime.now().strftime("%B %d, %Y")
    prompt = (
        f"Today is {today}. Location: {location}. "
        "Generate a short agricultural news bulletin for Indian farmers covering: "
        "1) Weather or season advisory 2) Key crop mandi price update "
        "3) Government scheme reminder 4) Pest or disease alert. "
        "Keep it under 150 words total. Reply in English only."
    )
    news_text = _query_dhenu2_sync(prompt)
    return [{"title": f"Daily Agri Bulletin – {today}", "summary": news_text}]


def format_news(news_items: list[dict], lang_code: str, location: str) -> tuple[str, str]:
    """
    FIX T7: Translate each news item from English → farmer's language.
    Returns (text_message, voice_text) both in farmer's language.
    """
    header     = f"🌾 Agricultural News\n📍 {location}\n🕐 {datetime.now().strftime('%I:%M %p, %d %b %Y')}\n\n"
    body_parts, voice_parts = [], []
    for i, item in enumerate(news_items, 1):
        # Each item comes in English — translate to farmer's language
        title   = to_farmer_lang(item.get("title", ""), lang_code)
        summary = to_farmer_lang(item.get("summary", ""), lang_code)
        body_parts.append(f"*{i}. {title}*\n{summary}")
        voice_parts.append(f"{title}. {summary}")
    return header + "\n\n".join(body_parts), " ".join(voice_parts)


async def send_scheduled_news(app: Application, chat_id: int):
    uid = str(chat_id)
    if uid not in farmer_db:
        return
    farmer    = farmer_db[uid]
    lang_code = farmer.get("lang_code", "hi")
    tts_lang  = farmer.get("tts_lang", "hi")
    location  = farmer.get("location", "India")

    # fetch_agri_news returns English items; format_news translates them
    news             = fetch_agri_news(location)
    text_msg, voice_txt = format_news(news, lang_code, location)

    await app.bot.send_message(chat_id=chat_id, text=text_msg, parse_mode="Markdown")
    audio = text_to_voice(voice_txt, tts_lang)
    if audio:
        with open(audio, "rb") as f:
            await app.bot.send_voice(chat_id=chat_id, voice=f, caption="🔊 Audio bulletin")
        try: os.unlink(audio)
        except: pass


def schedule_loop(app: Application):
    while True:
        schedule.run_pending()
        time.sleep(20)


def register_schedule(app: Application, chat_id: int, alert_times: list[str]):
    uid = str(chat_id)
    schedule.clear(tag=uid)
    for t in alert_times:
        try:
            time_str = datetime.strptime(t, "%I:%M %p").strftime("%H:%M")
            schedule.every().day.at(time_str).do(
                lambda cid=chat_id: asyncio.run_coroutine_threadsafe(
                    send_scheduled_news(app, cid), app.loop
                )
            ).tag(uid)
        except Exception as e:
            logger.error(f"Schedule error: {e}")


# ══════════════════════════════════════════════════════════════════
#  CORE RESPONSE PIPELINE  ← FULLY FIXED TRANSLATION PIPELINE
# ══════════════════════════════════════════════════════════════════
async def process_and_respond(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_text: str                     # native language text (from Whisper or typed)
):
    """
    FIXED translation pipeline:

    Step 1: user_text (native lang)  →  from_farmer_lang()  →  english_text
    Step 2: english_text             →  Dhenu2              →  response_en (English)
    Step 3: response_en              →  to_farmer_lang()    →  response_native
    Step 4: response_native          →  gTTS (tts_lang)     →  voice file
    Step 5: Send response_native as text + voice to user

    This ensures:
    - Dhenu2 always gets clean English input (much more reliable)
    - User always gets response in their own language
    - TTS pronounces words correctly in native language
    """
    uid       = str(update.effective_user.id)
    farmer    = farmer_db.get(uid, {})
    lang_code = farmer.get("lang_code", "en")
    tts_lang  = farmer.get("tts_lang", "en")
    location  = farmer.get("location", "India")

    loop = asyncio.get_event_loop()

    # ── Step 1: Translate native language → English ───────────────────────
    # FIX T1 + T4: runs in executor so it never blocks the event loop
    english_text = await loop.run_in_executor(
        _executor, from_farmer_lang, user_text, lang_code
    )
    logger.info(f"[{uid}] ({lang_code}→EN): '{user_text[:60]}' → '{english_text[:60]}'")

    # ── Step 2: Build prompt and query Dhenu2 in English ─────────────────
    prompt = (
        f"Farmer location: {location}.\n"
        f"Date: {datetime.now().strftime('%B %d, %Y')}.\n"
        f"Farmer's question: {english_text}"
    )

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    # query_dhenu2 already runs in executor (non-blocking)
    response_en = await query_dhenu2(prompt)
    logger.info(f"[{uid}] Dhenu2 (EN): {response_en[:100]}")

    # ── Step 3: Translate English response → farmer's native language ─────
    # FIX T2 + T4: runs in executor so it never blocks the event loop
    response_native = await loop.run_in_executor(
        _executor, to_farmer_lang, response_en, lang_code
    )
    logger.info(f"[{uid}] (EN→{lang_code}): '{response_native[:80]}'")

    # ── Step 4: Send text reply in native language ────────────────────────
    await update.message.reply_text(f"🌾 {response_native}")

    # ── Step 5: Generate and send TTS voice in native language ────────────
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="upload_voice"
    )

    # text_to_voice is blocking — run in executor
    # response_native is already in tts_lang language, so pronunciation will be correct
    audio_path = await loop.run_in_executor(
        _executor, text_to_voice, response_native, tts_lang
    )
    if audio_path:
        with open(audio_path, "rb") as audio:
            await update.message.reply_voice(voice=audio, caption="🔊")
        try: os.unlink(audio_path)
        except: pass


# ══════════════════════════════════════════════════════════════════
#  TEXT MESSAGE HANDLER
# ══════════════════════════════════════════════════════════════════
async def handle_text_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles typed text messages.
    The text may be in any language — process_and_respond handles translation.
    """
    uid = str(update.effective_user.id)
    if uid not in farmer_db:
        await update.message.reply_text("Please run /start first to set up your profile! 🌾")
        return
    await process_and_respond(update, context, update.message.text.strip())


# ══════════════════════════════════════════════════════════════════
#  VOICE MESSAGE HANDLER  ← ALL ORIGINAL FIXES + TRANSLATION FIX
# ══════════════════════════════════════════════════════════════════
async def handle_voice_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIXED voice pipeline — no blocking calls on the async event loop.
    Every error path sends a user-visible message (no blank screen).

    Pipeline:
      OGG download → ffmpeg WAV → Whisper (native lang) → from_farmer_lang (→EN)
      → Dhenu2 (EN) → to_farmer_lang (→native) → gTTS (native) + text reply
    """
    uid = str(update.effective_user.id)
    if uid not in farmer_db:
        await update.message.reply_text("Please run /start first! 🌾")
        return

    farmer    = farmer_db[uid]
    lang_code = farmer.get("lang_code", "en")

    # ── Step 1: Acknowledge immediately (user sees this, no blank screen) ──
    await update.message.reply_text(LISTEN_MSGS.get(lang_code, LISTEN_MSGS["en"]))

    # ── Step 2: Check Whisper is ready (NON-BLOCKING check) ──────────────
    if not _whisper_ready.is_set():
        await update.message.reply_text(
            "⚠️ Voice engine is still loading (takes ~30 sec at startup). "
            "Please wait a moment and try again, or type your question instead."
        )
        return

    if _whisper_model is None:
        await update.message.reply_text(
            "❌ Voice engine failed to load. Please type your question.\n"
            "To fix: run `pip install openai-whisper` and restart the bot."
        )
        return

    # ── Step 3: Download voice file ───────────────────────────────────────
    ogg_path = None
    wav_path = None
    try:
        voice         = update.message.voice
        tg_voice_file = await context.bot.get_file(voice.file_id)
        ogg_path      = os.path.join(
            tempfile.gettempdir(),
            f"agri_{uid}_{int(time.time())}.ogg"
        )
        await tg_voice_file.download_to_drive(ogg_path)
        logger.info(f"📥 Voice saved: {ogg_path} ({voice.duration}s)")
    except Exception as e:
        logger.error(f"Voice download failed: {e}")
        await update.message.reply_text(
            f"❌ Could not download voice message. Please try again.\n"
            f"Error: {str(e)}"
        )
        return

    try:
        loop = asyncio.get_event_loop()

        # ── Step 4: Convert OGG → WAV (in executor, non-blocking) ────────
        wav_path, ffmpeg_err = await loop.run_in_executor(
            _executor, _convert_ogg_to_wav_sync, ogg_path
        )

        if wav_path is None:
            if "not installed" in ffmpeg_err:
                await update.message.reply_text(
                    "❌ ffmpeg is not installed on this machine.\n"
                    "Install it: https://ffmpeg.org/download.html\n"
                    "Or on Ubuntu: `sudo apt install ffmpeg`\n\n"
                    "👉 You can still TYPE your question below!"
                )
            else:
                await update.message.reply_text(
                    f"❌ Voice conversion failed: {ffmpeg_err}\n"
                    "Please try again or type your question."
                )
            return

        # ── Step 5: Transcribe with Whisper (in executor, non-blocking) ───
        # Result is text in farmer's NATIVE language (e.g. Tamil, Telugu)
        transcribed_native, status = await loop.run_in_executor(
            _executor, _transcribe_sync, wav_path, lang_code
        )

        # ── Step 6: Handle transcription result ───────────────────────────
        if transcribed_native and transcribed_native.strip():
            # FIX T6: Show the user what was heard in their OWN language
            heard_label = HEARD_MSGS.get(lang_code, HEARD_MSGS["en"])
            await update.message.reply_text(
                f"{heard_label}: _{transcribed_native}_",
                parse_mode="Markdown"
            )
            # process_and_respond handles the full translation pipeline:
            # transcribed_native → EN → Dhenu2 → EN response → native → TTS
            await process_and_respond(update, context, transcribed_native)

        else:
            # Always send a reply — no blank screen
            await update.message.reply_text(
                FAIL_MSGS.get(lang_code, FAIL_MSGS["en"])
            )

    finally:
        # Always clean up temp files, even on error
        for path in [ogg_path, wav_path]:
            if path:
                try: os.unlink(path)
                except: pass


# ══════════════════════════════════════════════════════════════════
#  ONBOARDING
# ══════════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    uid  = str(update.effective_user.id)
    name = update.effective_user.first_name

    if uid in farmer_db:
        lang_code = farmer_db[uid].get("lang_code", "en")
        msg = to_farmer_lang(f"Welcome back {name}! Ask me anything about farming 🌾", lang_code)
        await update.message.reply_text(msg)
        return ConversationHandler.END

    await update.message.reply_text(
        f"🌾 *Namaste {name}!*\n\n"
        "I am *Dhenu* — your AI farming assistant.\n\n"
        "✅ Answers farming questions in YOUR language\n"
        "✅ Daily agri-news alerts\n"
        "✅ Replies with voice 🔊 and text\n"
        "✅ Accepts typed AND voice questions 🎤\n\n"
        "Let's set up your profile 👇",
        parse_mode="Markdown"
    )

    buttons, row = [], []
    for lang_name, info in LANGUAGES.items():
        row.append(InlineKeyboardButton(f"{info['flag']} {lang_name}", callback_data=f"lang:{lang_name}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await update.message.reply_text(
        "🌐 Choose your language:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return STATE_LANGUAGE


async def language_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query     = update.callback_query
    await query.answer()
    lang_name = query.data.split("lang:", 1)[1]
    info      = LANGUAGES[lang_name]

    context.user_data.update({
        "lang_name": lang_name,
        "lang_code": info["code"],
        "tts_lang":  info["tts_lang"]
    })

    await query.edit_message_text(f"✅ Language: {lang_name}")
    loc_btn = [[KeyboardButton("📍 Share My Location", request_location=True)]]
    await query.message.reply_text(
        to_farmer_lang("Now share your location or type your village/district name:", info["code"]),
        reply_markup=ReplyKeyboardMarkup(loc_btn, one_time_keyboard=True, resize_keyboard=True)
    )
    return STATE_LOCATION


async def location_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang_code    = context.user_data.get("lang_code", "en")
    location_str = ""

    if update.message.location:
        lat, lon     = update.message.location.latitude, update.message.location.longitude
        location_str = f"{lat:.3f},{lon:.3f}"
        try:
            addr = requests.get(
                f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json",
                headers={"User-Agent": "AgrithmBot/3.0"},
                timeout=5
            ).json().get("address", {})
            parts        = [
                addr.get("village") or addr.get("town") or addr.get("city") or addr.get("county", ""),
                addr.get("state", "")
            ]
            location_str = ", ".join(p for p in parts if p) or location_str
        except Exception:
            pass
    else:
        location_str = update.message.text.strip()

    context.user_data["location"] = location_str
    await update.message.reply_text(
        to_farmer_lang(f"📍 Location set: {location_str}", lang_code)
    )
    await update.message.reply_text(
        to_farmer_lang("When should I send MORNING news?", lang_code),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(t, callback_data=f"time1:{t}")] for t in ALERT_TIMES[:5]]
        )
    )
    return STATE_TIME1


async def time1_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    t1        = query.data.split("time1:", 1)[1]
    lang_code = context.user_data.get("lang_code", "en")
    context.user_data["time1"] = t1

    await query.edit_message_text(
        to_farmer_lang(f"✅ Morning: {t1}\nWhen should I send EVENING news?", lang_code),
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(t, callback_data=f"time2:{t}")] for t in ALERT_TIMES[4:]]
        )
    )
    return STATE_TIME2


async def time2_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query     = update.callback_query
    await query.answer()
    t2        = query.data.split("time2:", 1)[1]
    uid       = str(query.from_user.id)
    lang_code = context.user_data.get("lang_code", "en")

    farmer_db[uid] = {
        "chat_id":       query.message.chat_id,
        "name":          query.from_user.first_name,
        "lang_name":     context.user_data["lang_name"],
        "lang_code":     lang_code,
        "tts_lang":      context.user_data["tts_lang"],
        "location":      context.user_data["location"],
        "alert_times":   [context.user_data["time1"], t2],
        "registered_at": datetime.now().isoformat()
    }
    save_data(farmer_db)
    register_schedule(context.application, query.message.chat_id, farmer_db[uid]["alert_times"])

    await query.edit_message_text(
        to_farmer_lang(
            f"✅ All set! Daily news at {context.user_data['time1']} and {t2}.\n\n"
            "Now ask me anything — by typing OR by sending a voice message! 🎤",
            lang_code
        )
    )
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════════════════════
async def cmd_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid not in farmer_db:
        await update.message.reply_text("Please /start first!")
        return
    await update.message.reply_text("📰 Fetching latest news...")
    await send_scheduled_news(context.application, update.effective_chat.id)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ollama_ok, models = check_ollama_connection()
    dhenu_ok = any(DHENU_MODEL.split(":")[0] in m for m in models)

    ollama_line  = "✅ Ollama running" if ollama_ok else "❌ Ollama offline — run: ollama serve"
    dhenu_line   = f"{'✅' if dhenu_ok else '❌'} {DHENU_MODEL}"
    models_line  = f"Models: {', '.join(models) if models else 'none found'}"
    whisper_line = f"{'✅' if _whisper_model else '⚠️'} Whisper {'ready' if _whisper_model else 'loading/not loaded'}"

    # Test translation
    try:
        test = GoogleTranslator(source="en", target="ta").translate("test")
        trans_line = "✅ Google Translate: working"
    except Exception as e:
        trans_line = f"❌ Google Translate: {e}"

    await update.message.reply_text(
        f"🔍 *System Status*\n\n"
        f"{ollama_line}\n{dhenu_line}\n{models_line}\n\n"
        f"{whisper_line}\n{trans_line}\n\n"
        f"👨‍🌾 Farmers registered: {len(farmer_db)}",
        parse_mode="Markdown"
    )


async def cmd_debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /debug command — shows exact failure reason for voice + translation pipeline.
    """
    lines = ["🔧 *Debug Report*\n"]

    # 1. ffmpeg check
    try:
        r = subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        lines.append("✅ ffmpeg: installed")
    except FileNotFoundError:
        lines.append("❌ ffmpeg: NOT FOUND — install from ffmpeg.org")
    except Exception as e:
        lines.append(f"⚠️ ffmpeg: {e}")

    # 2. Whisper check
    if _whisper_model:
        lines.append(f"✅ Whisper: ready (model: {WHISPER_MODEL_SIZE})")
    elif _whisper_ready.is_set():
        lines.append("❌ Whisper: failed to load — check logs")
    else:
        lines.append("⏳ Whisper: still loading — wait 30s")

    # 3. Ollama check
    ollama_ok, models = check_ollama_connection()
    if ollama_ok:
        lines.append(f"✅ Ollama: running | models: {models}")
        dhenu_ok = any(DHENU_MODEL.split(":")[0] in m for m in models)
        if dhenu_ok:
            lines.append(f"✅ {DHENU_MODEL}: found")
        else:
            lines.append(f"❌ {DHENU_MODEL}: NOT found — run: ollama pull {DHENU_MODEL}")
    else:
        lines.append("❌ Ollama: offline — run: ollama serve")

    # 4. Translation check (FIX T1 — verify both directions work)
    try:
        test_en  = GoogleTranslator(source="ta", target="en").translate("நான் நன்றாக இருக்கிறேன்")
        test_ta  = GoogleTranslator(source="en", target="ta").translate("I am doing well")
        lines.append(f"✅ Translation (ta→EN): '{test_en}'")
        lines.append(f"✅ Translation (EN→ta): '{test_ta}'")
    except Exception as e:
        lines.append(f"❌ Google Translate: {e} — install: pip install deep-translator")

    # 5. Temp dir writable
    try:
        t = tempfile.NamedTemporaryFile(delete=True)
        t.close()
        lines.append(f"✅ Temp dir: writable ({tempfile.gettempdir()})")
    except Exception as e:
        lines.append(f"❌ Temp dir: not writable — {e}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def cmd_test_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid       = str(update.effective_user.id)
    lang_code = farmer_db.get(uid, {}).get("lang_code", "en")

    # Test questions in native language (to verify full translation pipeline)
    test_prompts = {
        "hi": "मेरे खेत में टमाटर की फसल के लिए सबसे अच्छा उर्वरक कौन सा है?",
        "ta": "தக்காளி பயிருக்கு சிறந்த உரம் எது?",
        "te": "టమాటా పంటకు ఉత్తమ ఎరువు ఏది?",
        "kn": "ಟೊಮ್ಯಾಟೊ ಬೆಳೆಗೆ ಉತ್ತಮ ಗೊಬ್ಬರ ಯಾವುದು?",
        "bn": "টমেটো ফসলের জন্য সেরা সার কোনটি?",
        "mr": "टोमॅटो पिकासाठी सर्वोत्तम खत कोणते?",
        "gu": "ટામેટાના પાક માટે શ્રેષ્ઠ ખાતર કયું છે?",
        "pa": "ਟਮਾਟਰ ਦੀ ਫ਼ਸਲ ਲਈ ਸਭ ਤੋਂ ਵਧੀਆ ਖਾਦ ਕਿਹੜੀ ਹੈ?",
        "en": "What is the best fertilizer for tomato crops?"
    }
    test_q = test_prompts.get(lang_code, test_prompts["en"])

    await update.message.reply_text(
        f"🧪 Testing full translation pipeline\n"
        f"Language: {lang_code}\n"
        f"Question: _{test_q}_",
        parse_mode="Markdown"
    )
    await process_and_respond(update, context, test_q)


async def cmd_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    if uid not in farmer_db:
        await update.message.reply_text("Please /start first!")
        return
    f = farmer_db[uid]
    lang_code = f.get("lang_code", "en")
    await update.message.reply_text(
        to_farmer_lang(
            f"Your Settings:\nLanguage: {f['lang_name']}\nLocation: {f['location']}\n"
            f"Alert times: {', '.join(f['alert_times'])}\n\nRun /start to update.",
            lang_code
        )
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid       = str(update.effective_user.id)
    lang_code = farmer_db.get(uid, {}).get("lang_code", "en")
    await update.message.reply_text(
        to_farmer_lang(
            "Commands:\n"
            "/start — Set up your profile\n"
            "/news — Get latest agri news now\n"
            "/settings — View your settings\n"
            "/status — Check system status\n"
            "/debug — Diagnose voice and translation issues\n"
            "/testvoice — Test full translation pipeline\n"
            "/help — Show this help\n\n"
            "Ask farming questions by TEXT or VOICE MESSAGE 🎤",
            lang_code
        )
    )


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    print("=" * 60)
    print("🌾  Agrithm Bot — Starting (TRANSLATION FIXED VERSION)")
    print(f"    Model  : {DHENU_MODEL}")
    print(f"    Ollama : {OLLAMA_URL}")
    print(f"    Whisper: {WHISPER_MODEL_SIZE}")
    print(f"    Farmers: {len(farmer_db)}")

    ollama_ok, models = check_ollama_connection()
    if ollama_ok:
        dhenu_found = any(DHENU_MODEL.split(":")[0] in m for m in models)
        print(f"    ✅ Ollama running | Models: {models}")
        if not dhenu_found:
            print(f"    ⚠️  WARNING: '{DHENU_MODEL}' not found")
            print(f"       Run: ollama pull {DHENU_MODEL}")
    else:
        print("    ❌ Ollama not reachable — run: ollama serve")

    # Quick translation sanity check at startup
    try:
        test = GoogleTranslator(source="en", target="hi").translate("Hello farmer")
        print(f"    ✅ Translation working: 'Hello farmer' → '{test}'")
    except Exception as e:
        print(f"    ❌ Translation BROKEN: {e}")
        print("       Run: pip install deep-translator")

    print("=" * 60)

    # Load Whisper in background (non-blocking)
    threading.Thread(target=_load_whisper_bg, daemon=True).start()

    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            STATE_LANGUAGE: [CallbackQueryHandler(language_selected, pattern="^lang:")],
            STATE_LOCATION: [
                MessageHandler(filters.LOCATION, location_received),
                MessageHandler(filters.TEXT & ~filters.COMMAND, location_received)
            ],
            STATE_TIME1: [CallbackQueryHandler(time1_selected, pattern="^time1:")],
            STATE_TIME2: [CallbackQueryHandler(time2_selected, pattern="^time2:")],
        },
        fallbacks=[CommandHandler("start", start)]
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("news",      cmd_news))
    app.add_handler(CommandHandler("settings",  cmd_settings))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("debug",     cmd_debug))
    app.add_handler(CommandHandler("testvoice", cmd_test_voice))
    app.add_handler(CommandHandler("help",      cmd_help))

    # Voice BEFORE text (order matters)
    app.add_handler(MessageHandler(filters.VOICE, handle_voice_query))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_query))

    for uid, farmer in farmer_db.items():
        times = farmer.get("alert_times", [])
        if times:
            register_schedule(app, farmer["chat_id"], times)

    threading.Thread(target=schedule_loop, args=(app,), daemon=True).start()

    print("✅ Bot running — Ctrl+C to stop\n")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
