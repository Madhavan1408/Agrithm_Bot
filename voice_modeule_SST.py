"""
stt.py
──────
Speech-to-Text using Faster-Whisper.
Supports Indian-accented speech across 5 languages.
"""

import io
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("faster-whisper not installed. STT will use fallback.")

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False


SUPPORTED_LANGUAGES = {
    "ta": "Tamil",
    "te": "Telugu",
    "hi": "Hindi",
    "kn": "Kannada",
    "en": "English",
    "ml": "Malayalam",
}

_whisper_model = None


def _get_whisper_model(model_size: str = "large-v2", device: str = "auto") -> "WhisperModel":
    global _whisper_model
    if _whisper_model is None and WHISPER_AVAILABLE:
        compute = "float16" if device == "cuda" else "int8"
        _whisper_model = WhisperModel(model_size, device=device, compute_type=compute)
        logger.info(f"Whisper model loaded: {model_size} on {device}")
    return _whisper_model


def transcribe_audio(
    audio_bytes: bytes,
    language: Optional[str] = None,
    model_size: str = "large-v2",
) -> Tuple[str, str]:
    """
    Transcribe audio bytes to text.

    Args:
        audio_bytes: Raw audio file bytes (mp3, wav, ogg, m4a)
        language: ISO language code hint ("ta", "hi", etc.) or None for auto-detect
        model_size: Whisper model variant

    Returns:
        (transcribed_text, detected_language_code)
    """
    if not WHISPER_AVAILABLE:
        return _fallback_transcribe(audio_bytes), "en"

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name

    try:
        model = _get_whisper_model(model_size)
        segments, info = model.transcribe(
            tmp_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        detected = info.language

        logger.info(f"STT → lang: {detected} | text: {text[:80]}...")
        return text, detected

    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return "", language or "en"

    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _fallback_transcribe(audio_bytes: bytes) -> str:
    """Fallback to Google Speech Recognition if Whisper unavailable."""
    if not SR_AVAILABLE:
        return ""
    recognizer = sr.Recognizer()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        tmp_path = f.name
    try:
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
        return recognizer.recognize_google(audio)
    except Exception as e:
        logger.error(f"Fallback STT failed: {e}")
        return ""
    finally:
        Path(tmp_path).unlink(missing_ok=True)
