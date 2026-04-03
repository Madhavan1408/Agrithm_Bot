"""
utils/crop_schedule.py  — v2 (multilingual)
────────────────────────────────────────────
Builds the Daily Crop Card and the LLM tip prompt for the Crop Journey feature.

Changes vs v1:
  • build_daily_card() now accepts `lang` parameter and returns
    all static strings in the farmer's chosen language.
  • _CARD_STRINGS contains translations for all 8 supported languages.
  • TTS text is also returned in the farmer's language.
  • build_daily_tip_prompt() now injects a language instruction so
    the Ollama AI tip is also returned in the correct language.
  • build_journey_start_message() accepts `lang` and is localised.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from utils.crop_journey import (
    CROP_LIFECYCLES,
    fertilizer_due_today,
    get_current_day,
    get_stage_for_day,
)

# ══════════════════════════════════════════════════════════════════
# LANGUAGE STRINGS FOR CARD LABELS
# ══════════════════════════════════════════════════════════════════

_CARD_STRINGS: dict[str, dict[str, str]] = {
    # ── Section headers ──────────────────────────────────────────
    "daily_card_header": {
        "English":   "🌾 Daily Crop Card",
        "Hindi":     "🌾 दैनिक फसल कार्ड",
        "Telugu":    "🌾 డైలీ క్రాప్ కార్డ్",
        "Tamil":     "🌾 தினசரி பயிர் அட்டை",
        "Kannada":   "🌾 ದೈನಂದಿನ ಬೆಳೆ ಕಾರ್ಡ್",
        "Malayalam": "🌾 ദൈനദിന വിള കാർഡ്",
        "Marathi":   "🌾 दैनिक पीक कार्ड",
        "Gujarati":  "🌾 દૈनિক ખેતી કાર્ડ",
    },
    "day_of": {
        "English":   "Day {day} of {total}",
        "Hindi":     "दिन {day} / {total}",
        "Telugu":    "రోజు {day} / {total}",
        "Tamil":     "நாள் {day} / {total}",
        "Kannada":   "ದಿನ {day} / {total}",
        "Malayalam": "ദിനം {day} / {total}",
        "Marathi":   "दिवस {day} / {total}",
        "Gujarati":  "દિવસ {day} / {total}",
    },
    "progress": {
        "English":   "Progress",
        "Hindi":     "प्रगति",
        "Telugu":    "పురోగతి",
        "Tamil":     "முன்னேற்றம்",
        "Kannada":   "ಪ್ರಗತಿ",
        "Malayalam": "പുരോഗതി",
        "Marathi":   "प्रगती",
        "Gujarati":  "પ્રગતિ",
    },
    "current_stage": {
        "English":   "Current Stage",
        "Hindi":     "वर्तमान चरण",
        "Telugu":    "ప్రస్తుత దశ",
        "Tamil":     "தற்போதைய நிலை",
        "Kannada":   "ಪ್ರಸ್ತುತ ಹಂತ",
        "Malayalam": "നിലവിലെ ഘട്ടം",
        "Marathi":   "सध्याचा टप्पा",
        "Gujarati":  "હાલનો તબક્કો",
    },
    "day_in_stage": {
        "English":   "Day {day_in} of {stage_total} in this stage",
        "Hindi":     "इस चरण में दिन {day_in} / {stage_total}",
        "Telugu":    "ఈ దశలో రోజు {day_in} / {stage_total}",
        "Tamil":     "இந்த நிலையில் நாள் {day_in} / {stage_total}",
        "Kannada":   "ಈ ಹಂತದಲ್ಲಿ ದಿನ {day_in} / {stage_total}",
        "Malayalam": "ഈ ഘട്ടത്തിൽ ദിനം {day_in} / {stage_total}",
        "Marathi":   "या टप्प्यात दिवस {day_in} / {stage_total}",
        "Gujarati":  "આ તબક્કામાં દિવસ {day_in} / {stage_total}",
    },
    "critical_stage_warning": {
        "English":   "⚠️ CRITICAL STAGE — Extra attention needed!",
        "Hindi":     "⚠️ महत्वपूर्ण चरण — विशेष ध्यान दें!",
        "Telugu":    "⚠️ క్రిటికల్ దశ — అదనపు శ్రద్ధ అవసరం!",
        "Tamil":     "⚠️ முக்கியமான நிலை — கூடுதல் கவனம் தேவை!",
        "Kannada":   "⚠️ ನಿರ್ಣಾಯಕ ಹಂತ — ಹೆಚ್ಚುವರಿ ಗಮನ ಬೇಕು!",
        "Malayalam": "⚠️ നിർണ്ണായക ഘട്ടം — അധിക ശ്രദ്ധ ആവശ്യം!",
        "Marathi":   "⚠️ महत्त्वाचा टप्पा — जास्त लक्ष द्या!",
        "Gujarati":  "⚠️ ક્રિટિકલ તબક્કો — વિશેષ ધ્યાન આપો!",
    },
    "todays_tasks": {
        "English":   "📋 Today's Tasks",
        "Hindi":     "📋 आज के काम",
        "Telugu":    "📋 ఈరోజు పనులు",
        "Tamil":     "📋 இன்றைய பணிகள்",
        "Kannada":   "📋 ಇಂದಿನ ಕಾರ್ಯಗಳು",
        "Malayalam": "📋 ഇന്നത്തെ ജോലികൾ",
        "Marathi":   "📋 आजची कामे",
        "Gujarati":  "📋 આજના કામ",
    },
    "dos": {
        "English":   "✅ Do's",
        "Hindi":     "✅ करें",
        "Telugu":    "✅ చేయవలసినవి",
        "Tamil":     "✅ செய்யவேண்டியவை",
        "Kannada":   "✅ ಮಾಡಬೇಕಾದವು",
        "Malayalam": "✅ ചെയ്യേണ്ടവ",
        "Marathi":   "✅ करायचे",
        "Gujarati":  "✅ કરવાનું",
    },
    "donts": {
        "English":   "❌ Don'ts",
        "Hindi":     "❌ न करें",
        "Telugu":    "❌ చేయకూడనివి",
        "Tamil":     "❌ செய்யக்கூடாதவை",
        "Kannada":   "❌ ಮಾಡಬಾರದವು",
        "Malayalam": "❌ ചെയ്യരുതാത്തവ",
        "Marathi":   "❌ करायचे नाही",
        "Gujarati":  "❌ ન કરવાનું",
    },
    "fertilizer_due": {
        "English":   "💊 Fertilizer Due Today",
        "Hindi":     "💊 आज खाद डालें",
        "Telugu":    "💊 ఈరోజు ఎరువు వేయాలి",
        "Tamil":     "💊 இன்று உரம் இடவும்",
        "Kannada":   "💊 ಇಂದು ಗೊಬ್ಬರ ಹಾಕಿ",
        "Malayalam": "💊 ഇന്ന് വളം ഇടേണ്ടതുണ്ട്",
        "Marathi":   "💊 आज खत द्या",
        "Gujarati":  "💊 આજ ખાતર આપો",
    },
    "product": {
        "English":   "Product",
        "Hindi":     "उत्पाद",
        "Telugu":    "ఉత్పత్తి",
        "Tamil":     "தயாரிப்பு",
        "Kannada":   "ಉತ್ಪನ್ನ",
        "Malayalam": "ഉൽപ്പന്നം",
        "Marathi":   "उत्पादन",
        "Gujarati":  "ઉત્પાદન",
    },
    "dose": {
        "English":   "Dose",
        "Hindi":     "मात्रा",
        "Telugu":    "మోతాదు",
        "Tamil":     "அளவு",
        "Kannada":   "ಪ್ರಮಾಣ",
        "Malayalam": "അളവ്",
        "Marathi":   "मात्रा",
        "Gujarati":  "માત્રા",
    },
    "method": {
        "English":   "Method",
        "Hindi":     "विधि",
        "Telugu":    "పద్ధతి",
        "Tamil":     "முறை",
        "Kannada":   "ವಿಧಾನ",
        "Malayalam": "രീതി",
        "Marathi":   "पद्धत",
        "Gujarati":  "પ્રક્રિયા",
    },
    "cost": {
        "English":   "Est. Cost",
        "Hindi":     "अनुमानित लागत",
        "Telugu":    "అంచనా ఖర్చు",
        "Tamil":     "மதிப்பீட்டு செலவு",
        "Kannada":   "ಅಂದಾಜು ವೆಚ್ಚ",
        "Malayalam": "ഏകദേശ ചെലവ്",
        "Marathi":   "अंदाजे खर्च",
        "Gujarati":  "અંદાજિત ખર્ચ",
    },
    "what_to_monitor": {
        "English":   "🔍 What to Monitor",
        "Hindi":     "🔍 क्या देखें",
        "Telugu":    "🔍 ఏమి పరిశీలించాలి",
        "Tamil":     "🔍 என்ன கண்காணிக்க வேண்டும்",
        "Kannada":   "🔍 ಏನನ್ನು ಗಮನಿಸಬೇಕು",
        "Malayalam": "🔍 എന്ത് നിരീക്ഷിക്കണം",
        "Marathi":   "🔍 काय बघायचे",
        "Gujarati":  "🔍 શું જોવાનું",
    },
    "ai_tip": {
        "English":   "🤖 AI Tip for Today",
        "Hindi":     "🤖 आज की AI सलाह",
        "Telugu":    "🤖 ఈరోజు AI చిట్కా",
        "Tamil":     "🤖 இன்றைய AI குறிப்பு",
        "Kannada":   "🤖 ಇಂದಿನ AI ಸಲಹೆ",
        "Malayalam": "🤖 ഇന്നത്തെ AI നുറുങ്ങ്",
        "Marathi":   "🤖 आजची AI टिप",
        "Gujarati":  "🤖 આજની AI ટિપ",
    },
    "next_stage_in": {
        "English":   "⏭ Next stage in {days} day(s)",
        "Hindi":     "⏭ अगला चरण {days} दिन में",
        "Telugu":    "⏭ తదుపరి దశ {days} రోజుల్లో",
        "Tamil":     "⏭ அடுத்த நிலை {days} நாளில்",
        "Kannada":   "⏭ ಮುಂದಿನ ಹಂತ {days} ದಿನದಲ್ಲಿ",
        "Malayalam": "⏭ അടുത്ത ഘട്ടം {days} ദിവസത്തിൽ",
        "Marathi":   "⏭ पुढील टप्पा {days} दिवसात",
        "Gujarati":  "⏭ આગળનો તબક્કો {days} દિવસમાં",
    },
    "harvest_in": {
        "English":   "🎉 Harvest in {days} day(s) — {date}",
        "Hindi":     "🎉 {days} दिन में कटाई — {date}",
        "Telugu":    "🎉 {days} రోజుల్లో కోత — {date}",
        "Tamil":     "🎉 {days} நாளில் அறுவடை — {date}",
        "Kannada":   "🎉 {days} ದಿನದಲ್ಲಿ ಕಟಾವು — {date}",
        "Malayalam": "🎉 {days} ദിവസത്തിൽ വിളവെടുക്കൽ — {date}",
        "Marathi":   "🎉 {days} दिवसात कापणी — {date}",
        "Gujarati":  "🎉 {days} દિવસમાં કાપણી — {date}",
    },
    "good_morning": {
        "English":   "Good morning, {name}!",
        "Hindi":     "सुप्रभात, {name}!",
        "Telugu":    "శుభోదయం, {name}!",
        "Tamil":     "காலை வணக்கம், {name}!",
        "Kannada":   "ಶುಭೋದಯ, {name}!",
        "Malayalam": "സുപ്രഭാതം, {name}!",
        "Marathi":   "सुप्रभात, {name}!",
        "Gujarati":  "સુપ્રભાત, {name}!",
    },
    "journey_started": {
        "English":   "🌱 Your {crop} journey has started!",
        "Hindi":     "🌱 आपकी {crop} की यात्रा शुरू हो गई!",
        "Telugu":    "🌱 మీ {crop} ప్రయాణం ప్రారంభమైంది!",
        "Tamil":     "🌱 உங்கள் {crop} பயணம் தொடங்கியது!",
        "Kannada":   "🌱 ನಿಮ್ಮ {crop} ಪ್ರಯಾಣ ಪ್ರಾರಂಭವಾಯಿತು!",
        "Malayalam": "🌱 നിങ്ങളുടെ {crop} യാത്ര ആരംഭിച്ചു!",
        "Marathi":   "🌱 तुमचा {crop} प्रवास सुरू झाला!",
        "Gujarati":  "🌱 તમારી {crop} યાત્રા શરૂ થઈ!",
    },
    "sow_date_label": {
        "English":   "Sow date",
        "Hindi":     "बुवाई तिथि",
        "Telugu":    "విత్తన తేదీ",
        "Tamil":     "விதைப்பு தேதி",
        "Kannada":   "ಬಿತ್ತನೆ ದಿನಾಂಕ",
        "Malayalam": "വിത്ത് തീയതി",
        "Marathi":   "पेरणी तारीख",
        "Gujarati":  "વાવણી તારીખ",
    },
    "harvest_date_label": {
        "English":   "Est. harvest",
        "Hindi":     "अनुमानित कटाई",
        "Telugu":    "అంచనా కోత",
        "Tamil":     "மதிப்பீட்டு அறுவடை",
        "Kannada":   "ಅಂದಾಜು ಕಟಾವು",
        "Malayalam": "ഏകദേശ വിളവെടുക്കൽ",
        "Marathi":   "अंदाजे कापणी",
        "Gujarati":  "અંદાજiત કાપણી",
    },
    "duration_label": {
        "English":   "Duration",
        "Hindi":     "अवधि",
        "Telugu":    "వ్యవధి",
        "Tamil":     "கால அளவு",
        "Kannada":   "ಅವಧಿ",
        "Malayalam": "ദൈർഘ്യം",
        "Marathi":   "कालावधी",
        "Gujarati":  "અવધિ",
    },
    "days": {
        "English":   "days",
        "Hindi":     "दिन",
        "Telugu":    "రోజులు",
        "Tamil":     "நாட்கள்",
        "Kannada":   "ದಿನಗಳು",
        "Malayalam": "ദിവസങ്ങൾ",
        "Marathi":   "दिवस",
        "Gujarati":  "દિવસ",
    },
    "daily_alarm": {
        "English":   "Daily alarm",
        "Hindi":     "दैनिक अलार्म",
        "Telugu":    "రోజువారీ అలారం",
        "Tamil":     "தினசரி அலாரம்",
        "Kannada":   "ದೈನಂದಿನ ಅಲಾರಂ",
        "Malayalam": "ദൈനദിന അലാറം",
        "Marathi":   "दैनिक अलार्म",
        "Gujarati":  "દૈनิक એલાર્મ",
    },
    "growth_stages": {
        "English":   "Growth stages",
        "Hindi":     "विकास के चरण",
        "Telugu":    "పెరుగుదల దశలు",
        "Tamil":     "வளர்ச்சி நிலைகள்",
        "Kannada":   "ಬೆಳವಣಿಗೆ ಹಂತಗಳು",
        "Malayalam": "വളർച്ചാ ഘട്ടങ്ങൾ",
        "Marathi":   "वाढीचे टप्पे",
        "Gujarati":  "વૃddhi તbakkao",
    },
    "morning_every": {
        "English":   "every morning",
        "Hindi":     "हर सुबह",
        "Telugu":    "ప్రతి ఉదయం",
        "Tamil":     "தினமும் காலையில்",
        "Kannada":   "ಪ್ರತಿ ಬೆಳಗ್ಗೆ",
        "Malayalam": "ദിനംതോറും രാവിലെ",
        "Marathi":   "दररोज सकाळी",
        "Gujarati":  "દરરોજ સવારે",
    },
    "confirm_start": {
        "English":   "You'll receive a *Daily Crop Card* every morning at {alarm} with tasks, fertilizer reminders, and monitoring tips.",
        "Hindi":     "आपको हर सुबह {alarm} बजे *डेली क्रॉप कार्ड* मिलेगा — काम, खाद रिमाइंडर और निगरानी टिप्स।",
        "Telugu":    "మీకు ప్రతి ఉదయం {alarm} కి *డైలీ క్రాప్ కార్డ్* వస్తుంది — పనులు, ఎరువుల రిమైండర్లు మరియు పర్యవేక్షణ చిట్కాలు.",
        "Tamil":     "ஒவ்வொரு காலையிலும் {alarm} மணிக்கு *டெய்லி க்ராப் கார்ட்* வரும் — பணிகள், உர நினைவூட்டல்கள், கண்காணிப்பு குறிப்புகள்.",
        "Kannada":   "ಪ್ರತಿ ಬೆಳಗ್ಗೆ {alarm} ಕ್ಕೆ *ಡೈಲಿ ಕ್ರಾಪ್ ಕಾರ್ಡ್* ಬರುತ್ತದೆ — ಕಾರ್ಯಗಳು, ಗೊಬ್ಬರ ಜ್ಞಾಪನೆ, ತನಿಖೆ ಸಲಹೆ.",
        "Malayalam": "ദിനംതോറും {alarm} ന് *ഡൈലി ക്രോപ്പ് കാർഡ്* ലഭിക്കും — ജോലികൾ, വളം ഓർമ്മപ്പെടുത്തലുകൾ, നിരീക്ഷണ നുറുങ്ങുകൾ.",
        "Marathi":   "दररोज सकाळी {alarm} वाजता *डेली पीक कार्ड* येईल — कामे, खत आठवण आणि देखरेख टिप्स.",
        "Gujarati":  "દરરોજ સવારે {alarm} વાગ્યે *ડૈલી ક્રોપ કાર્ડ* આવશે — કામ, ખાતર રિminder અને મૉnitering tips.",
    },
}


def _s(key: str, lang: str, **kwargs) -> str:
    """Get a localised card string, fall back to English."""
    d = _CARD_STRINGS.get(key, {})
    tmpl = d.get(lang) or d.get("English", "")
    return tmpl.format(**kwargs) if kwargs else tmpl


def _progress_bar(current: int, total: int, width: int = 10) -> str:
    filled = current * width // total
    return "█" * filled + "░" * (width - filled)


# ══════════════════════════════════════════════════════════════════
# MAIN CARD BUILDER
# ══════════════════════════════════════════════════════════════════

def build_daily_card(
    journey: dict,
    farmer_name: str,
    ollama_tip: str | None = None,
    lang: str = "English",
) -> tuple[str, str]:
    """
    Build the daily crop card in the farmer's language.

    Returns:
        (markdown_text, tts_plain_text)
    """
    crop_key   = journey["crop_key"]
    crop_name  = journey["crop_name"]
    sow_date   = journey["sow_date"]
    har_date   = journey["harvest_date"]
    total_days = journey["total_days"]

    day   = (
        (__import__("datetime").date.today() - __import__("datetime").date.fromisoformat(sow_date)).days + 1
    )
    day   = max(1, day)
    stage = get_stage_for_day(crop_key, day)

    if not stage:
        # Journey complete
        lines = [
            f"🎉 *{_s('daily_card_header', lang)}*",
            f"*{_s('good_morning', lang, name=farmer_name)}*",
            "",
            f"🌾 Your *{crop_name}* journey is complete!",
            f"📅 {_s('harvest_date_label', lang)}: {har_date}",
        ]
        tts = f"{_s('good_morning', lang, name=farmer_name)} Your {crop_name} journey is complete."
        return "\n".join(lines), tts

    # ── Computed metadata ────────────────────────────────────────
    stage_name       = stage["name"]
    stage_emoji      = stage["emoji"]
    is_critical      = stage.get("critical", False)
    day_in           = stage.get("day_in_stage", 1)
    stage_total      = stage.get("stage_total_days", 1)
    crop_progress    = stage.get("crop_progress_pct", 0)
    progress_bar     = _progress_bar(crop_progress, 100)
    key_tasks        = stage.get("key_tasks", [])
    dos              = stage.get("dos", [])
    donts            = stage.get("donts", [])
    monitor          = stage.get("monitor", [])
    fert             = fertilizer_due_today(crop_key, day)

    # Days to next stage / harvest
    days_left_stage  = stage_total - day_in
    harvest_dt       = __import__("datetime").date.fromisoformat(har_date)
    today            = __import__("datetime").date.today()
    days_to_harvest  = (harvest_dt - today).days

    # ── Markdown card ────────────────────────────────────────────
    lines: list[str] = []

    # Header
    lines += [
        f"*{_s('daily_card_header', lang)}* — {crop_name}",
        f"*{_s('good_morning', lang, name=farmer_name)}*",
        "",
        f"📅 {_s('day_of', lang, day=day, total=total_days)}",
        f"📊 {_s('progress', lang)}: {progress_bar} {crop_progress}%",
        "",
    ]

    # Current stage
    lines += [
        f"*{stage_emoji} {_s('current_stage', lang)}: {stage_name}*",
        f"_{_s('day_in_stage', lang, day_in=day_in, stage_total=stage_total)}_",
    ]
    if is_critical:
        lines += ["", f"*{_s('critical_stage_warning', lang)}*"]
    lines.append("")

    # Today's tasks
    if key_tasks:
        lines.append(f"*{_s('todays_tasks', lang)}*")
        for task in key_tasks[:3]:
            lines.append(f"• {task}")
        lines.append("")

    # Do's
    if dos:
        lines.append(f"*{_s('dos', lang)}*")
        for d in dos[:3]:
            lines.append(f"✅ {d}")
        lines.append("")

    # Don'ts
    if donts:
        lines.append(f"*{_s('donts', lang)}*")
        for d in donts[:3]:
            lines.append(f"❌ {d}")
        lines.append("")

    # Fertilizer
    if fert:
        lines += [
            f"*{_s('fertilizer_due', lang)}*",
            f"💊 {_s('product', lang)}: {fert['product']}",
            f"📏 {_s('dose', lang)}: {fert['dose']}",
            f"🛠 {_s('method', lang)}: {fert['method']}",
            f"💰 {_s('cost', lang)}: {fert['cost']}",
            "",
        ]

    # Monitor
    if monitor:
        lines.append(f"*{_s('what_to_monitor', lang)}*")
        for m in monitor[:3]:
            lines.append(f"🔍 {m}")
        lines.append("")

    # AI tip
    if ollama_tip and ollama_tip.strip():
        lines += [
            f"*{_s('ai_tip', lang)}*",
            f"_{ollama_tip.strip()}_",
            "",
        ]

    # Footer
    if days_left_stage > 0:
        lines.append(_s("next_stage_in", lang, days=days_left_stage))
    if days_to_harvest > 0:
        lines.append(_s("harvest_in", lang, days=days_to_harvest, date=har_date))
    elif days_to_harvest == 0:
        lines.append("🎉 Harvest day is today!")

    markdown = "\n".join(lines)

    # ── TTS plain text ────────────────────────────────────────────
    tts_parts = [
        _s("good_morning", lang, name=farmer_name),
        f"{crop_name}.",
        _s("day_of", lang, day=day, total=total_days) + ".",
        f"{stage_emoji} {stage_name}.",
    ]
    if is_critical:
        tts_parts.append(_s("critical_stage_warning", lang))
    if key_tasks:
        tts_parts.append(key_tasks[0])
    if fert:
        tts_parts.append(
            f"{_s('fertilizer_due', lang)}: {fert['product']} — {fert['dose']}"
        )
    if ollama_tip:
        tts_parts.append(ollama_tip.strip()[:200])

    tts = " ".join(tts_parts)
    return markdown, tts


# ══════════════════════════════════════════════════════════════════
# LLM TIP PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════

# Language instruction for tip prompt — tells the LLM to reply in
# the farmer's language so the tip inside the card is also localised.
_LANG_TIP_INSTRUCTION: dict[str, str] = {
    "English":   "",
    "Hindi":     "IMPORTANT: Reply ONLY in Hindi (हिंदी). Every word must be in Hindi.\n\n",
    "Telugu":    "IMPORTANT: Reply ONLY in Telugu (తెలుగు). Every word must be in Telugu.\n\n",
    "Tamil":     "IMPORTANT: Reply ONLY in Tamil (தமிழ்). Every word must be in Tamil.\n\n",
    "Kannada":   "IMPORTANT: Reply ONLY in Kannada (ಕನ್ನಡ). Every word must be in Kannada.\n\n",
    "Malayalam": "IMPORTANT: Reply ONLY in Malayalam (മലയാളം). Every word must be in Malayalam.\n\n",
    "Marathi":   "IMPORTANT: Reply ONLY in Marathi (मराठी). Every word must be in Marathi.\n\n",
    "Gujarati":  "IMPORTANT: Reply ONLY in Gujarati (ગુજરાતી). Every word must be in Gujarati.\n\n",
}


def build_daily_tip_prompt(
    journey: dict,
    profile: dict,
) -> str:
    """
    Build the prompt sent to Ollama to generate the daily AI tip.
    Injects a language instruction so the tip is returned in the
    farmer's chosen language.
    """
    crop_key  = journey["crop_key"]
    crop_name = journey["crop_name"]
    sow_date  = journey["sow_date"]
    total     = journey["total_days"]

    day = (
        (__import__("datetime").date.today() - __import__("datetime").date.fromisoformat(sow_date)).days + 1
    )
    day   = max(1, day)
    stage = get_stage_for_day(crop_key, day)

    name     = profile.get("name", "Farmer")
    village  = profile.get("village", "India")
    district = profile.get("district", "")
    lang     = profile.get("language", "English")

    lang_instruction = _LANG_TIP_INSTRUCTION.get(lang, "")
    stage_name = stage["name"] if stage else "Complete"
    stage_tasks = stage.get("key_tasks", [])[:2] if stage else []
    tasks_str = "; ".join(stage_tasks) if stage_tasks else "general crop monitoring"

    location = f"{village}, {district}, India" if district else f"{village}, India"

    prompt = (
        f"{lang_instruction}"
        f"Farmer: {name} | Crop: {crop_name} | Location: {location}\n"
        f"Today: Day {day} of {total} | Stage: {stage_name}\n"
        f"Current tasks: {tasks_str}\n\n"
        f"Give ONE specific, practical farming tip for today "
        f"relevant to this stage and location. "
        f"2-3 sentences only. No bullet points. No headings."
    )
    return prompt


# ══════════════════════════════════════════════════════════════════
# JOURNEY START MESSAGE BUILDER
# ══════════════════════════════════════════════════════════════════

def build_journey_start_message(
    journey: dict,
    farmer_name: str,
    lang: str = "English",
) -> str:
    """
    Build the confirmation message sent when a journey starts.
    Localised to the farmer's language.
    """
    crop_key  = journey["crop_key"]
    crop_name = journey["crop_name"]
    sow_date  = journey["sow_date"]
    har_date  = journey["harvest_date"]
    total     = journey["total_days"]
    alarm     = journey.get("alarm_time", "06:00")

    lifecycle    = CROP_LIFECYCLES.get(crop_key, {})
    stages       = lifecycle.get("stages", [])
    stages_preview = "\n".join(
        f"  {s['emoji']} {s['name']} ({_s('day_of', lang, day=s['start']+1, total=s['end'])})"
        for s in stages
    )

    greeting = _s("journey_started", lang, crop=crop_name)
    confirm  = _s("confirm_start",   lang, alarm=alarm)

    return (
        f"✅ {greeting}\n\n"
        f"📅 {_s('sow_date_label', lang)}: {sow_date}\n"
        f"🎉 {_s('harvest_date_label', lang)}: {har_date}\n"
        f"⏱ {_s('duration_label', lang)}: {total} {_s('days', lang)}\n"
        f"🔔 {_s('daily_alarm', lang)}: {alarm} {_s('morning_every', lang)}\n\n"
        f"*{_s('growth_stages', lang)}:*\n{stages_preview}\n\n"
        f"{confirm}"
    )