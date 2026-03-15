# 🌾 Agrithm — AI Farming Assistant Bot

<div align="center">

![Agrithm](https://img.shields.io/badge/Agrithm-AI%20Farming%20Assistant-2d6a27?style=for-the-badge&logo=leaf&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat-square&logo=telegram&logoColor=white)
![Dhenu2](https://img.shields.io/badge/LLM-Dhenu2%20Farming-2d6a27?style=flat-square&logo=huggingface&logoColor=white)
![GoogleTranslate](https://img.shields.io/badge/Translation-Google%20Translate-4285F4?style=flat-square&logo=google&logoColor=white)
![Whisper](https://img.shields.io/badge/STT-OpenAI%20Whisper-412991?style=flat-square&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**A multilingual Telegram bot that gives Indian farmers AI-powered farming advice,
daily agri-news alerts, and voice interaction — in their own language.**

[Report Bug](https://github.com/Madhavan1408/agrithm/issues) · [Request Feature](https://github.com/Madhavan1408/agrithm/issues)

</div>

---

## 📌 Table of Contents

- [What It Does](#-what-it-does)
- [Voice Pipeline](#-voice-pipeline)
- [Text Pipeline](#-text-pipeline)
- [Features](#-features)
- [Supported Languages](#-supported-languages)
- [Tech Stack](#-tech-stack)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Bot](#-running-the-bot)
- [Bot Commands](#-bot-commands)
- [Onboarding Flow](#-onboarding-flow)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Acknowledgements](#-acknowledgements)
- [License](#-license)

---

## 🤖 What It Does

Agrithm is a **Telegram bot** that acts as a personal farming advisor for Indian smallholder farmers. A farmer sends a voice note or typed message in their native language (Tamil, Hindi, Telugu, etc.), and the bot replies with practical farming advice — both as **text and audio** — in the same language.

Behind the scenes it uses:
- **Dhenu2** (farming-specific LLM via Ollama) for agricultural intelligence
- **OpenAI Whisper** for converting voice notes to text
- **Google Translate** (via `deep-translator`) for bidirectional translation
- **gTTS** for converting the reply back to voice
- **schedule** for pushing daily agri-news alerts at farmer-chosen times

---

## 🎙️ Voice Pipeline

```
Farmer sends voice note (OGG)
        ↓
  Download OGG file from Telegram
        ↓
  ffmpeg: OGG → WAV (16kHz mono)
        ↓
  Whisper (base): WAV → native language text
  e.g. "தக்காளிக்கு சிறந்த உரம் எது?"
        ↓
  Google Translate: native lang → English
  e.g. "What is the best fertilizer for tomatoes?"
        ↓
  Dhenu2 (via Ollama): generates English farming advice
        ↓
  Google Translate: English → native lang
  e.g. "தக்காளிக்கு DAP மற்றும் NPK உரம் சிறந்தது..."
        ↓
  gTTS: native text → MP3 voice file
        ↓
  Bot sends: text reply + voice reply to farmer
```

> All blocking steps (ffmpeg, Whisper, translation, Dhenu2, TTS) run in a **ThreadPoolExecutor** so they never freeze the async Telegram event loop.

---

## 💬 Text Pipeline

```
Farmer types message (any language)
        ↓
  Google Translate: native lang → English
        ↓
  Dhenu2 (via Ollama): English farming advice
        ↓
  Google Translate: English → native lang
        ↓
  gTTS: native text → MP3
        ↓
  Bot sends: text reply + voice reply
```

---

## ✨ Features

| Feature | Detail |
|---|---|
| 🎤 Voice input | Farmer speaks in their language — Whisper transcribes it |
| 🔊 Voice output | Every reply is also sent as a voice note via gTTS |
| 🌐 10 languages | Hindi, Tamil, Telugu, Kannada, Bengali, Marathi, Gujarati, Punjabi, Odia, English |
| 🤖 Dhenu2 LLM | Farming-specific model — crop advice, soil, pests, government schemes |
| 📰 Daily news alerts | Agri news delivered at 2 farmer-chosen times per day |
| 📍 Location-aware | Farmer's district/village personalises advice and news |
| 💾 Persistent profiles | Farmer preferences saved to `farmer_data.json` across restarts |
| 🔧 /debug command | One-command diagnosis of ffmpeg, Whisper, Ollama, and translation |
| 🧪 /testvoice command | Tests the full translation pipeline end-to-end |
| ♻️ Graceful fallbacks | Every error path sends a user-visible message — no blank screens |

---

## 🌐 Supported Languages

| Language | Code | TTS | Whisper STT |
|---|---|---|---|
| हिंदी (Hindi) | `hi` | ✅ | ✅ |
| தமிழ் (Tamil) | `ta` | ✅ | ✅ |
| తెలుగు (Telugu) | `te` | ✅ | ✅ |
| ಕನ್ನಡ (Kannada) | `kn` | ✅ | ✅ |
| বাংলা (Bengali) | `bn` | ✅ | ✅ |
| मराठी (Marathi) | `mr` | ✅ | ✅ |
| ગુજરાતી (Gujarati) | `gu` | ✅ | ✅ |
| ਪੰਜਾਬੀ (Punjabi) | `pa` | ✅ | ✅ |
| ଓଡ଼ିଆ (Odia) | `or` | ✅ | ❌ (text only) |
| English | `en` | ✅ | ✅ |

---

## 🛠️ Tech Stack

| Component | Technology |
|---|---|
| **Bot Framework** | `python-telegram-bot` v21 |
| **Farming LLM** | Dhenu2 (`dhenu2-farming:latest`) via Ollama REST API |
| **Speech-to-Text** | OpenAI Whisper (`base` model) |
| **Audio Conversion** | ffmpeg (OGG → WAV 16kHz mono) |
| **Translation** | Google Translate via `deep-translator` |
| **Text-to-Speech** | gTTS (Google Text-to-Speech) |
| **News Feed** | apitube.io News API (falls back to Dhenu2 if unavailable) |
| **Scheduling** | `schedule` library (daily alerts at farmer-set times) |
| **Async Execution** | `asyncio` + `ThreadPoolExecutor` (4 workers) |
| **Storage** | `farmer_data.json` (local JSON, persistent across restarts) |
| **Geolocation** | Nominatim (OpenStreetMap) reverse geocoding |

---

## ⚙️ Prerequisites

### 1. Python 3.10+
```bash
python --version
```

### 2. ffmpeg
Required to convert Telegram voice notes (OGG) to WAV for Whisper.
```bash
# Ubuntu / Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows — download from https://ffmpeg.org/download.html

# Verify
ffmpeg -version
```

### 3. Ollama + Dhenu2 model
```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Start Ollama server
ollama serve

# Pull Dhenu2 (in a new terminal)
ollama pull dhenu2-farming:latest
```

---

## 📦 Installation

```bash
# 1. Clone the repo
git clone https://github.com/Madhavan1408/agrithm.git
cd agrithm

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install python-telegram-bot gtts deep-translator requests schedule openai-whisper
```

---

## 🔧 Configuration

Open `bot.py` and update the `CONFIG` section at the top:

```python
BOT_TOKEN          = "your_telegram_bot_token"     # from @BotFather on Telegram
OLLAMA_URL         = "http://localhost:11434"       # Ollama server (default)
DHENU_MODEL        = "dhenu2-farming:latest"        # Ollama model name
NEWS_API_KEY       = "your_apitube_key"             # optional — apitube.io
WHISPER_MODEL_SIZE = "base"                         # tiny | base | small | medium
```

**Get a bot token:** Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → copy the token.

**NEWS_API_KEY is optional.** If not set, the bot asks Dhenu2 to generate a daily agri bulletin instead.

**Whisper model sizes** (trade-off between speed and accuracy):

| Model | Size | Speed | Accuracy |
|---|---|---|---|
| `tiny` | 75 MB | Fastest | Basic |
| `base` | 142 MB | Fast | Good ← recommended |
| `small` | 466 MB | Medium | Better |
| `medium` | 1.5 GB | Slow | Best |

---

## ▶️ Running the Bot

```bash
# Terminal 1 — keep Ollama running
ollama serve

# Terminal 2 — start the bot
python bot.py
```

Expected startup output:
```
============================================================
🌾  Agrithm Bot — Starting (TRANSLATION FIXED VERSION)
    Model  : dhenu2-farming:latest
    Ollama : http://localhost:11434
    Whisper: base
    Farmers: 0
    ✅ Ollama running | Models: ['dhenu2-farming:latest']
    ✅ Translation working: 'Hello farmer' → 'नमस्ते किसान'
============================================================
✅ Bot running — Ctrl+C to stop
```

Whisper loads in the background (~30 seconds). Text queries work immediately. Voice queries work once Whisper finishes loading.

---

## 📋 Bot Commands

| Command | Description |
|---|---|
| `/start` | Set up farmer profile (language → location → alert times) |
| `/news` | Fetch and send latest agricultural news right now |
| `/settings` | View your current language, location, and alert times |
| `/status` | Check Ollama, Whisper, and Google Translate status |
| `/debug` | Full diagnosis — ffmpeg, Whisper, Ollama, translation (both directions) |
| `/testvoice` | Test the complete translation pipeline with a sample question |
| `/help` | Show all available commands |

After setup, farmers can simply **type** or **send a voice note** — no command needed.

---

## 👨‍🌾 Onboarding Flow

When a new farmer runs `/start`:

```
Step 1 — Language selection
         10-language inline keyboard (Hindi, Tamil, Telugu, Kannada, etc.)
              ↓
Step 2 — Location
         Share GPS (auto reverse-geocoded via Nominatim)
         OR type village/district name
              ↓
Step 3 — Morning alert time
         Choose from: 5 AM, 6 AM, 7 AM, 8 AM, 12 PM
              ↓
Step 4 — Evening alert time
         Choose from: 12 PM, 4 PM, 6 PM, 7 PM, 9 PM
              ↓
Step 5 — Profile saved
         farmer_data.json updated
         Daily news schedule registered
```

Returning farmers skip onboarding and go straight to the assistant.

---

## 📁 Project Structure

```
agrithm/
├── bot.py                  # Entire bot — all logic in one file
├── farmer_data.json        # Auto-created on first /start — stores all farmer profiles
├── requirements.txt        # Python dependencies
└── README.md
```

### Key sections inside `bot.py`

| Section | Purpose |
|---|---|
| `CONFIG` | Token, Ollama URL, model name, API keys, Whisper size |
| `LANGUAGE CONFIGURATION` | Lang codes, TTS langs, Whisper map, multilingual UI messages |
| `PERSISTENT STORAGE` | `load_data()` / `save_data()` for `farmer_data.json` |
| `TRANSLATION` | `to_farmer_lang()` (EN→native) and `from_farmer_lang()` (native→EN) |
| `TEXT-TO-SPEECH` | `text_to_voice()` — gTTS MP3 generation with text cleanup |
| `OGG → WAV` | `_convert_ogg_to_wav_sync()` — ffmpeg subprocess in executor |
| `WHISPER` | `_transcribe_sync()` — blocking Whisper call in executor |
| `DHENU2` | `_query_dhenu2_sync()` / `query_dhenu2()` — Ollama REST API |
| `NEWS` | `fetch_agri_news()`, `format_news()`, `send_scheduled_news()` |
| `CORE PIPELINE` | `process_and_respond()` — 5-step translation + LLM + TTS pipeline |
| `HANDLERS` | `handle_text_query()` and `handle_voice_query()` |
| `ONBOARDING` | `start()`, `language_selected()`, `location_received()`, `time1/2_selected()` |
| `COMMANDS` | `/news`, `/status`, `/debug`, `/testvoice`, `/settings`, `/help` |
| `MAIN` | App build, handler registration, scheduler thread, polling start |

---

## 🔧 Troubleshooting

Run `/debug` inside the bot for instant diagnosis. Manual checks:

**Voice notes not working**
```bash
ffmpeg -version          # must show version info
sudo apt install ffmpeg  # if not found
```

**"Whisper still loading" message**
Wait 30 seconds after startup. Whisper loads in the background. Type `/status` to check.

**Dhenu2 not responding**
```bash
ollama serve                           # make sure Ollama is running
ollama list                            # check if dhenu2-farming:latest is there
ollama pull dhenu2-farming:latest      # pull if missing
```

**Translation not working**
```bash
pip install deep-translator
```

**Whisper fails to load**
```bash
pip install openai-whisper
pip install torch                      # required by Whisper
```

**Bot registered farmers not getting scheduled news**
Check that `farmer_data.json` exists and contains valid `alert_times` entries. Run `/settings` to verify.

---

## 🙏 Acknowledgements

- **Telugu LLM Labs** — for [Dhenu2](https://huggingface.co/Telugu-LLM-Labs/Dhenu2-8B-latest), the farming-specific LLM powering all advisory
- **OpenAI** — for Whisper, enabling accurate Indian-language speech recognition
- **Google** — for the Translate API via `deep-translator`
- **Ollama** — for simple local LLM inference
- **python-telegram-bot** — for the async bot framework
- **apitube.io** — for the agricultural news API

---

## 📄 License

MIT License — see [`LICENSE`](LICENSE) for details.

---

<div align="center">

Built with ❤️ for Indian farmers by **Madhavan S**
B.E. Artificial Intelligence Engineering | Saveetha School of Engineering, Chennai

[![GitHub](https://img.shields.io/badge/GitHub-Madhavan1408-181717?style=flat-square&logo=github)](https://github.com/Madhavan1408)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-14maddy-FFD21E?style=flat-square&logo=huggingface&logoColor=black)](https://huggingface.co/14maddy)

*"Technology is most powerful when it reaches those who need it most."*

</div>
