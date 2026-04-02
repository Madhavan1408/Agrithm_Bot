"""
agrithm_config.py  — v3  (C2 / C3 fixed)
─────────────────────────────────────────
Single source of truth for all Agrithm settings.

FIXES:
  C2 / C3: OLLAMA_URL and OLLAMA_MODEL now read from env first.
           The v2 file still had the hardcoded ngrok URL on line 36
           because it appeared AFTER the comment that said it was fixed.
           This file removes that hardcoded assignment entirely.
           Both bot.py AND utils/rag.py import OLLAMA_URL from here,
           so there is now one source of truth and no split-brain.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY")       # reserved, not yet used
SARVAM_API_KEY = os.environ.get("SARVAM_API_KEY")
MANDI_API_KEY  = os.environ.get("MANDI_API_KEY")

# ── Validate required keys on startup ─────────────────────────────────
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN missing from .env")
if not SARVAM_API_KEY:
    raise ValueError("SARVAM_API_KEY missing from .env")

# ── LLM Backend ───────────────────────────────────────────────────────
# C2/C3 FIX: Read BOTH values from env — no hardcoded URL.
#
# To use a ngrok tunnel:   OLLAMA_URL=https://xxxx.ngrok-free.app
# To use localhost (default, no .env entry needed):
#                          OLLAMA_URL=http://localhost:11434
#
# Both bot.py and utils/rag.py import OLLAMA_URL from this module,
# so they always talk to the same endpoint.
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "dhenu2-farming:latest")

# ── Sarvam AI Models ──────────────────────────────────────────────────
STT_MODEL       = "saarika:v2.5"
TTS_MODEL       = "bulbul:v2"        # H4: unified — voice.py was using v1
TRANSLATE_MODEL = "mayura:v1"

# ── Embedding Model ───────────────────────────────────────────────────
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ── Paths ─────────────────────────────────────────────────────────────
# H5: Absolute paths derived from this file's location so the bot
#     works correctly regardless of which directory it is started from.
_CONFIG_DIR         = os.path.dirname(os.path.abspath(__file__))
VECTOR_STORE_PATH   = os.path.join(_CONFIG_DIR, "vector_store")
USER_PROFILES_PATH  = os.path.join(_CONFIG_DIR, "data", "user_profiles.json")
FARMER_NETWORK_PATH = os.path.join(_CONFIG_DIR, "data", "farmer_network.json")
AUDIO_TEMP_DIR      = os.path.join(_CONFIG_DIR, "audio_temp")

# ── RAG Settings ──────────────────────────────────────────────────────
TOP_K          = 3
MIN_SIMILARITY = 0.6

# ── Supported Languages ───────────────────────────────────────────────
LANGUAGES = {
    # ── South Indian ──────────────────────────────────────────────────
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
    # ── North Indian ──────────────────────────────────────────────────
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
    # ── East Indian ───────────────────────────────────────────────────
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

# ── Quick lookup helpers ───────────────────────────────────────────────
LANGUAGE_NAMES   = list(LANGUAGES.keys())
LANGUAGE_CODES   = {k: v["code"] for k, v in LANGUAGES.items()}
CODE_TO_LANGUAGE = {v["code"]: k for k, v in LANGUAGES.items()}

# ── Bot Conversation States ────────────────────────────────────────────
# 13 unique sequential integers — no gaps, no collisions.
(
    STATE_ONBOARD_LANG,      # 0
    STATE_ONBOARD_NAME,      # 1
    STATE_ONBOARD_CROP,      # 2
    STATE_ONBOARD_LOCATION,  # 3
    STATE_ONBOARD_TIME,      # 4  — M3 fix: now has a handler in bot.py
    STATE_ONBOARD_VILLAGE,   # 5
    STATE_MAIN_MENU,         # 6
    STATE_VOICE_QUERY,       # 7
    STATE_MANDI_CROP,        # 8
    STATE_CONNECT_CROP,      # 9  — reserved
    STATE_SET_TIME,          # 10
    STATE_DISEASE_DETECT,    # 11
    STATE_CHAT_ROOM,         # 12
) = range(13)

# ── Mandi API ─────────────────────────────────────────────────────────
MANDI_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"