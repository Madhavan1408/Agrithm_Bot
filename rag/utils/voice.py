"""
utils/voice.py
──────────────
Handles all audio operations using Sarvam AI:
  - STT  : transcribe_audio()       — voice → text
  - TTS  : speak()                  — text → voice
  - Trans: translate_to_english()   — local lang → English
  - Trans: translate_from_english() — English → local lang
"""

import os
import sys
import uuid
import base64
import logging
import subprocess

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agrithm_config import (
    SARVAM_API_KEY, STT_MODEL, TTS_MODEL, TRANSLATE_MODEL,
    LANGUAGES, AUDIO_TEMP_DIR
)

log = logging.getLogger(__name__)
os.makedirs(AUDIO_TEMP_DIR, exist_ok=True)


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def get_lang_config(language_name: str) -> dict:
    """Get language config dict by name. Defaults to English."""
    return LANGUAGES.get(language_name, LANGUAGES["English"])


def _convert_to_wav(input_path: str) -> str:
    """
    Convert .oga/.ogg (Telegram audio) to 16kHz mono .wav
    Required by Sarvam STT API.
    """
    output_path = os.path.splitext(input_path)[0] + "_converted.wav"
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", "16000",   # 16kHz — required by Sarvam
            "-ac", "1",       # mono
            "-f", "wav",
            output_path
        ], check=True, capture_output=True)
        return output_path
    except subprocess.CalledProcessError as e:
        log.error("ffmpeg conversion failed: %s", e.stderr.decode())
        raise
    except FileNotFoundError:
        raise RuntimeError(
            "ffmpeg not found. Install it: winget install ffmpeg\n"
            "or download from https://ffmpeg.org/download.html"
        )


# ═══════════════════════════════════════════════════════════════
# SPEECH TO TEXT
# ═══════════════════════════════════════════════════════════════

def transcribe_audio(path: str, lang_code: str) -> str:
    """
    Transcribe a voice file to text using Sarvam AI STT.
    Converts .oga → .wav automatically before sending.
    Returns empty string on failure.
    """
    wav_path = None
    try:
        wav_path = _convert_to_wav(path)

        with open(wav_path, "rb") as f:
            resp = httpx.post(
                "https://api.sarvam.ai/speech-to-text",
                headers={"api-subscription-key": SARVAM_API_KEY},
                files={"file": ("audio.wav", f, "audio/wav")},
                data={
                    "language_code": lang_code,
                    "model": STT_MODEL,
                },
                timeout=30,
            )
        resp.raise_for_status()
        transcript = resp.json().get("transcript", "").strip()
        log.info("STT transcript [%s]: %s", lang_code, transcript[:80])
        return transcript

    except httpx.HTTPStatusError as e:
        log.error("Sarvam STT error %s: %s", e.response.status_code, e.response.text)
        return ""
    except RuntimeError as e:
        log.error("Audio conversion error: %s", e)
        return ""
    except Exception as e:
        log.error("transcribe_audio failed: %s", e)
        return ""
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass


# ═══════════════════════════════════════════════════════════════
# TEXT TO SPEECH
# ═══════════════════════════════════════════════════════════════

def speak(text: str, lang_code: str, speaker: str = "anushka") -> str:
    """
    Convert text to speech using Sarvam AI TTS.
    Returns path to .wav audio file.
    Raises exception on failure — caller should handle.
    """
    # Sarvam TTS max ~500 chars — truncate gracefully
    if len(text) > 500:
        text = text[:497] + "..."

    resp = httpx.post(
        "https://api.sarvam.ai/text-to-speech",
        headers={
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "inputs":         [text],
            "target_language_code": lang_code,
            "speaker":        speaker,
            "model":          TTS_MODEL,
            "enable_preprocessing": True,
        },
        timeout=30,
    )
    resp.raise_for_status()

    audio_b64 = resp.json()["audios"][0]
    audio_bytes = base64.b64decode(audio_b64)

    out_path = os.path.join(AUDIO_TEMP_DIR, f"{uuid.uuid4().hex}.wav")
    with open(out_path, "wb") as f:
        f.write(audio_bytes)

    log.info("TTS generated [%s]: %s → %s", lang_code, text[:50], out_path)
    return out_path


# ═══════════════════════════════════════════════════════════════
# TRANSLATION
# ═══════════════════════════════════════════════════════════════

def translate_to_english(text: str, source_lang_code: str) -> str:
    """
    Translate text from farmer's language to English.
    Used before sending to RAG pipeline.
    Returns original text on failure.
    """
    if not text or not text.strip():
        return text
    if source_lang_code == "en-IN":
        return text  # already English

    try:
        resp = httpx.post(
            "https://api.sarvam.ai/translate",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "input":                text,
                "source_language_code": source_lang_code,
                "target_language_code": "en-IN",
                "model":                TRANSLATE_MODEL,
                "enable_preprocessing": True,
            },
            timeout=20,
        )
        resp.raise_for_status()
        translated = resp.json().get("translated_text", text).strip()
        log.info("Translated to English [%s→en]: %s", source_lang_code, translated[:80])
        return translated
    except Exception as e:
        log.warning("translate_to_english failed, using original: %s", e)
        return text


def translate_from_english(text: str, target_lang_code: str) -> str:
    """
    Translate English text to farmer's language.
    Used before sending RAG answer back to farmer.
    Returns original text on failure.
    """
    if not text or not text.strip():
        return text
    if target_lang_code == "en-IN":
        return text  # no translation needed

    try:
        resp = httpx.post(
            "https://api.sarvam.ai/translate",
            headers={
                "api-subscription-key": SARVAM_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "input":                text,
                "source_language_code": "en-IN",
                "target_language_code": target_lang_code,
                "model":                TRANSLATE_MODEL,
                "enable_preprocessing": True,
            },
            timeout=20,
        )
        resp.raise_for_status()
        translated = resp.json().get("translated_text", text).strip()
        log.info("Translated from English [en→%s]: %s", target_lang_code, translated[:80])
        return translated
    except Exception as e:
        log.warning("translate_from_english failed, using English: %s", e)
        return text