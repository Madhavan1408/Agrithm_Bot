# 🌾 Agrithm — Algorithmic Intelligence for Indian Agriculture

<div align="center">

![Agrithm Banner](https://img.shields.io/badge/Agrithm-AI%20for%20Agriculture-2d6a27?style=for-the-badge&logo=leaf&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?style=flat-square&logo=fastapi&logoColor=white)
![HuggingFace](https://img.shields.io/badge/HuggingFace-Spaces-FFD21E?style=flat-square&logo=huggingface&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange?style=flat-square)

**Empowering 140 million Indian smallholder farmers with AI-driven price intelligence,
multilingual voice advisory, and real-time market access — built for the last mile.**

[Live Demo](https://huggingface.co/spaces/14maddy/Agri_llm) · [GitHub](https://github.com/Madhavan1408) · [Report Bug](https://github.com/Madhavan1408/agrithm/issues) · [Request Feature](https://github.com/Madhavan1408/agrithm/issues)

</div>

---

## 📌 Table of Contents

- [About Agrithm](#-about-agrithm)
- [The Problem](#-the-problem)
- [Our Solution](#-our-solution)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [ML Pipeline](#-ml-pipeline)
- [Dataset](#-dataset)
- [Model Details](#-model-details)
- [API Reference](#-api-reference)
- [Deployment](#-deployment)
- [Impact & Metrics](#-impact--metrics)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Acknowledgements](#-acknowledgements)
- [License](#-license)

---

## 🌱 About Agrithm

Agrithm is an open-source, AI-powered agricultural intelligence platform designed specifically for Indian smallholder farmers. It bridges the critical information gap between farmers and markets through:

- **Multilingual voice interaction** — no reading, typing, or app navigation required
- **Crop price forecasting** — ML-driven 7–30 day price predictions across Tamil Nadu and Andhra Pradesh mandis
- **WhatsApp-first delivery** — works on basic Android devices over 2G connectivity
- **5-language support** — Tamil, Telugu, Hindi, Kannada, English

> Built as a submission for the **ACM × IBM Hackathon 2026** at Jain University (April 4, 2026).

---

## ❗ The Problem

Indian agriculture employs **58% of the rural workforce**, yet smallholder farmers — who make up **86% of all farm holdings** — consistently operate without access to timely, reliable, or personalized market information.

| Pain Point | Impact |
|---|---|
| Price information asymmetry at mandis | Farmers under-sell by 20–40% below fair market value |
| English-only advisory services | Inaccessible to 400M+ vernacular-language speakers |
| No data-driven seasonal planning | Cyclical income shocks from market oversupply |
| App-dependent solutions | Excludes farmers without smartphone literacy |

**Estimated annual loss from post-harvest price information gaps: ₹6,500 Crore**

---

## 💡 Our Solution

Agrithm delivers four interconnected capabilities:

```
┌─────────────────────────────────────────────────────┐
│                    AGRITHM PLATFORM                 │
│                                                     │
│  1. Price Intelligence  →  XGBoost forecasting      │
│  2. Voice Assistant     →  STT + LLM + TTS          │
│  3. Multilingual NLP    →  IndicTrans2 translation  │
│  4. WhatsApp Interface  →  Twilio API delivery      │
└─────────────────────────────────────────────────────┘
```

Farmers simply **send a voice message in their language** to a WhatsApp number and receive actionable price predictions, crop recommendations, and mandi routing — all spoken back in their language.

---

## ✨ Key Features

### 🔮 Price Intelligence Engine
- XGBoost + multi-output regression for crop price prediction
- 7-day and 30-day price forecasting per crop per district
- Covers Tamil Nadu and Andhra Pradesh mandi data
- Pivot-transformed dataset with engineered seasonal features

### 🎙️ Multilingual Voice Assistant
- **Speech-to-Text**: Faster-Whisper (large-v2) for accurate Indian-accented speech
- **Language Model**: QLoRA fine-tuned TinyLlama / Phi-3-mini on agricultural domain data
- **Translation**: IndicTrans2 (AI4Bharat) for 5 Indian languages
- **Text-to-Speech**: gTTS for natural voice responses

### 📱 Zero-App Accessibility
- WhatsApp-based interaction via Twilio API
- No app download, no account creation required
- Telegram bot alternative with location-based personalization
- Works on 2G/3G connectivity

### 🌐 Offline Resilience
- Local Ollama-based inference for intermittent connectivity zones
- Core price data cached for offline querying
- Lightweight model variants for low-resource environments

---

## 🏗️ System Architecture

```
                        FARMER (WhatsApp / Telegram)
                               │
                    ┌──────────▼──────────┐
                    │   Twilio / Bot API  │  ← Message Gateway
                    └──────────┬──────────┘
                               │ Voice / Text Message
                    ┌──────────▼──────────┐
                    │    FastAPI Backend  │  ← Node.js / FastAPI
                    └──────┬──────┬───────┘
                           │      │
          ┌────────────────▼──┐  ┌▼────────────────────┐
          │  Voice Pipeline   │  │  Price Intelligence  │
          │                   │  │                      │
          │  Faster-Whisper   │  │  XGBoost Forecaster  │
          │       STT         │  │  Multi-output Reg.   │
          │        ↓          │  │  District-level      │
          │  IndicTrans2      │  │  Crop Price Pred.    │
          │  (→ English)      │  └──────────────────────┘
          │        ↓          │
          │  Fine-tuned LLM   │  ← TinyLlama / Phi-3-mini
          │  (QLoRA AgriBot)  │      (QLoRA, 4-bit)
          │        ↓          │
          │  IndicTrans2      │
          │  (→ Native Lang)  │
          │        ↓          │
          │  gTTS Voice Out   │
          └───────────────────┘
                    │
          ┌─────────▼─────────┐
          │   Voice Response  │  → Delivered via WhatsApp
          │   to Farmer       │
          └───────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **AI / ML Core** | XGBoost, scikit-learn, TinyLlama, Phi-3-mini, QLoRA (4-bit) |
| **Speech Processing** | Faster-Whisper (large-v2), gTTS, Google Speech Recognition |
| **Translation** | IndicTrans2 (AI4Bharat), 5-language multilingual pipeline |
| **Backend** | FastAPI, Node.js, REST APIs |
| **Bot Interfaces** | Twilio (WhatsApp), aiogram (Telegram), python-telegram-bot |
| **ML Training** | Google Colab, Kaggle (T4 GPU), PEFT, bitsandbytes |
| **Model Serving** | Ollama (local), HuggingFace Inference API, ngrok |
| **Deployment** | HuggingFace Spaces (Gradio), Docker (planned) |
| **IBM Integration** | IBM watsonx.ai, watsonx Assistant |
| **Data** | pandas, numpy, Tamil Nadu mandi dataset (synthetic + real) |

---

## 📁 Project Structure

```
agrithm/
├── 📂 core/
│   ├── price_engine/
│   │   ├── train_model.py          # XGBoost training pipeline
│   │   ├── predict.py              # Price prediction inference
│   │   ├── data_engineering.py     # Pivot transforms, feature eng.
│   │   └── models/                 # Saved model artifacts
│   ├── voice_pipeline/
│   │   ├── stt.py                  # Faster-Whisper STT
│   │   ├── tts.py                  # gTTS text-to-speech
│   │   └── translate.py            # IndicTrans2 wrapper
│   └── llm/
│       ├── finetune_qlora.py       # QLoRA fine-tuning script
│       ├── inference.py            # LLM inference handler
│       └── prompts/                # Prompt templates (5 languages)
│
├── 📂 bots/
│   ├── whatsapp_bot/
│   │   ├── app.py                  # Twilio WhatsApp handler
│   │   └── webhook.py              # FastAPI webhook endpoint
│   └── telegram_bot/
│       ├── bot.py                  # aiogram Telegram bot
│       └── handlers.py             # Command + voice handlers
│
├── 📂 api/
│   ├── main.py                     # FastAPI application entry
│   ├── routes/
│   │   ├── price.py                # Price prediction endpoints
│   │   ├── advisory.py             # Crop advisory endpoints
│   │   └── voice.py                # Voice processing endpoints
│   └── schemas/                    # Pydantic request/response models
│
├── 📂 data/
│   ├── raw/                        # Raw mandi price data
│   ├── processed/                  # Cleaned, pivot-transformed data
│   ├── synthetic/                  # Synthetic Tamil Nadu dataset
│   └── multilingual_dataset/       # 1,625-entry fine-tuning dataset
│
├── 📂 notebooks/
│   ├── 01_data_engineering.ipynb   # Data pipeline exploration
│   ├── 02_ml_training.ipynb        # Model training walkthrough
│   ├── 03_qlora_finetune.ipynb     # LLM fine-tuning notebook
│   └── 04_evaluation.ipynb         # Model evaluation & metrics
│
├── 📂 gradio_app/
│   └── app.py                      # HuggingFace Spaces demo
│
├── 📂 docs/
│   ├── architecture.md
│   ├── api_reference.md
│   └── deployment.md
│
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── docker-compose.yml
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Git
- CUDA-compatible GPU (recommended for LLM inference)
- Ollama (for local model serving)
- Twilio account (for WhatsApp integration)

### 1. Clone the Repository

```bash
git clone https://github.com/Madhavan1408/agrithm.git
cd agrithm
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For development:
```bash
pip install -r requirements-dev.txt
```

### 4. Environment Setup

```bash
cp .env.example .env
# Edit .env with your API keys (see Configuration section)
```

### 5. Download Models

```bash
# Pull base LLM via Ollama
ollama pull llama3.2

# Or use our fine-tuned model from HuggingFace
python scripts/download_models.py
```

### 6. Run the Application

```bash
# Start FastAPI backend
uvicorn api.main:app --reload --port 8000

# In a separate terminal — start Telegram bot
python bots/telegram_bot/bot.py

# For WhatsApp webhook (requires ngrok)
ngrok http 8000
# Update Twilio webhook URL with your ngrok URL
```

---

## ⚙️ Configuration

Create a `.env` file from `.env.example`:

```env
# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# HuggingFace
HF_TOKEN=your_hf_token
HF_MODEL_REPO=14maddy/Agri_llm

# IBM watsonx (optional)
WATSONX_API_KEY=your_watsonx_key
WATSONX_PROJECT_ID=your_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# App
DEBUG=False
LOG_LEVEL=INFO
```

---

## 📖 Usage

### Via WhatsApp

Send a voice message or text to the Agrithm WhatsApp number:

```
"நாளை தக்காளி விலை என்ன?" (Tamil: "What is the tomato price tomorrow?")
"कल टमाटर का भाव क्या होगा?" (Hindi: "What will be the tomato rate tomorrow?")
"రేపు టమాటా ధర ఎంత?" (Telugu: "What is the tomato price tomorrow?")
```

### Via Telegram Bot

```
/start          — Initialize bot, set language preference
/price <crop>   — Get price prediction for a crop
/advisory       — Get personalized farming advisory
/mandi          — Find nearest mandi with current prices
/help           — List all commands
```

### Via API

```bash
# Get price prediction
curl -X POST http://localhost:8000/api/price/predict \
  -H "Content-Type: application/json" \
  -d '{
    "crop": "tomato",
    "district": "Chennai",
    "state": "Tamil Nadu",
    "days_ahead": 7
  }'

# Get crop advisory
curl -X POST http://localhost:8000/api/advisory \
  -H "Content-Type: application/json" \
  -d '{
    "query": "When should I sell my onions?",
    "language": "ta",
    "location": "Coimbatore"
  }'
```

---

## 🤖 ML Pipeline

### Price Prediction Pipeline

```python
# 1. Data Ingestion
raw_data = load_mandi_data("data/raw/tamilnadu_mandis.csv")

# 2. Feature Engineering
df = engineer_features(raw_data)
# → Pivot transformation: (date, crop, district) → wide format
# → Lag features: price_lag_7, price_lag_30
# → Seasonal features: month, week_of_year, harvest_season

# 3. Model Training
from sklearn.multioutput import MultiOutputRegressor
from xgboost import XGBRegressor

model = MultiOutputRegressor(
    XGBRegressor(n_estimators=300, max_depth=6, learning_rate=0.05)
)
model.fit(X_train, y_train)  # y = [price_7d, price_30d]

# 4. Inference
predictions = model.predict([[crop_encoded, district_encoded, ...]])
# → Returns: {"7_day_price": 45.2, "30_day_price": 52.8}
```

### Voice Pipeline

```python
# 1. Receive voice message (WhatsApp/Telegram)
audio_bytes = receive_voice_message(message)

# 2. Speech-to-Text
from faster_whisper import WhisperModel
model = WhisperModel("large-v2", device="cuda")
segments, info = model.transcribe(audio_bytes)
text = " ".join([s.text for s in segments])
detected_lang = info.language  # "ta", "te", "hi", "kn", "en"

# 3. Translate to English (if needed)
if detected_lang != "en":
    english_text = indictrans2_translate(text, src=detected_lang, tgt="en")

# 4. LLM Inference
response = ollama_generate(model="agrithm-bot", prompt=english_text)

# 5. Translate response back
if detected_lang != "en":
    native_response = indictrans2_translate(response, src="en", tgt=detected_lang)

# 6. Text-to-Speech
from gtts import gTTS
tts = gTTS(text=native_response, lang=detected_lang)
tts.save("response.mp3")
```

---

## 📊 Dataset

### Mandi Price Dataset (Tamil Nadu)
- **Size**: Synthetic + real mandi records covering 32 districts
- **Crops**: 28 major crops (tomato, onion, rice, sugarcane, cotton, etc.)
- **Features**: Date, district, crop, modal price, min price, max price, volume
- **Time range**: 2019–2024 (synthetic extended to 2025)
- **Source**: Agmarknet API + synthetic augmentation

### LLM Fine-tuning Dataset
- **Size**: 1,625 entries
- **Languages**: English, Tamil, Telugu, Hindi, Kannada
- **Domains**: Crop pricing, pest management, weather advisory, soil health, government schemes
- **Format**: Instruction-tuning format (system prompt + user query + assistant response)
- **HuggingFace**: [14maddy/Agri_llm](https://huggingface.co/14maddy/Agri_llm)

---

## 🧠 Model Details

| Model | Base | Method | Parameters | Purpose |
|---|---|---|---|---|
| Agrithm-LLM-v1 | TinyLlama-1.1B | QLoRA (4-bit) | 1.1B | Agricultural Q&A |
| Agrithm-LLM-v2 | Phi-3-mini-4k | QLoRA (4-bit) | 3.8B | Enhanced reasoning |
| Price-XGB | XGBoost | Multi-output | — | Price forecasting |
| STT | Faster-Whisper large-v2 | — | 1.5B | Speech recognition |
| Translation | IndicTrans2 | — | 200M | 5-language translation |

**Training Configuration (QLoRA):**
```python
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)
```

---

## 📡 API Reference

### `POST /api/price/predict`
Predict crop price for a given district and time horizon.

**Request:**
```json
{
  "crop": "tomato",
  "district": "Chennai",
  "state": "Tamil Nadu",
  "days_ahead": 7
}
```

**Response:**
```json
{
  "crop": "tomato",
  "district": "Chennai",
  "predicted_price_7d": 45.20,
  "predicted_price_30d": 52.80,
  "confidence": 0.84,
  "unit": "₹/kg",
  "timestamp": "2026-04-04T10:30:00Z"
}
```

### `POST /api/advisory`
Get multilingual agricultural advisory.

**Request:**
```json
{
  "query": "When should I sell my onions?",
  "language": "ta",
  "location": "Coimbatore",
  "crop": "onion"
}
```

**Response:**
```json
{
  "response_text": "...",
  "response_audio_url": "...",
  "language": "ta",
  "sources": ["price_model", "llm_advisory"]
}
```

Full API documentation: [`docs/api_reference.md`](docs/api_reference.md)

---

## 🚢 Deployment

### HuggingFace Spaces (Demo)

The Gradio demo is live at: [huggingface.co/spaces/14maddy/Agri_llm](https://huggingface.co/spaces/14maddy/Agri_llm)

### Local Deployment with Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull and run model
ollama run agrithm-bot

# Start API
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

### Docker (Coming Soon)

```bash
docker-compose up --build
```

### WhatsApp Production Setup

1. Create a Twilio account at [twilio.com](https://twilio.com)
2. Enable WhatsApp sandbox
3. Deploy API to a public server (Railway, Render, or EC2)
4. Set Twilio webhook to: `https://your-domain.com/webhook/whatsapp`

---

## 📈 Impact & Metrics

| Metric | Value |
|---|---|
| Target farmer segment | 140M+ smallholder farmers |
| Annual price loss addressable | ₹6,500 Crore |
| Languages supported | 5 (Tamil, Telugu, Hindi, Kannada, English) |
| Rural language speakers covered | 400M+ |
| Districts covered (price data) | 32 (Tamil Nadu) + 13 (Andhra Pradesh) |
| Crops in price model | 28 major crops |
| Fine-tuning dataset size | 1,625 entries |
| WhatsApp penetration (rural India) | ~65% of mobile users |
| Device requirement | Basic Android, 2G connectivity |

---

## 🗺️ Roadmap

### Phase 1 — Core MVP (Current)
- [x] XGBoost price prediction pipeline
- [x] Faster-Whisper STT integration
- [x] QLoRA fine-tuned TinyLlama
- [x] IndicTrans2 multilingual translation
- [x] WhatsApp bot (Twilio)
- [x] Telegram bot (aiogram)
- [x] HuggingFace Spaces demo
- [x] FastAPI backend

### Phase 2 — Production Ready (Q3 2026)
- [ ] Expand to 10+ states with real mandi API integration
- [ ] IBM watsonx.ai full integration
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Real-time Agmarknet data ingestion
- [ ] User feedback collection system

### Phase 3 — Scale (Q4 2026+)
- [ ] Expand to 28 states
- [ ] Soil health analysis via image input
- [ ] Pest/disease detection (computer vision)
- [ ] Integration with PM-Kisan and e-NAM portals
- [ ] Farmer cooperative network features
- [ ] Dialect-specific model fine-tuning

---

## 🤝 Contributing

Contributions are welcome — especially from developers with agricultural domain knowledge, native speakers of Indian languages, and ML engineers with low-resource NLP experience.

### How to Contribute

1. Fork the repository
2. Create your feature branch: `git checkout -b feature/your-feature-name`
3. Commit your changes: `git commit -m 'Add: meaningful description'`
4. Push to the branch: `git push origin feature/your-feature-name`
5. Open a Pull Request

### Areas Where We Need Help

- 🌐 **Translation quality**: Native speakers to verify IndicTrans2 output accuracy
- 📊 **Data collection**: Real mandi price data from additional states
- 🤖 **Model improvement**: Better fine-tuning datasets, RLHF, DPO
- 🧪 **Testing**: Unit tests, integration tests, field testing with real farmers
- 📱 **IVR integration**: IVRS-based interaction for feature phone users

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) for our code of conduct and detailed contribution guidelines.

---

## 🙏 Acknowledgements

- **AI4Bharat** — for IndicTrans2 and the broader Indic NLP ecosystem
- **Sarvam AI** — for inspiration in building for Bharat-first voice AI
- **HuggingFace** — for open model hosting and the transformers library
- **Agmarknet (DACFW, GoI)** — for agricultural market price data
- **Ollama** — for making local LLM inference accessible
- **ACM × IBM Hackathon 2026** — for the platform to build and present Agrithm

---

## 📄 License

This project is licensed under the **MIT License** — see the [`LICENSE`](LICENSE) file for details.

---

<div align="center">

Built with ❤️ for Indian farmers by **Madhavan S**
B.E. Artificial Intelligence Engineering | Saveetha School of Engineering, Chennai

[![GitHub](https://img.shields.io/badge/GitHub-Madhavan1408-181717?style=flat-square&logo=github)](https://github.com/Madhavan1408)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-14maddy-FFD21E?style=flat-square&logo=huggingface&logoColor=black)](https://huggingface.co/14maddy)

*"Technology is most powerful when it reaches those who need it most."*

</div>
