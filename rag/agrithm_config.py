"""
agrithm_config.py
─────────────────
Single source of truth for all Agrithm settings.
All secrets loaded from .env file — never hardcoded.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY")
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
MANDI_API_KEY  = os.environ.get("MANDI_API_KEY")

# ── Validate required keys on startup ────────────────────────────
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN missing from .env")
if not SARVAM_API_KEY:
    raise ValueError("SARVAM_API_KEY missing from .env")

# ── LLM Backend ───────────────────────────────────────────────────
# Set to "ollama" to use local Ollama instead of Groq
# Set to "groq"   to use Groq cloud API

# ── Ollama Settings ───────────────────────────────────────────────
OLLAMA_URL   = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "dhenu2-farming:latest"

# ── Sarvam AI Models ──────────────────────────────────────────────
STT_MODEL       = "saarika:v2.5"
TTS_MODEL       = "bulbul:v2"
TRANSLATE_MODEL = "mayura:v1"

# ── Embedding Model ───────────────────────────────────────────────
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ── Paths ─────────────────────────────────────────────────────────
VECTOR_STORE_PATH   = "vector_store"
USER_PROFILES_PATH  = "data/user_profiles.json"
FARMER_NETWORK_PATH = "data/farmer_network.json"
AUDIO_TEMP_DIR      = "audio_temp"

# ── RAG Settings ──────────────────────────────────────────────────
TOP_K          = 4
MIN_SIMILARITY = 0.35

# ── Supported Languages ───────────────────────────────────────────
LANGUAGES = {
    # ── South Indian ──────────────────────────────────────────────
    "Tamil": {
        "code": "ta-IN",
        "tts_speaker": "anushka",
        "native": "தமிழ்",
        "region": "south",
    },
    "Telugu": {
        "code": "te-IN",
        "tts_speaker": "anushka",
        "native": "తెలుగు",
        "region": "south",
    },
    "Kannada": {
        "code": "kn-IN",
        "tts_speaker": "anushka",
        "native": "ಕನ್ನಡ",
        "region": "south",
    },
    "Malayalam": {
        "code": "ml-IN",
        "tts_speaker": "anushka",
        "native": "മലയാളം",
        "region": "south",
    },
    # ── North Indian ──────────────────────────────────────────────
    "Hindi": {
        "code": "hi-IN",
        "tts_speaker": "anushka",
        "native": "हिन्दी",
        "region": "north",
    },
    "Punjabi": {
        "code": "pa-IN",
        "tts_speaker": "neel",
        "native": "ਪੰਜਾਬੀ",
        "region": "north",
    },
    "Gujarati": {
        "code": "gu-IN",
        "tts_speaker": "anushka",
        "native": "ગુજરાતી",
        "region": "west",
    },
    "Marathi": {
        "code": "mr-IN",
        "tts_speaker": "anushka",
        "native": "मराठी",
        "region": "west",
    },
    # ── East Indian ───────────────────────────────────────────────
    "Bengali": {
        "code": "bn-IN",
        "tts_speaker": "anushka",
        "native": "বাংলা",
        "region": "east",
    },
    "Odia": {
        "code": "od-IN",
        "tts_speaker": "anushka",
        "native": "ଓଡ଼ିଆ",
        "region": "east",
    },
    "English": {
        "code": "en-IN",
        "tts_speaker": "anushka",
        "native": "English",
        "region": "pan-india",
    },
}

# ── Quick lookup helpers ──────────────────────────────────────────
LANGUAGE_NAMES   = list(LANGUAGES.keys())
LANGUAGE_CODES   = {k: v["code"] for k, v in LANGUAGES.items()}
CODE_TO_LANGUAGE = {v["code"]: k for k, v in LANGUAGES.items()}

# ── Bot Conversation States ───────────────────────────────────────
(
    STATE_ONBOARD_LANG,
    STATE_ONBOARD_NAME,
    STATE_ONBOARD_CROP,
    STATE_ONBOARD_LOCATION,
    STATE_ONBOARD_TIME,
    STATE_ONBOARD_VILLAGE,
    STATE_MAIN_MENU,
    STATE_VOICE_QUERY,
    STATE_MANDI_CROP,
    STATE_CONNECT_CROP,
    STATE_SET_TIME,
    STATE_DISEASE_DETECT,
) = range(12)

# ── Mandi API ─────────────────────────────────────────────────────
MANDI_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"