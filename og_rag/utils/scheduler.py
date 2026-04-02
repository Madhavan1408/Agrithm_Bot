"""
utils/scheduler.py
──────────────────
APScheduler-based daily digest sender.
Fires every minute and sends digests to farmers whose scheduled
time matches now (IST).

FIXES vs v1:
  FIX L2: Removed local duplicate get_all_profiles() — now imports
          from utils.storage where it is properly maintained.
  FIX H5: Uses absolute path for logs directory.
  FIX H4: TTS model unified to bulbul:v2.
"""

import os
import sys
import base64
import logging
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

# ── Path setup ─────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            os.path.join(_ROOT, "logs", "scheduler.log"), encoding="utf-8"
        ),
    ]
)
log = logging.getLogger("agrithm.scheduler")
IST = ZoneInfo("Asia/Kolkata")

# ── Load env ────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(os.path.join(_ROOT, ".env"))

SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY", "")

# FIX L2: Import from storage — no more local duplicate
from utils.storage import get_all_profiles, update_profile


# ═══════════════════════════════════════════════════════════════════════
# Sarvam TTS + Translate — inline, no dependency on bot.py
# ═══════════════════════════════════════════════════════════════════════

_SARVAM_LANG_MAP = {
    "Tamil": "ta-IN", "Telugu": "te-IN", "Hindi": "hi-IN",
    "Kannada": "kn-IN", "Malayalam": "ml-IN", "Punjabi": "pa-IN",
    "Gujarati": "gu-IN", "Marathi": "mr-IN", "Bengali": "bn-IN",
    "Odia": "od-IN", "English": "en-IN",
}
_SARVAM_SPEAKERS = {
    "Tamil": "anushka", "Telugu": "anushka", "Hindi": "anushka",
    "Kannada": "anushka", "Malayalam": "anushka", "Punjabi": "neel",
    "Gujarati": "anushka", "Marathi": "anushka", "Bengali": "anushka",
    "Odia": "anushka", "English": "meera",
}


def _sarvam_tts(text: str, lang_name: str) -> str | None:
    """Generate TTS audio via Sarvam API. Returns temp WAV path or None."""
    if not SARVAM_API_KEY:
        return None
    lang_code = _SARVAM_LANG_MAP.get(lang_name, "en-IN")
    speaker   = _SARVAM_SPEAKERS.get(lang_name, "meera")
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
                "pitch": 0, "pace": 1.0, "loudness": 1.5,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model": "bulbul:v2",   # FIX H4: unified to v2
            },
            timeout=30,
        )
        resp.raise_for_status()
        audio_bytes = base64.b64decode(resp.json()["audios"][0])
        path = os.path.join(
            _ROOT, "audio_temp",
            f"digest_{datetime.now().timestamp()}.wav",
        )
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(audio_bytes)
        return path
    except Exception as e:
        log.warning("Sarvam TTS failed [%s]: %s", lang_name, e)
        return None


def _sarvam_translate(text: str, src: str, tgt: str) -> str:
    """Translate text via Sarvam mayura:v1. Returns original on failure."""
    if src == tgt or not SARVAM_API_KEY:
        return text
    try:
        resp = requests.post(
            "https://api.sarvam.ai/translate",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "input": text[:1000],
                "source_language_code": src,
                "target_language_code": tgt,
                "speaker_gender": "Female",
                "mode": "formal",
                "model": "mayura:v1",
                "enable_preprocessing": True,
            },
            timeout=20,
        )
        resp.raise_for_status()
        return resp.json().get("translated_text", text).strip() or text
    except Exception as e:
        log.warning("Translation failed [%s→%s]: %s", src, tgt, e)
        return text


# ═══════════════════════════════════════════════════════════════════════
# Digest Generator — graceful fallback if RAG unavailable
# ═══════════════════════════════════════════════════════════════════════

