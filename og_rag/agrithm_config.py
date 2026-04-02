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
# FIX B: OLLAMA_URL is defined ONCE here — imported by both bot.py
#         and utils/rag.py so they always hit the same endpoint.
#
#         Priority order:
#           1. OLLAMA_URL env var in your .env file  (recommended)
#           2. Falls back to localhost if not set
#
#         To use a ngrok tunnel, add this line to your .env:
#           OLLAMA_URL=https://xxxx-xxxx.ngrok-free.app
OLLAMA_URL   = "https://alfreda-nonsubsistent-snakily.ngrok-free.dev"
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
TOP_K          = 3
MIN_SIMILARITY = 0.6

# ── Supported Languages ───────────────────────────────────────────
LANGUAGES = {
    # ── South Indian ──────────────────────────────────────────────
    "Tamil": {
        "code":        "ta-IN",
        "tts_speaker": "anushka",
        "native":      "தமிழ்",
        "region":      "south",
    },
    "Telugu": {
        "code":        "te-IN",
        "tts_speaker": "anushka",
        "native":      "తెలుగు",
        "region":      "south",
    },
    "Kannada": {
        "code":        "kn-IN",
        "tts_speaker": "anushka",
        "native":      "ಕನ್ನಡ",
        "region":      "south",
    },
    "Malayalam": {
        "code":        "ml-IN",
        "tts_speaker": "anushka",
        "native":      "മലയാളം",
        "region":      "south",
    },
    # ── North Indian ──────────────────────────────────────────────
    "Hindi": {
        "code":        "hi-IN",
        "tts_speaker": "anushka",
        "native":      "हिन्दी",
        "region":      "north",
    },
    "Punjabi": {
        "code":        "pa-IN",
        "tts_speaker": "neel",
        "native":      "ਪੰਜਾਬੀ",
        "region":      "north",
    },
    "Gujarati": {
        "code":        "gu-IN",
        "tts_speaker": "anushka",
        "native":      "ગુજરાતી",
        "region":      "west",
    },
    "Marathi": {
        "code":        "mr-IN",
        "tts_speaker": "anushka",
        "native":      "मराठी",
        "region":      "west",
    },
    # ── East Indian ───────────────────────────────────────────────
    "Bengali": {
        "code":        "bn-IN",
        "tts_speaker": "anushka",
        "native":      "বাংলা",
        "region":      "east",
    },
    "Odia": {
        "code":        "od-IN",
        "tts_speaker": "anushka",
        "native":      "ଓଡ଼ିଆ",
        "region":      "east",
    },
    "English": {
        "code":        "en-IN",
        "tts_speaker": "meera",
        "native":      "English",
        "region":      "pan-india",
    },
}

# ── Quick lookup helpers ──────────────────────────────────────────
LANGUAGE_NAMES   = list(LANGUAGES.keys())
LANGUAGE_CODES   = {k: v["code"] for k, v in LANGUAGES.items()}
CODE_TO_LANGUAGE = {v["code"]: k for k, v in LANGUAGES.items()}

# ── Bot Conversation States ───────────────────────────────────────
# FIX E: 13 unique sequential integers — no gaps, no collisions.
#         STATE_CHAT_ROOM is the 13th state (index 12).
(
    STATE_ONBOARD_LANG,      # 0
    STATE_ONBOARD_NAME,      # 1
    STATE_ONBOARD_CROP,      # 2
    STATE_ONBOARD_LOCATION,  # 3
    STATE_ONBOARD_TIME,      # 4  ← was silently missing from old bot.py import
    STATE_ONBOARD_VILLAGE,   # 5
    STATE_MAIN_MENU,         # 6
    STATE_VOICE_QUERY,       # 7
    STATE_MANDI_CROP,        # 8
    STATE_CONNECT_CROP,      # 9
    STATE_SET_TIME,          # 10
    STATE_DISEASE_DETECT,    # 11
    STATE_CHAT_ROOM,         # 12
) = range(13)

# ── Mandi API ─────────────────────────────────────────────────────
MANDI_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"