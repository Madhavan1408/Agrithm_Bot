"""
utils/voice.py — Agrithm Voice Processing Module
──────────────────────────────────────────────────
Handles all voice I/O for the Agrithm Telegram bot:

  • OGG/OPUS → WAV conversion (16kHz mono) via ffmpeg
  • Sarvam AI STT (saarika:v2.5) for transcription
  • Auto language detection from Sarvam API response
  • Sarvam AI Translation (mayura:v1) for English ↔ regional
  • Sarvam AI TTS (bulbul:v1) for voice output
  • Entity extraction: name, crop, symptoms
  • Graceful fallback on all API failures
  • Zero persistent audio storage (temp files cleaned immediately)

Public API
──────────
  transcribe_audio(file_path, lang_code="unknown") -> tuple[str, str]
  text_to_speech(text, lang_code, speaker)         -> bytes | None
  extract_name(text)                                -> str
  extract_crop(text)                                -> str
  extract_symptoms(text)                            -> list[str]
  translate_to_english(text, src_lang_code)         -> str
  translate_from_english(text, tgt_lang_code)       -> str
  get_lang_config(language_name)                    -> dict
"""

from __future__ import annotations

import os
import re
import json
import logging
import tempfile
import subprocess
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

# ── Sarvam API ────────────────────────────────────────────────────
SARVAM_API_KEY       = os.environ.get("SARVAM_API_KEY", "")
SARVAM_STT_URL       = "https://api.sarvam.ai/speech-to-text"
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
SARVAM_TTS_URL       = "https://api.sarvam.ai/text-to-speech"  # FIX: was missing entirely

STT_MODEL       = "saarika:v2.5"
TRANSLATE_MODEL = "mayura:v1"
TTS_MODEL       = "bulbul:v1"

# ── Language registry ─────────────────────────────────────────────
LANG_CONFIG: dict[str, dict] = {
    "Tamil":     {"code": "ta-IN", "tts_speaker": "anushka", "native": "தமிழ்"},
    "Telugu":    {"code": "te-IN", "tts_speaker": "anushka", "native": "తెలుగు"},
    "Kannada":   {"code": "kn-IN", "tts_speaker": "anushka", "native": "ಕನ್ನಡ"},
    "Malayalam": {"code": "ml-IN", "tts_speaker": "anushka", "native": "മലയാളം"},
    "Hindi":     {"code": "hi-IN", "tts_speaker": "anushka", "native": "हिन्दी"},
    "Punjabi":   {"code": "pa-IN", "tts_speaker": "neel",    "native": "ਪੰਜਾਬੀ"},
    "Gujarati":  {"code": "gu-IN", "tts_speaker": "anushka", "native": "ગુજરાતી"},
    "Marathi":   {"code": "mr-IN", "tts_speaker": "anushka", "native": "मराठी"},
    "Bengali":   {"code": "bn-IN", "tts_speaker": "anushka", "native": "বাংলা"},
    "Odia":      {"code": "od-IN", "tts_speaker": "anushka", "native": "ଓଡ଼ିଆ"},
    "English":   {"code": "en-IN", "tts_speaker": "meera",   "native": "English"},
}

# Reverse map: BCP-47 code → language name
CODE_TO_LANG: dict[str, str] = {v["code"]: k for k, v in LANG_CONFIG.items()}

SARVAM_DETECT_LANGS = [cfg["code"] for cfg in LANG_CONFIG.values()]

# ── Common agricultural crop terms for extraction ─────────────────
_CROP_KEYWORDS: list[str] = [
    # English
    "paddy", "rice", "wheat", "sugarcane", "cotton", "maize", "corn",
    "groundnut", "soybean", "turmeric", "chilli", "tomato", "onion",
    "potato", "banana", "mango", "coconut", "sunflower", "mustard",
    "jowar", "bajra", "ragi", "arhar", "dal", "pulses", "lentil",
    "chickpea", "brinjal", "okra", "lady finger", "cauliflower",
    "cabbage", "spinach", "garlic", "ginger", "pepper", "cardamom",
    # Telugu
    "వరి", "వేరుశనగ", "మిరప", "పత్తి", "చెరకు", "మొక్కజొన్న",
    "అరటి", "మామిడి", "టమాటో", "ఉల్లిపాయ",
    # Tamil
    "நெல்", "கரும்பு", "வாழை", "தக்காளி", "வெங்காயம்", "மிளகாய்",
    # Hindi
    "धान", "गेहूं", "गन्ना", "कपास", "मक्का", "आलू", "टमाटर",
    # Kannada
    "ಭತ್ತ", "ಕಬ್ಬು", "ಮೆಕ್ಕೆಜೋಳ", "ಟೊಮೆಟೊ",
]