def _generate_digest(district: str, crop: str) -> str:
    """
    Try to use RAG digest generator; fall back to a generic message.
    Prevents scheduler from crashing when RAG module has issues.
    """
    try:
        from utils.rag import generate_daily_digest
        result = generate_daily_digest(district, crop)
        if result and result.strip():
            return result
    except Exception as e:
        log.warning("RAG digest failed, using fallback: %s", e)

    # Fallback generic digest
    return (
        f"Good morning! Here is your daily farming update.\n\n"
        f"• Check soil moisture levels for your {crop} crop today.\n"
        f"• Monitor for any pest activity and inspect leaves carefully.\n"
        f"• Review weather forecast before irrigation.\n"
        f"• Contact your local agricultural office for latest scheme info.\n\n"
        f"Have a productive day! 🌾"
    )


# ═══════════════════════════════════════════════════════════════════════
# Digest Sender
# ═══════════════════════════════════════════════════════════════════════

async def send_daily_digest(bot: Bot, user_id: int, profile: dict) -> bool:
    """Send personalized voice + text digest. Returns True on success."""
    lang_name = profile.get("language", "English")
    district  = profile.get("district", "")
    crop      = profile.get("crop", "your crop")

    log.info("Digest: user=%s crop=%s lang=%s", user_id, crop, lang_name)

    # Generate English digest
    english_digest = _generate_digest(district, crop)

    # Translate if needed
    src_code = _SARVAM_LANG_MAP.get(lang_name, "en-IN")
    if lang_name != "English":
        local_digest = _sarvam_translate(english_digest, "en-IN", src_code)
    else:
        local_digest = english_digest

    # Send text message
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🌾 *Good morning!* Here is your daily farm update.\n\n{local_digest}",
            parse_mode=ParseMode.MARKDOWN,
        )
    except TelegramError as e:
        log.error("Text send failed user=%s: %s", user_id, e)
        return False

    # Send voice message (best-effort, never crashes scheduler)
    audio_path = None
    try:
        audio_path = _sarvam_tts(local_digest, lang_name)
        if audio_path:
            with open(audio_path, "rb") as f:
                await bot.send_voice(
                    chat_id=user_id,
                    voice=f,
                    caption="🎙️ Daily farm digest",
                )
    except Exception as e:
        log.warning("Voice send failed user=%s: %s", user_id, e)
    finally:
        if audio_path and os.path.exists(audio_path):
            try:
                os.remove(audio_path)
            except OSError:
                pass

    update_profile(user_id, last_digest_date=datetime.now(IST).strftime("%Y-%m-%d"))
    return True


# ═══════════════════════════════════════════════════════════════════════
# Per-minute Job
# ═══════════════════════════════════════════════════════════════════════

async def _check_and_send_digests(bot: Bot) -> None:
    now       = datetime.now(IST)
    today_key = now.strftime("%Y-%m-%d")
    # FIX L2: uses imported get_all_profiles from storage.py
    profiles  = get_all_profiles()

    if not profiles:
        return

    sent = errors = 0
    for uid_str, profile in profiles.items():
        if not profile.get("onboarded"):
            continue
        digest_time = profile.get("digest_time")
        if not digest_time:
            continue
        # Already sent today — skip
        if profile.get("last_digest_date") == today_key:
            continue
        try:
            scheduled = datetime.strptime(digest_time, "%H:%M")
        except ValueError:
            continue
        if now.hour != scheduled.hour or now.minute != scheduled.minute:
            continue

        log.info("Time matched: user=%s at %s", uid_str, digest_time)
        try:
            if await send_daily_digest(bot, int(uid_str), profile):
                sent += 1
            else:
                errors += 1
        except Exception as e:
            log.error("Digest failed user=%s: %s", uid_str, e)
            errors += 1

    if sent or errors:
        log.info("Digest run — sent: %d | errors: %d", sent, errors)


# ═══════════════════════════════════════════════════════════════════════
# Bootstrap
# ═══════════════════════════════════════════════════════════════════════

def create_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Create and return configured APScheduler. Call .start() after bot starts."""
    scheduler = AsyncIOScheduler(timezone=IST)
    scheduler.add_job(
        _check_and_send_digests,
        trigger=CronTrigger(minute="*", timezone=IST),
        args=[bot],
        id="daily_digest",
        name="Agrithm Daily Digest Dispatcher",
        max_instances=1,
        misfire_grace_time=30,
    )
    log.info("Scheduler ready — fires every minute (IST).")
    return scheduler