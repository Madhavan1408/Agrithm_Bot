"""
utils/voice.py — Agrithm Voice Processing Module
──────────────────────────────────────────────────
FIXES:
  - TTS_MODEL and STT_MODEL now imported from agrithm_config (was v1, config has v2)
  - TRANSLATE_MODEL also from config for consistency
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
SARVAM_TTS_URL       = "https://api.sarvam.ai/text-to-speech"

# FIX: Import models from config so there's a single source of truth
try:
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from agrithm_config import STT_MODEL, TTS_MODEL, TRANSLATE_MODEL
except ImportError:
    # Fallback if config not available
    STT_MODEL       = "saarika:v2.5"
    TTS_MODEL       = "bulbul:v2"      # FIX: was v1, should be v2
    TRANSLATE_MODEL = "mayura:v1"

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

CODE_TO_LANG: dict[str, str] = {v["code"]: k for k, v in LANG_CONFIG.items()}
SARVAM_DETECT_LANGS = [cfg["code"] for cfg in LANG_CONFIG.values()]

_CROP_KEYWORDS: list[str] = [
    "paddy", "rice", "wheat", "sugarcane", "cotton", "maize", "corn",
    "groundnut", "soybean", "turmeric", "chilli", "tomato", "onion",
    "potato", "banana", "mango", "coconut", "sunflower", "mustard",
    "jowar", "bajra", "ragi", "arhar", "dal", "pulses", "lentil",
    "chickpea", "brinjal", "okra", "lady finger", "cauliflower",
    "cabbage", "spinach", "garlic", "ginger", "pepper", "cardamom",
    "వరి", "వేరుశనగ", "మిరప", "పత్తి", "చెరకు", "మొక్కజొన్న",
    "అరటి", "మామిడి", "టమాటో", "ఉల్లిపాయ",
    "నెல்", "கரும்பு", "வாழை", "தக்காளி", "வெங்காயம்", "மிளகாய்",
    "धान", "गेहूं", "गन्ना", "कपास", "मक्का", "आलू", "टमाटर",
    "ಭತ್ತ", "ಕಬ್ಬು", "ಮೆಕ್ಕೆಜೋಳ", "ಟೊಮೆಟೊ",
]

_SYMPTOM_KEYWORDS: list[str] = [
    "yellowing", "wilting", "spots", "blight", "rot", "fungus", "mold",
    "pest", "insect", "holes", "curling", "drying", "stunted", "lesion",
    "discolouration", "discoloration", "powdery", "rust", "mosaic",
    "necrosis", "chlorosis", "damage", "infection", "disease", "worm",
    "larvae", "aphid", "whitefly", "mites", "thrips", "leaf curl",
    "పసుపు", "వాడు", "మచ్చలు", "తెగులు",
    "மஞ்சள்", "வாடல்", "புள்ளிகள்", "கருகல்",
    "पीला", "मुरझाना", "धब्बे", "झुलसा",
]


def _convert_to_wav(input_path: str) -> Optional[str]:
    wav_path: Optional[str] = None
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = tmp.name
        tmp.close()
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-ar", "16000", "-ac", "1", "-acodec", "pcm_s16le", wav_path,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if result.returncode != 0:
            log.error("ffmpeg conversion failed [code=%d]", result.returncode)
            os.unlink(wav_path)
            return None
        return wav_path
    except FileNotFoundError:
        log.error("ffmpeg not found. Install with: sudo apt install ffmpeg")
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)
        return None
    except subprocess.TimeoutExpired:
        log.error("ffmpeg timed out for: %s", input_path)
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)
        return None
    except Exception as e:
        log.error("Audio conversion error: %s", e)
        if wav_path and os.path.exists(wav_path):
            os.unlink(wav_path)
        return None


def transcribe_audio(file_path: str, lang_code: str = "unknown") -> tuple[str, str]:
    if not SARVAM_API_KEY:
        log.error("SARVAM_API_KEY not set in environment.")
        return "", lang_code
    if not os.path.exists(file_path):
        log.error("Audio file not found: %s", file_path)
        return "", lang_code

    wav_path: Optional[str] = None
    try:
        wav_path = _convert_to_wav(file_path)
        send_path = wav_path if wav_path else file_path
        if not wav_path:
            log.warning("WAV conversion failed; attempting STT with original file.")

        with open(send_path, "rb") as audio_file:
            audio_bytes = audio_file.read()

        files = {"file": ("audio.wav", audio_bytes, "audio/wav")}
        data: dict = {"model": STT_MODEL, "with_timestamps": False}

        if lang_code and lang_code != "unknown":
            data["language_code"] = lang_code

        headers = {"api-subscription-key": SARVAM_API_KEY}
        log.info("Calling Sarvam STT [lang=%s, size=%d bytes]", lang_code, len(audio_bytes))
        response = requests.post(SARVAM_STT_URL, headers=headers, files=files, data=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        transcript   = result.get("transcript", "").strip()
        detected_lang = result.get("language_code", "") or lang_code

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
            except Exception as cleanup_err:
                log.warning("Could not delete temp WAV: %s", cleanup_err)


def text_to_speech(text: str, lang_code: str, speaker: Optional[str] = None) -> Optional[bytes]:
    if not text or not text.strip():
        log.warning("text_to_speech called with empty text.")
        return None
    if not SARVAM_API_KEY:
        log.error("SARVAM_API_KEY not set; cannot generate TTS.")
        return None

    if not speaker:
        lang_name = CODE_TO_LANG.get(lang_code, "English")
        speaker = LANG_CONFIG.get(lang_name, LANG_CONFIG["English"])["tts_speaker"]

    MAX_CHARS = 500
    text = text.strip()
    if len(text) > MAX_CHARS:
        log.warning("TTS text truncated from %d to %d chars.", len(text), MAX_CHARS)
        text = text[:MAX_CHARS]

    try:
        payload = {
            "inputs":               [text],
            "target_language_code": lang_code,
            "speaker":              speaker,
            "pitch":                0,
            "pace":                 1.0,
            "loudness":             1.5,
            "speech_sample_rate":   8000,
            "enable_preprocessing": True,
            "model":                TTS_MODEL,  # FIX: from config, now v2
        }
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type":         "application/json",
        }
        log.info("Calling Sarvam TTS [lang=%s, speaker=%s, model=%s, chars=%d]",
                 lang_code, speaker, TTS_MODEL, len(text))
        response = requests.post(SARVAM_TTS_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()
        audios  = result.get("audios", [])
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
    except Exception as e:
        log.error("Sarvam TTS unexpected error: %s", e)
        return None


def _sarvam_translate(text: str, source_lang: str, target_lang: str) -> str:
    if not text.strip():
        return text
    if source_lang == target_lang:
        return text
    if not SARVAM_API_KEY:
        log.warning("SARVAM_API_KEY not set; skipping translation.")
        return text
    if len(text) > 1000:
        log.warning("Translation input truncated from %d to 1000 chars.", len(text))
    try:
        payload = {
            "input":                text[:1000],
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
        response = requests.post(SARVAM_TRANSLATE_URL, headers=headers, json=payload, timeout=20)
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
    if src_lang_code in ("en-IN", "en-US", "en"):
        return text
    return _sarvam_translate(text, src_lang_code, "en-IN")


def translate_from_english(text: str, tgt_lang_code: str) -> str:
    if tgt_lang_code in ("en-IN", "en-US", "en"):
        return text
    return _sarvam_translate(text, "en-IN", tgt_lang_code)


def extract_name(text: str) -> str:
    if not text:
        return ""
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
    telugu_m = re.search(r"నా పేరు\s+(\S+)", text)
    if telugu_m:
        return _clean_name(telugu_m.group(1))
    hindi_m = re.search(r"मेरा नाम\s+(\S+)", text)
    if hindi_m:
        return _clean_name(hindi_m.group(1))
    tamil_m = re.search(r"என் பெயர்\s+(\S+)", text)
    if tamil_m:
        return _clean_name(tamil_m.group(1))
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
    name = re.sub(r"[^\w\s\u0300-\u036f\u0900-\u0DFF]", "", name, flags=re.UNICODE)
    return name.strip()


def extract_crop(text: str) -> str:
    if not text:
        return ""
    text_lower = text.lower()
    for crop in _CROP_KEYWORDS:
        if crop.lower() in text_lower:
            log.debug("Crop extracted: %s", crop)
            return crop.lower()
    return ""


def extract_symptoms(text: str) -> list[str]:
    if not text:
        return []
    text_lower = text.lower()
    found = [kw for kw in _SYMPTOM_KEYWORDS if kw.lower() in text_lower]
    if found:
        log.debug("Symptoms extracted: %s", found)
    return found


def get_lang_config(language_name: str) -> dict:
    cfg = LANG_CONFIG.get(language_name)
    if not cfg:
        log.debug("Unknown language '%s'; defaulting to English.", language_name)
        return LANG_CONFIG["English"]
    return cfg


def lang_name_from_code(lang_code: str) -> str:
    return CODE_TO_LANG.get(lang_code, "English")