# Common disease/symptom terms
_SYMPTOM_KEYWORDS: list[str] = [
    "yellowing", "wilting", "spots", "blight", "rot", "fungus", "mold",
    "pest", "insect", "holes", "curling", "drying", "stunted", "lesion",
    "discolouration", "discoloration", "powdery", "rust", "mosaic",
    "necrosis", "chlorosis", "damage", "infection", "disease", "worm",
    "larvae", "aphid", "whitefly", "mites", "thrips", "leaf curl",
    # Telugu
    "పసుపు", "వాడు", "మచ్చలు", "తెగులు",
    # Tamil
    "மஞ்சள்", "வாடல்", "புள்ளிகள்", "கருகல்",
    # Hindi
    "पीला", "मुरझाना", "धब्बे", "झुलसा",
]


# ═══════════════════════════════════════════════════════════════════
# AUDIO CONVERSION
# ═══════════════════════════════════════════════════════════════════

def _convert_to_wav(input_path: str) -> Optional[str]:
    """
    Convert any audio format (OGG, OPUS, MP3, etc.) to 16kHz mono WAV
    using ffmpeg. Returns path to temp WAV file, or None on failure.

    The caller is responsible for deleting the returned temp file.
    """
    wav_path: Optional[str] = None  # FIX: declare before try so except blocks can clean up
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = tmp.name
        tmp.close()

        cmd = [
            "ffmpeg",
            "-y",
            "-i", input_path,
            "-ar", "16000",
            "-ac", "1",
            "-acodec", "pcm_s16le",
            wav_path,
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
        if result.returncode != 0:
            log.error(
                "ffmpeg conversion failed [code=%d]: %s",
                result.returncode,
                result.stderr.decode(errors="replace")[:300],
            )
            os.unlink(wav_path)
            return None

        log.debug("Audio converted → %s", wav_path)
        return wav_path

    except FileNotFoundError:
        log.error("ffmpeg not found. Install with: sudo apt install ffmpeg")
        if wav_path and os.path.exists(wav_path):  # FIX: clean up on all exception paths
            os.unlink(wav_path)
        return None
    except subprocess.TimeoutExpired:
        log.error("ffmpeg timed out for: %s", input_path)
        if wav_path and os.path.exists(wav_path):  # FIX: was leaking temp file here
            os.unlink(wav_path)
        return None
    except Exception as e:
        log.error("Audio conversion error: %s", e)
        if wav_path and os.path.exists(wav_path):  # FIX: clean up on all exception paths
            os.unlink(wav_path)
        return None


# ═══════════════════════════════════════════════════════════════════
# SARVAM STT
# ═══════════════════════════════════════════════════════════════════

def transcribe_audio(file_path: str, lang_code: str = "unknown") -> tuple[str, str]:
    """
    Transcribe a voice file using Sarvam AI STT (saarika:v2.5).

    Parameters
    ──────────
    file_path : str
        Path to the audio file (OGG/OPUS from Telegram, or any ffmpeg-readable format).
    lang_code : str
        BCP-47 code hint (e.g. "te-IN"). Use "unknown" for auto-detect.

    Returns
    ───────
    tuple[str, str]
        (transcript, detected_lang_code)
        transcript is empty string on failure.
        detected_lang_code falls back to the passed lang_code if Sarvam doesn't return one.

    FIX: previously returned only str — callers had no way to get detected language,
         breaking language-adaptive responses and TTS voice selection.
    """
    if not SARVAM_API_KEY:
        log.error("SARVAM_API_KEY not set in environment.")
        return "", lang_code

    if not os.path.exists(file_path):
        log.error("Audio file not found: %s", file_path)
        return "", lang_code

    wav_path: Optional[str] = None
    try:
        # ── 1. Convert to 16kHz mono WAV ──────────────────────────
        wav_path = _convert_to_wav(file_path)
        send_path = wav_path if wav_path else file_path
        if not wav_path:
            log.warning("WAV conversion failed; attempting STT with original file.")

        # ── 2. Build multipart request ────────────────────────────
        with open(send_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        files = {
            "file": ("audio.wav", audio_bytes, "audio/wav"),
        }
        # FIX: with_timestamps must be boolean false, not string "false"
        # Some Sarvam API versions reject the string form
        data: dict = {
            "model": STT_MODEL,
            "with_timestamps": False,
        }

        # Only pass language_code when we actually know it
        # FIX: original code also excluded "en-IN" — wrong, we should pass it when known
        if lang_code and lang_code != "unknown":
            data["language_code"] = lang_code

        headers = {
            "api-subscription-key": SARVAM_API_KEY,
        }

        # ── 3. Call Sarvam API ────────────────────────────────────
        log.info("Calling Sarvam STT [lang=%s, size=%d bytes]", lang_code, len(audio_bytes))
        response = requests.post(
            SARVAM_STT_URL,
            headers=headers,
            files=files,
            data=data,
            timeout=30,
        )
        response.raise_for_status()

        # ── 4. Parse response ─────────────────────────────────────
        result = response.json()
        transcript = result.get("transcript", "").strip()
        # FIX: return detected language so callers can update session state
        detected_lang = result.get("language_code", "") or lang_code

        if detected_lang:
            log.info("Sarvam detected language: %s", detected_lang)

        if not transcript:
            log.warning("Sarvam returned empty transcript.")
            return "", detected_lang

        log.info("Transcription complete [%d chars]: %s…", len(transcript), transcript[:60])
        return transcript, detected_lang

    except requests.exceptions.Timeout:
        log.error("Sarvam STT timed out.")
        return "", lang_code
    except requests.exceptions.HTTPError as e:
        log.error("Sarvam STT HTTP error [%s]: %s", e.response.status_code, e.response.text[:200])
        return "", lang_code
    except requests.exceptions.RequestException as e:
        log.error("Sarvam STT request failed: %s", e)
        return "", lang_code
    except json.JSONDecodeError:
        log.error("Sarvam STT returned non-JSON response.")
        return "", lang_code
    except Exception as e:
        log.error("transcribe_audio unexpected error: %s", e)
        return "", lang_code
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
                log.debug("Temp WAV deleted: %s", wav_path)
            except Exception as cleanup_err:
                log.warning("Could not delete temp WAV: %s", cleanup_err)


# ═══════════════════════════════════════════════════════════════════
# SARVAM TTS  ← FIX: this entire section was missing; caused voice output to break
# ═══════════════════════════════════════════════════════════════════

def text_to_speech(
    text: str,
    lang_code: str,
    speaker: Optional[str] = None,
) -> Optional[bytes]:
    """
    Convert text to speech using Sarvam AI TTS (bulbul:v1).

    Parameters
    ──────────
    text      : Text to speak (in the target language)
    lang_code : BCP-47 code (e.g. "te-IN"). Determines voice model.
    speaker   : Optional speaker name override. Defaults to language config default.

    Returns
    ───────
    Raw audio bytes (WAV) ready to send as a Telegram voice message,
    or None on failure.

    Usage in bot handler
    ────────────────────
    audio_bytes = text_to_speech(reply_text, "te-IN")
    if audio_bytes:
        await bot.send_voice(chat_id, BufferedInputFile(audio_bytes, "reply.wav"))
    else:
        await bot.send_message(chat_id, reply_text)   # text fallback
    """
    if not text or not text.strip():
        log.warning("text_to_speech called with empty text.")
        return None

    if not SARVAM_API_KEY:
        log.error("SARVAM_API_KEY not set; cannot generate TTS.")
        return None

    # Resolve speaker from language config if not supplied
    if not speaker:
        lang_name = CODE_TO_LANG.get(lang_code, "English")
        speaker = LANG_CONFIG.get(lang_name, LANG_CONFIG["English"])["tts_speaker"]

    # Sarvam TTS has a per-request character limit; chunk if needed
    MAX_CHARS = 500
    text = text.strip()
    if len(text) > MAX_CHARS:
        log.warning("TTS text truncated from %d to %d chars.", len(text), MAX_CHARS)
        text = text[:MAX_CHARS]

    try:
        payload = {
            "inputs":          [text],
            "target_language_code": lang_code,
            "speaker":         speaker,
            "pitch":           0,
            "pace":            1.0,
            "loudness":        1.5,
            "speech_sample_rate": 8000,
            "enable_preprocessing": True,
            "model":           TTS_MODEL,
        }
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type":         "application/json",
        }

        log.info("Calling Sarvam TTS [lang=%s, speaker=%s, chars=%d]", lang_code, speaker, len(text))
        response = requests.post(
            SARVAM_TTS_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()

        result = response.json()
        # Sarvam TTS returns: { "audios": ["<base64-wav>", ...] }
        audios = result.get("audios", [])
        if not audios:
            log.error("Sarvam TTS returned no audio data.")
            return None

        import base64
        audio_bytes = base64.b64decode(audios[0])
        log.info("TTS complete [%d bytes audio]", len(audio_bytes))
        return audio_bytes

    except requests.exceptions.Timeout:
        log.error("Sarvam TTS timed out.")
        return None
    except requests.exceptions.HTTPError as e:
        log.error("Sarvam TTS HTTP error [%s]: %s", e.response.status_code, e.response.text[:200])
        return None
    except requests.exceptions.RequestException as e:
        log.error("Sarvam TTS request failed: %s", e)
        return None
    except (json.JSONDecodeError, KeyError, Exception) as e:
        log.error("Sarvam TTS unexpected error: %s", e)
        return None


# ═══════════════════════════════════════════════════════════════════
# TRANSLATION  (Sarvam mayura:v1)
# ═══════════════════════════════════════════════════════════════════

def _sarvam_translate(text: str, source_lang: str, target_lang: str) -> str:
    """
    Internal: call Sarvam translate API.
    Returns translated text or original text on failure.
    """
    if not text.strip():
        return text
    if source_lang == target_lang:
        return text
    if not SARVAM_API_KEY:
        log.warning("SARVAM_API_KEY not set; skipping translation.")
        return text

    # FIX: log a warning when text is silently truncated
    if len(text) > 1000:
        log.warning("Translation input truncated from %d to 1000 chars.", len(text))

    try:
        payload = {
            "input":               text[:1000],
            "source_language_code": source_lang,
            "target_language_code": target_lang,
            "speaker_gender":       "Female",
            "mode":                 "formal",
            "model":                TRANSLATE_MODEL,
            "enable_preprocessing": True,
        }
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type":         "application/json",
        }
        response = requests.post(
            SARVAM_TRANSLATE_URL,
            headers=headers,
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        translated = response.json().get("translated_text", "").strip()
        return translated if translated else text

    except requests.exceptions.HTTPError as e:
        log.warning("Translation HTTP error [%s → %s]: %s", source_lang, target_lang, e)
        return text
    except Exception as e:
        log.warning("Translation failed [%s → %s]: %s", source_lang, target_lang, e)
        return text


def translate_to_english(text: str, src_lang_code: str) -> str:
    """
    Translate regional language text to English.
    If src_lang_code is already English, returns text unchanged.
    """
    if src_lang_code in ("en-IN", "en-US", "en"):
        return text
    return _sarvam_translate(text, src_lang_code, "en-IN")


def translate_from_english(text: str, tgt_lang_code: str) -> str:
    """
    Translate English text to a regional language.
    If tgt_lang_code is English, returns text unchanged.
    """
    if tgt_lang_code in ("en-IN", "en-US", "en"):
        return text
    return _sarvam_translate(text, "en-IN", tgt_lang_code)


# ═══════════════════════════════════════════════════════════════════
# ENTITY EXTRACTION
# ═══════════════════════════════════════════════════════════════════

def extract_name(text: str) -> str:
    """
    Extract a person's name from a sentence.

    Strategy:
      1. Pattern match common intro phrases: "My name is X", "I am X", "నా పేరు X"
      2. Capitalised word heuristic as fallback
      3. Returns the first matched token cleaned of punctuation

    Examples
    ────────
    >>> extract_name("My name is Ramesh from Nellore")
    'Ramesh'
    >>> extract_name("నా పేరు రమేష్")
    'రమేష్'
    >>> extract_name("मेरा नाम सुरेश है")
    'सुरेश'
    """
    if not text:
        return ""

    # ── Pattern 1: English intro phrases ─────────────────────
    english_patterns = [
        r"(?:my name is|i am|i'm|call me|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        r"(?:name is|named)\s+([A-Z][a-z]+)",
    ]
    for pattern in english_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            name = m.group(1).strip()
            name = re.split(r"\s+(?:from|of|in|at)\b", name, flags=re.IGNORECASE)[0]
            return _clean_name(name)

    # ── Pattern 2: Telugu intro phrases ──────────────────────
    telugu_m = re.search(r"నా పేరు\s+(\S+)", text)
    if telugu_m:
        return _clean_name(telugu_m.group(1))

    # ── Pattern 3: Hindi intro phrase ────────────────────────
    hindi_m = re.search(r"मेरा नाम\s+(\S+)", text)
    if hindi_m:
        return _clean_name(hindi_m.group(1))

    # ── Pattern 4: Tamil intro phrase ────────────────────────
    tamil_m = re.search(r"என் பெயர்\s+(\S+)", text)
    if tamil_m:
        return _clean_name(tamil_m.group(1))

    # ── Pattern 5: Capitalised word fallback (English only) ──
    if re.search(r"[a-zA-Z]", text):
        _non_names = {
            "I", "My", "The", "A", "An", "Is", "Am", "From", "In",
            "At", "Of", "And", "But", "Sir", "Madam", "Hello", "Hi",
        }
        tokens = text.split()
        for token in tokens:
            clean = re.sub(r"[^a-zA-Z]", "", token)
            if clean and clean[0].isupper() and len(clean) > 2 and clean not in _non_names:
                return clean

    return ""


def _clean_name(name: str) -> str:
    """
    Strip punctuation and extra whitespace from an extracted name.

    FIX: original regex used explicit Unicode block ranges which excluded
    Punjabi (Gurmukhi U+0A00-U+0A7F) and Odia (U+0B00-U+0B7F) characters.
    Replaced with a broad Unicode word character match that covers all scripts.
    """
    # Keep letters, digits, spaces, and Unicode combining marks.
    # The \w shorthand strips combining marks (e.g. Telugu virama ్ U+0C4D,
    # matras in Devanagari, etc.) which are essential parts of Indian script names.
    # We use Unicode category matching instead:
    #   \w  → word chars (letters, digits, _)
    #   \s  → whitespace
    #   \u0300-\u036f → combining diacritics
    #   \u0900-\u0DFF → Devanagari through Sinhala (covers all major Indian scripts)
    #   \u0A00-\u0A7F → Gurmukhi (Punjabi)  — kept explicit for clarity
    name = re.sub(
        r"[^\w\s\u0300-\u036f\u0900-\u0DFF]",
        "",
        name,
        flags=re.UNICODE,
    )
    return name.strip()


def extract_crop(text: str) -> str:
    """
    Extract a crop name from transcribed text.

    Returns the first matched crop name in lowercase, or "" if not found.

    Examples
    ────────
    >>> extract_crop("I grow paddy and some vegetables")
    'paddy'
    >>> extract_crop("నేను వరి పండిస్తాను")
    'వరి'
    """
    if not text:
        return ""
    text_lower = text.lower()
    for crop in _CROP_KEYWORDS:
        if crop.lower() in text_lower:
            log.debug("Crop extracted: %s", crop)
            return crop.lower()
    return ""


def extract_symptoms(text: str) -> list[str]:
    """
    Extract disease/pest symptoms from a farmer's voice description.

    Returns list of matched symptom keywords, or [] if none found.

    Examples
    ────────
    >>> extract_symptoms("The leaves are yellowing and I see white spots")
    ['yellowing', 'spots']
    """
    if not text:
        return []
    text_lower = text.lower()
    found = [kw for kw in _SYMPTOM_KEYWORDS if kw.lower() in text_lower]
    if found:
        log.debug("Symptoms extracted: %s", found)
    return found


# ═══════════════════════════════════════════════════════════════════
# LANGUAGE CONFIG HELPERS
# ═══════════════════════════════════════════════════════════════════

def get_lang_config(language_name: str) -> dict:
    """
    Return config dict for a language name.
    Falls back to English config if name not found.

    Example
    ───────
    >>> get_lang_config("Telugu")
    {'code': 'te-IN', 'tts_speaker': 'anushka', 'native': 'తెలుగు'}
    """
    cfg = LANG_CONFIG.get(language_name)
    if not cfg:
        log.debug("Unknown language '%s'; defaulting to English.", language_name)
        return LANG_CONFIG["English"]
    return cfg


def lang_name_from_code(lang_code: str) -> str:
    """
    Reverse-lookup: BCP-47 code → language name.

    Example
    ───────
    >>> lang_name_from_code("te-IN")
    'Telugu'
    """
    return CODE_TO_LANG.get(lang_code, "English")