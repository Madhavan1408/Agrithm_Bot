"""
tts.py
──────
Text-to-Speech using gTTS.
Converts advisory text to audio in native Indian languages.
"""

import io
import tempfile
from pathlib import Path
from typing import Optional

from loguru import logger

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logger.warning("gTTS not installed. TTS will be unavailable.")


LANG_MAP = {
    "ta": "ta",   # Tamil
    "te": "te",   # Telugu
    "hi": "hi",   # Hindi
    "kn": "kn",   # Kannada
    "en": "en",   # English
    "ml": "ml",   # Malayalam
    "mr": "mr",   # Marathi
}

SLOW_LANGS = {"ta", "te", "kn"}  # Slower TTS for clarity in complex scripts


def text_to_speech(
    text: str,
    language: str = "en",
    output_path: Optional[str] = None,
) -> Optional[bytes]:
    """
    Convert text to speech audio.

    Args:
        text: Text to synthesize
        language: ISO language code
        output_path: Optional file path to save MP3. If None, returns bytes.

    Returns:
        Audio bytes (MP3) or None on failure
    """
    if not GTTS_AVAILABLE:
        logger.error("gTTS not available. Cannot synthesize speech.")
        return None

    lang_code = LANG_MAP.get(language, "en")
    slow = language in SLOW_LANGS

    try:
        tts = gTTS(text=text, lang=lang_code, slow=slow)

        if output_path:
            tts.save(output_path)
            logger.info(f"TTS saved to {output_path}")
            return Path(output_path).read_bytes()

        buffer = io.BytesIO()
        tts.write_to_fp(buffer)
        buffer.seek(0)
        audio_bytes = buffer.read()
        logger.info(f"TTS generated: {len(audio_bytes)} bytes | lang: {language}")
        return audio_bytes

    except Exception as e:
        logger.error(f"TTS failed for lang={language}: {e}")
        return None


def text_to_speech_file(text: str, language: str = "en") -> Optional[str]:
    """Generate TTS and return temporary file path."""
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    result = text_to_speech(text, language, output_path=tmp_path)
    return tmp_path if result else None
