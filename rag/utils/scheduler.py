"""
utils/scheduler.py
──────────────────
APScheduler-based daily digest sender.
Fires every minute and sends digests to farmers whose scheduled time matches now (IST).
"""

import os
import sys
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(os.path.join(_ROOT, "logs"), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(_ROOT, "logs", "scheduler.log"), encoding="utf-8"),
    ]
)
log = logging.getLogger("agrithm.scheduler")
IST = ZoneInfo("Asia/Kolkata")


# ── Digest Sender ─────────────────────────────────────────────────

async def send_daily_digest(bot: Bot, user_id: int, profile: dict) -> bool:
    """Send personalized voice + text digest. Returns True on success."""
    from utils.rag    import generate_daily_digest
    from utils.voice  import speak, translate_from_english, get_lang_config
    from utils.storage import update_profile

    lang_name = profile.get("language", "English")
    district  = profile.get("district", "")
    crop      = profile.get("crop", "")

    log.info("Digest: user=%s crop=%s lang=%s", user_id, crop, lang_name)

    try:
        lang_cfg  = get_lang_config(lang_name)
        lang_code = lang_cfg["code"]
        speaker   = lang_cfg["tts_speaker"]
    except Exception as e:
        log.error("Language config failed user=%s: %s", user_id, e)
        return False

    try:
        english_digest = generate_daily_digest(district, crop)
        if not english_digest or not english_digest.strip():
            log.warning("Empty digest for user=%s", user_id)
            return False
    except Exception as e:
        log.error("RAG failed user=%s: %s", user_id, e)
        return False

    try:
        local_digest = translate_from_english(english_digest, lang_code) if lang_name != "English" else english_digest
    except Exception as e:
        log.warning("Translation failed user=%s, using English: %s", user_id, e)
        local_digest = english_digest

    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🌾 *Good morning!* Here is your daily farm update.\n\n{local_digest}",
            parse_mode=ParseMode.MARKDOWN
        )
    except TelegramError as e:
        log.error("Text send failed user=%s: %s", user_id, e)
        return False

    audio_path = None
    try:
        audio_path = speak(local_digest, lang_code, speaker)
        with open(audio_path, "rb") as f:
            await bot.send_voice(chat_id=user_id, voice=f, caption="🎙️ Daily farm digest")
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


# ── Per-minute Job ────────────────────────────────────────────────

async def _check_and_send_digests(bot: Bot):
    from utils.storage import get_all_profiles

    now       = datetime.now(IST)
    today_key = now.strftime("%Y-%m-%d")
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
        if profile.get("last_digest_date") == today_key:
            continue
        try:
            scheduled = datetime.strptime(digest_time, "%H:%M")
        except ValueError:
            continue
        if now.hour != scheduled.hour or now.minute != scheduled.minute:
            continue

        log.info("Time matched: user=%s at %s", uid_str, digest_time)
        if await send_daily_digest(bot, int(uid_str), profile):
            sent += 1
        else:
            errors += 1

    if sent or errors:
        log.info("Digest run — sent: %d | errors: %d", sent, errors)


# ── Bootstrap ─────────────────────────────────────────────────────

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