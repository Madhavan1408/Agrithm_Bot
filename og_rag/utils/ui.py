"""
utils/ui.py — All UI strings and keyboards for Agrithm.
─────────────────────────────────────────────────────────
Rules:
- Never mention KVK or Krishi Vigyan Kendra anywhere.
- Every dict must have an "English" key as the final fallback.
- Use get_msg(dict, lang) everywhere — never index dicts directly.

FIXES vs v1:
  FIX H3: Added "alarm" key to MENU_BUTTONS for all 11 languages.
           Previously the alarm button never appeared on the keyboard —
           users could only set alarms by typing, not via a button tap.
  FIX H3: main_menu_keyboard() now includes a 4th row with alarm + chat.
"""

from telegram import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove,
)
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agrithm_config import LANGUAGES


# ═══════════════════════════════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════════════════════════════

def language_keyboard() -> ReplyKeyboardMarkup:
    """Builds keyboard from LANGUAGES in config — auto-updates when languages are added."""
    names = list(LANGUAGES.keys())
    rows  = [names[i : i + 2] for i in range(0, len(names), 2)]
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("Share My Location", request_location=True)]],
        one_time_keyboard=True,
        resize_keyboard=True,
    )


def main_menu_keyboard(lang: str = "English", chat_unread: int = 0) -> ReplyKeyboardMarkup:
    """
    Returns a fully localised main menu keyboard with 8 action buttons.

    Layout (4 rows):
      Row 1: Ask Question  |  Mandi Prices
      Row 2: Connect Farmers | Disease Check
      Row 3: Daily News    |  My Profile
      Row 4: ⏰ My Alarms  |  Chat Room (with unread badge)

    FIX H3: Row 4 now includes the alarm button which was previously
    missing — users can now tap instead of having to type "alarm".
    """
    btn        = MENU_BUTTONS.get(lang, MENU_BUTTONS["English"])
    chat_label = btn["chat"]
    if chat_unread:
        chat_label = f"{chat_label} ({chat_unread})"
    rows = [
        [btn["ask"],     btn["mandi"]],
        [btn["connect"], btn["disease"]],
        [btn["news"],    btn["profile"]],
        [btn["alarm"],   chat_label],      # FIX H3: alarm button now visible
    ]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(b) for b in row] for row in rows],
        resize_keyboard=True,
        is_persistent=True,
    )


def chat_room_keyboard(lang: str = "English", in_chat: bool = False) -> ReplyKeyboardMarkup:
    btn  = CHAT_BUTTONS.get(lang, CHAT_BUTTONS["English"])
    rows = [[btn["leave"], btn["history"]]] if in_chat else [[btn["leave"]]]
    return ReplyKeyboardMarkup(
        [[KeyboardButton(b) for b in row] for row in rows],
        resize_keyboard=True,
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ═══════════════════════════════════════════════════════════════════════
# MENU BUTTON LABELS  (used for routing AND display)
# ═══════════════════════════════════════════════════════════════════════
# FIX H3: Added "alarm" key to every language entry.
#         The alarm button label is kept short and uses ⏰ emoji
#         so farmers immediately recognise it across all languages.

MENU_BUTTONS = {
    "Tamil":     {
        "ask":     "கேள்வி கேளுங்கள்",
        "mandi":   "மண்டி விலைகள்",
        "connect": "விவசாயிகளை இணைக்கவும்",
        "disease": "நோய் கண்டறிதல்",
        "news":    "தினசரி செய்திகள்",
        "profile": "என் சுயவிவரம்",
        "chat":    "அரட்டை அறை",
        "alarm":   "⏰ என் அலாரம்கள்",   # FIX H3
    },
    "Telugu":    {
        "ask":     "ప్రశ్న అడగండి",
        "mandi":   "మండీ ధరలు",
        "connect": "రైతులను కనెక్ట్ చేయి",
        "disease": "వ్యాధి తనిఖీ",
        "news":    "దైనందిన వార్తలు",
        "profile": "నా ప్రొఫైల్",
        "chat":    "చాట్ గది",
        "alarm":   "⏰ నా అలారాలు",       # FIX H3
    },
    "Kannada":   {
        "ask":     "ಪ್ರಶ್ನೆ ಕೇಳಿ",
        "mandi":   "ಮಂಡಿ ಬೆಲೆಗಳು",
        "connect": "ರೈತರನ್ನು ಸಂಪರ್ಕಿಸಿ",
        "disease": "ರೋಗ ಪರೀಕ್ಷೆ",
        "news":    "ದಿನದ ಸುದ್ದಿ",
        "profile": "ನನ್ನ ಪ್ರೊಫೈಲ್",
        "chat":    "ಚಾಟ್ ರೂಮ್",
        "alarm":   "⏰ ನನ್ನ ಅಲಾರಂಗಳು",   # FIX H3
    },
    "Malayalam": {
        "ask":     "ചോദ്യം ചോദിക്കൂ",
        "mandi":   "മണ്ടി വിലകൾ",
        "connect": "കർഷകരെ ബന്ധിപ്പിക്കൂ",
        "disease": "രോഗ പരിശോധന",
        "news":    "ദൈനംദിന വാർത്ത",
        "profile": "എന്റെ പ്രൊഫൈൽ",
        "chat":    "ചാറ്റ് റൂം",
        "alarm":   "⏰ എന്റെ അലാറങ്ങൾ",  # FIX H3
    },
    "Hindi":     {
        "ask":     "सवाल पूछें",
        "mandi":   "मंडी भाव",
        "connect": "किसानों से जुड़ें",
        "disease": "रोग जाँच",
        "news":    "दैनिक समाचार",
        "profile": "मेरी प्रोफाइल",
        "chat":    "चैट रूम",
        "alarm":   "⏰ मेरे अलार्म",      # FIX H3
    },
    "Punjabi":   {
        "ask":     "ਸਵਾਲ ਪੁੱਛੋ",
        "mandi":   "ਮੰਡੀ ਭਾਅ",
        "connect": "ਕਿਸਾਨਾਂ ਨਾਲ ਜੁੜੋ",
        "disease": "ਰੋਗ ਜਾਂਚ",
        "news":    "ਰੋਜ਼ਾਨਾ ਖ਼ਬਰਾਂ",
        "profile": "ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ",
        "chat":    "ਚੈਟ ਰੂਮ",
        "alarm":   "⏰ ਮੇਰੇ ਅਲਾਰਮ",      # FIX H3
    },
    "Gujarati":  {
        "ask":     "પ્રશ્ન પૂછો",
        "mandi":   "મંડી ભાવ",
        "connect": "ખેડૂતોને જોડો",
        "disease": "રોગ તપાસ",
        "news":    "દૈનિક સમાચાર",
        "profile": "મારી પ્રોફાઇલ",
        "chat":    "ચેટ રૂમ",
        "alarm":   "⏰ મારા એલાર્મ",     # FIX H3
    },
    "Marathi":   {
        "ask":     "प्रश्न विचारा",
        "mandi":   "मंडी भाव",
        "connect": "शेतकऱ्यांशी जोडा",
        "disease": "रोग तपासणी",
        "news":    "दैनंदिन बातम्या",
        "profile": "माझी प्रोफाइल",
        "chat":    "चॅट रूम",
        "alarm":   "⏰ माझे अलार्म",     # FIX H3
    },
    "Bengali":   {
        "ask":     "প্রশ্ন করুন",
        "mandi":   "মান্ডি দাম",
        "connect": "কৃষকদের সাথে যুক্ত হন",
        "disease": "রোগ পরীক্ষা",
        "news":    "দৈনিক সংবাদ",
        "profile": "আমার প্রোফাইল",
        "chat":    "চ্যাট রুম",
        "alarm":   "⏰ আমার অ্যালার্ম",  # FIX H3
    },
    "Odia":      {
        "ask":     "ପ୍ରଶ୍ନ କରନ୍ତୁ",
        "mandi":   "ମଣ୍ଡି ମୂଲ୍ୟ",
        "connect": "କୃଷକଙ୍କ ସହ ଯୋଡ଼ନ୍ତୁ",
        "disease": "ରୋଗ ପରୀକ୍ଷା",
        "news":    "ଦୈନିକ ସମ୍ବାଦ",
        "profile": "ମୋ ପ୍ରୋଫାଇଲ୍",
        "chat":    "ଚ୍ୟାଟ୍ ରୁମ୍",
        "alarm":   "⏰ ମୋ ଆଲାର୍ମ",       # FIX H3
    },
    "English":   {
        "ask":     "Ask Question",
        "mandi":   "Mandi Prices",
        "connect": "Connect Farmers",
        "disease": "Disease Check",
        "news":    "Daily News",
        "profile": "My Profile",
        "chat":    "Chat Room",
        "alarm":   "⏰ My Alarms",        # FIX H3
    },
}

CHAT_BUTTONS = {
    "Tamil":     {"leave": "அரட்டையை விட்டு வெளியேறு", "history": "வரலாற்றை காண்க"},
    "Telugu":    {"leave": "చాట్ వదిలి వెళ్ళు",         "history": "చరిత్ర చూడు"},
    "Kannada":   {"leave": "ಚಾಟ್ ಬಿಡಿ",                 "history": "ಇತಿಹಾಸ ನೋಡಿ"},
    "Malayalam": {"leave": "ചാറ്റ് വിടുക",              "history": "ചരിത്രം കാണുക"},
    "Hindi":     {"leave": "चैट छोड़ें",                 "history": "इतिहास देखें"},
    "Punjabi":   {"leave": "ਚੈਟ ਛੱਡੋ",                  "history": "ਇਤਿਹਾਸ ਦੇਖੋ"},
    "Gujarati":  {"leave": "ચેટ છોડો",                   "history": "ઇતિહાસ જુઓ"},
    "Marathi":   {"leave": "चॅट सोडा",                   "history": "इतिहास पहा"},
    "Bengali":   {"leave": "চ্যাট ছেড়ে দিন",            "history": "ইতিহাস দেখুন"},
    "Odia":      {"leave": "ଚ୍ୟାଟ୍ ଛାଡ଼ନ୍ତୁ",             "history": "ଇତିହାସ ଦେଖନ୍ତୁ"},
    "English":   {"leave": "Leave Chat",                "history": "View History"},
}


# ═══════════════════════════════════════════════════════════════════════
# MESSAGE DICTIONARIES  — one dict per UI string, all 11 languages
# ═══════════════════════════════════════════════════════════════════════

GREETINGS = {
    "Tamil":     "வணக்கம்! நான் Agrithm. உங்கள் விவசாய உதவியாளர்.",
    "Telugu":    "నమస్కారం! నేను Agrithm. మీ వ్యవసాయ సహాయకుడు.",
    "Kannada":   "ನಮಸ್ಕಾರ! ನಾನು Agrithm. ನಿಮ್ಮ ಕೃಷಿ ಸಹಾಯಕ.",
    "Malayalam": "നമസ്കാരം! ഞാൻ Agrithm ആണ്. നിങ്ങളുടെ കൃഷി സഹായി.",
    "Hindi":     "नमस्ते! मैं Agrithm हूँ। आपका कृषि सहायक।",
    "Punjabi":   "ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ Agrithm ਹਾਂ। ਤੁਹਾਡਾ ਖੇਤੀ ਸਹਾਇਕ।",
    "Gujarati":  "નમસ્તે! હું Agrithm છું. તમારો ખેતી સહાયક.",
    "Marathi":   "नमस्कार! मी Agrithm आहे. तुमचा शेती सहाय्यक.",
    "Bengali":   "নমস্কার! আমি Agrithm। আপনার কৃষি সহায়ক।",
    "Odia":      "ନମସ୍କାର! ମୁଁ Agrithm। ଆପଣଙ୍କ କୃଷି ସହାୟକ।",
    "English":   "Hello! I am Agrithm. Your personal farming assistant.",
}

WELCOME_BACK = {
    "Tamil":     "மீண்டும் வரவேற்கிறோம், {name}! இன்று என்ன உதவி வேண்டும்?",
    "Telugu":    "మళ్ళీ స్వాగతం, {name}! ఈరోజు నేను ఎలా సహాయం చేయగలను?",
    "Kannada":   "ಮತ್ತೆ ಸ್ವಾಗತ, {name}! ಇಂದು ಏನು ಸಹಾಯ ಬೇಕು?",
    "Malayalam": "വീണ്ടും സ്വാഗതം, {name}! ഇന്ന് എന്ത് സഹായം വേണം?",
    "Hindi":     "वापस स्वागत है, {name}! आज मैं कैसे मदद कर सकता हूँ?",
    "Punjabi":   "ਵਾਪਸ ਸੁਆਗਤ ਹੈ, {name}! ਅੱਜ ਮੈਂ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?",
    "Gujarati":  "પાછા આવ્યા, {name}! આજે હું કેવી રીતે મદદ કરી શકું?",
    "Marathi":   "परत स्वागत, {name}! आज मी कशी मदत करू?",
    "Bengali":   "আবার স্বাগতম, {name}! আজ আমি কীভাবে সাহায্য করতে পারি?",
    "Odia":      "ପୁଣି ସ୍ୱାଗତ, {name}! ଆଜି ମୁଁ କିପରି ସାହାଯ୍ୟ କରିପାରିବି?",
    "English":   "Welcome back, {name}! How can I help you today?",
}

SHARE_LOCATION = {
    "Tamil":     "முதலில் உங்கள் இருப்பிடத்தை பகிரவும்:",
    "Telugu":    "మొదట మీ స్థానం షేర్ చేయండి:",
    "Kannada":   "ಮೊದಲು ನಿಮ್ಮ ಸ್ಥಳ ಹಂಚಿಕೊಳ್ಳಿ:",
    "Malayalam": "ആദ്യം നിങ്ങളുടെ സ്ഥലം പങ്കിടൂ:",
    "Hindi":     "पहले अपना स्थान शेयर करें:",
    "Punjabi":   "ਪਹਿਲਾਂ ਆਪਣੀ ਸਥਿਤੀ ਸਾਂਝੀ ਕਰੋ:",
    "Gujarati":  "પ્રથમ તમારું સ્થાન શેર કરો:",
    "Marathi":   "आधी तुमचे स्थान शेअर करा:",
    "Bengali":   "প্রথমে আপনার অবস্থান শেয়ার করুন:",
    "Odia":      "ପ୍ରଥମେ ଆପଣଙ୍କ ସ୍ଥାନ ଶେୟାର କରନ୍ତୁ:",
    "English":   "First, share your location:",
}

CHOOSE_LANGUAGE = {
    "Tamil":     "உங்கள் மொழியை தேர்ந்தெடுக்கவும்:",
    "Telugu":    "మీ భాషను ఎంచుకోండి:",
    "Kannada":   "ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ:",
    "Malayalam": "നിങ്ങളുടെ ഭാഷ തിരഞ്ഞെടുക്കൂ:",
    "Hindi":     "अपनी भाषा चुनें:",
    "Punjabi":   "ਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ:",
    "Gujarati":  "તમારી ભાષા પસંદ કરો:",
    "Marathi":   "तुमची भाषा निवडा:",
    "Bengali":   "আপনার ভাষা বেছে নিন:",
    "Odia":      "ଆପଣଙ୍କ ଭାଷା ବାଛନ୍ତୁ:",
    "English":   "Choose your language:",
}

ASK_NAME = {
    "Tamil":     "உங்கள் பெயரை தட்டச்சு செய்யவும் அல்லது குரல் செய்தியாக அனுப்பவும்.",
    "Telugu":    "మీ పేరు టైప్ చేయండి లేదా వాయిస్ మెసేజ్ పంపండి.",
    "Kannada":   "ನಿಮ್ಮ ಹೆಸರನ್ನು ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಕಳುಹಿಸಿ.",
    "Malayalam": "നിങ്ങളുടെ പേര് ടൈപ്പ് ചെയ്യൂ അല്ലെങ്കിൽ വോയ്സ് മെസേജ് അയക്കൂ.",
    "Hindi":     "अपना नाम टाइप करें या वॉइस मैसेज भेजें।",
    "Punjabi":   "ਆਪਣਾ ਨਾਮ ਟਾਈਪ ਕਰੋ ਜਾਂ ਵੌਇਸ ਮੈਸੇਜ ਭੇਜੋ।",
    "Gujarati":  "તમારું નામ ટાઇપ કરો અથવા વૉઇસ મેસેજ મોકલો.",
    "Marathi":   "तुमचे नाव टाइप करा किंवा व्हॉइस मेसेज पाठवा.",
    "Bengali":   "আপনার নাম টাইপ করুন বা ভয়েস মেসেজ পাঠান।",
    "Odia":      "ଆପଣଙ୍କ ନାମ ଟାଇପ୍ କରନ୍ତୁ ବା ଭଏସ୍ ମେସେଜ୍ ପଠାନ୍ତୁ।",
    "English":   "Please type your name or send it as a voice message.",
}

HELLO_NAME = {
    "Tamil":     "வணக்கம் {name}! நீங்கள் என்ன பயிர் பயிரிடுகிறீர்கள்?",
    "Telugu":    "నమస్కారం {name}! మీరు ఏ పంట వేస్తున్నారు?",
    "Kannada":   "ನಮಸ್ಕಾರ {name}! ನೀವು ಯಾವ ಬೆಳೆ ಬೆಳೆಯುತ್ತೀರಿ?",
    "Malayalam": "നമസ്കാരം {name}! നിങ്ങൾ എന്ത് വിള കൃഷി ചെയ്യുന്നു?",
    "Hindi":     "नमस्ते {name}! आप कौन सी फसल उगाते हैं?",
    "Punjabi":   "ਸਤ ਸ੍ਰੀ ਅਕਾਲ {name}! ਤੁਸੀਂ ਕਿਹੜੀ ਫ਼ਸਲ ਉਗਾਉਂਦੇ ਹੋ?",
    "Gujarati":  "નમસ્તે {name}! તમે કઈ ફસલ ઉગાડો છો?",
    "Marathi":   "नमस्कार {name}! तुम्ही कोणते पीक घेता?",
    "Bengali":   "নমস্কার {name}! আপনি কোন ফসল চাষ করেন?",
    "Odia":      "ନମସ୍କାର {name}! ଆପଣ କେଉଁ ଫସଲ ଚାଷ କରନ୍ତି?",
    "English":   "Hello {name}! What crop do you mainly grow?",
}

ASK_CROP = {
    "Tamil":     "நீங்கள் என்ன பயிர் பயிரிடுகிறீர்கள்? (எ.கா: நெல், வாழை, கரும்பு)",
    "Telugu":    "మీరు ఏ పంట వేస్తున్నారు? (ఉదా: వరి, అరటి, చెరకు)",
    "Kannada":   "ನೀವು ಯಾವ ಬೆಳೆ ಬೆಳೆಯುತ್ತೀರಿ? (ಉದಾ: ಭತ್ತ, ಬಾಳೆ, ಕಬ್ಬು)",
    "Malayalam": "നിങ്ങൾ ഏത് വിള കൃഷി ചെയ്യുന്നു? (ഉദാ: നെല്ല്, വാഴ, കരിമ്പ്)",
    "Hindi":     "आप कौन सी फसल उगाते हैं? (जैसे: धान, गन्ना, गेहूं)",
    "Punjabi":   "ਤੁਸੀਂ ਕਿਹੜੀ ਫਸਲ ਉਗਾਉਂਦੇ ਹੋ? (ਜਿਵੇਂ: ਝੋਨਾ, ਕਣਕ, ਗੰਨਾ)",
    "Gujarati":  "તમે કઈ ફસલ ઉગાડો છો? (ઉદા: ડાંગર, ઘઉં, શેરડી)",
    "Marathi":   "तुम्ही कोणते पीक घेता? (उदा: भात, ऊस, गहू)",
    "Bengali":   "আপনি কোন ফসল চাষ করেন? (যেমন: ধান, আখ, গম)",
    "Odia":      "ଆପଣ କେଉଁ ଫସଲ ଚାଷ କରନ୍ତି? (ଯେପରି: ଧାନ, ଆଖୁ, ଗହମ)",
    "English":   "What crop do you mainly grow? (e.g. paddy, sugarcane, wheat)",
}

ASK_VILLAGE = {
    "Tamil":     "உங்கள் கிராமம் அல்லது நகரம் என்ன?",
    "Telugu":    "మీ గ్రామం లేదా పట్టణం ఏది?",
    "Kannada":   "ನಿಮ್ಮ ಗ್ರಾಮ ಅಥವಾ ಪಟ್ಟಣ ಯಾವುದು?",
    "Malayalam": "നിങ്ങളുടെ ഗ്രാമം അല്ലെങ്കിൽ പട്ടണം ഏതാണ്?",
    "Hindi":     "आपका गांव या शहर कौन सा है?",
    "Punjabi":   "ਤੁਹਾਡਾ ਪਿੰਡ ਜਾਂ ਸ਼ਹਿਰ ਕਿਹੜਾ ਹੈ?",
    "Gujarati":  "તમારું ગામ અથવા શહેર કયું છે?",
    "Marathi":   "तुमचे गाव किंवा शहर कोणते आहे?",
    "Bengali":   "আপনার গ্রাম বা শহর কোনটি?",
    "Odia":      "ଆପଣଙ୍କ ଗ୍ରାମ ବା ସହର କେଉଁଟି?",
    "English":   "What is your village or town name?",
}

ASK_VILLAGE_GPS = {
    "Tamil":     "GPS அடிப்படையில் உங்கள் இருப்பிடம் {village} என கண்டறியப்பட்டது. நீங்கள் இதை உறுதிப்படுத்தலாம் அல்லது வேறு பெயரை தட்டச்சு செய்யலாம்:",
    "Telugu":    "GPS ఆధారంగా మీ స్థానం {village} గా గుర్తించబడింది. మీరు దీన్ని నిర్ధారించవచ్చు లేదా వేరే పేరు టైప్ చేయవచ్చు:",
    "Kannada":   "GPS ಆಧಾರದ ಮೇಲೆ ನಿಮ್ಮ ಸ್ಥಳ {village} ಎಂದು ಗುರುತಿಸಲಾಗಿದೆ. ನೀವು ಇದನ್ನು ದೃಢೀಕರಿಸಬಹುದು ಅಥವಾ ಬೇರೆ ಹೆಸರು ಟೈಪ್ ಮಾಡಬಹುದು:",
    "Malayalam": "GPS ഡാറ്റ പ്രകാരം നിങ്ങളുടെ സ്ഥലം {village} ആണ്. ഇത് ശരിയാണോ? അല്ലെങ്കിൽ മറ്റൊരു പേര് ടൈപ്പ് ചെയ്യൂ:",
    "Hindi":     "GPS के अनुसार आपका स्थान {village} है। इसे कन्फर्म करें या अपने गांव का नाम टाइप करें:",
    "Punjabi":   "GPS ਅਨੁਸਾਰ ਤੁਹਾਡੀ ਸਥਿਤੀ {village} ਹੈ। ਇਸਨੂੰ ਕਨਫਰਮ ਕਰੋ ਜਾਂ ਆਪਣੇ ਪਿੰਡ ਦਾ ਨਾਮ ਟਾਈਪ ਕਰੋ:",
    "Gujarati":  "GPS અનુસાર તમારું સ્થાન {village} છે. તેની પુષ્ટિ કરો અથવા ગામ નું નામ ટાઇપ કરો:",
    "Marathi":   "GPS नुसार तुमचे स्थान {village} आहे. याची पुष्टी करा किंवा गावाचे नाव टाइप करा:",
    "Bengali":   "GPS অনুযায়ী আপনার অবস্থান {village}। নিশ্চিত করুন বা গ্রামের নাম টাইপ করুন:",
    "Odia":      "GPS ଅନୁସାରେ ଆପଣଙ୍କ ସ୍ଥାନ {village}। ନିଶ୍ଚିତ କରନ୍ତୁ ବା ଗ୍ରାମ ନାମ ଟାଇପ କରନ୍ତୁ:",
    "English":   "Based on GPS your location is {village}. Confirm or type a different village name:",
}

PROFILE_SAVED = {
    "Tamil":     "✅ உங்கள் விவரங்கள் சேமிக்கப்பட்டன!\n👤 பெயர்: {name}\n🌾 பயிர்: {crop}\n🏘 கிராமம்: {village}\n📍 மாவட்டம்: {district}",
    "Telugu":    "✅ మీ వివరాలు సేవ్ చేయబడ్డాయి!\n👤 పేరు: {name}\n🌾 పంట: {crop}\n🏘 గ్రామం: {village}\n📍 జిల్లా: {district}",
    "Kannada":   "✅ ನಿಮ್ಮ ವಿವರಗಳು ಉಳಿಸಲಾಗಿದೆ!\n👤 ಹೆಸರು: {name}\n🌾 ಬೆಳೆ: {crop}\n🏘 ಗ್ರಾಮ: {village}\n📍 ಜಿಲ್ಲೆ: {district}",
    "Malayalam": "✅ നിങ്ങളുടെ വിവരങ്ങൾ സേവ് ചെയ്തു!\n👤 പേര്: {name}\n🌾 വിള: {crop}\n🏘 ഗ്രാമം: {village}\n📍 ജില്ല: {district}",
    "Hindi":     "✅ आपकी जानकारी सहेजी गई!\n👤 नाम: {name}\n🌾 फसल: {crop}\n🏘 गांव: {village}\n📍 जिला: {district}",
    "Punjabi":   "✅ ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ ਸੁਰੱਖਿਅਤ ਕੀਤੀ ਗਈ!\n👤 ਨਾਮ: {name}\n🌾 ਫ਼ਸਲ: {crop}\n🏘 ਪਿੰਡ: {village}\n📍 ਜ਼ਿਲ੍ਹਾ: {district}",
    "Gujarati":  "✅ તમારી માહિતી સાચવવામાં આવી!\n👤 નામ: {name}\n🌾 ફસલ: {crop}\n🏘 ગામ: {village}\n📍 જિલ્લો: {district}",
    "Marathi":   "✅ तुमची माहिती जतन केली!\n👤 नाव: {name}\n🌾 पीक: {crop}\n🏘 गाव: {village}\n📍 जिल्हा: {district}",
    "Bengali":   "✅ আপনার তথ্য সংরক্ষণ করা হয়েছে!\n👤 নাম: {name}\n🌾 ফসল: {crop}\n🏘 গ্রাম: {village}\n📍 জেলা: {district}",
    "Odia":      "✅ ଆପଣଙ୍କ ତଥ୍ୟ ସଂରକ୍ଷିତ ହୋଇଛି!\n👤 ନାମ: {name}\n🌾 ଫସଲ: {crop}\n🏘 ଗ୍ରାମ: {village}\n📍 ଜିଲ୍ଲା: {district}",
    "English":   "✅ Your profile saved!\n👤 Name: {name}\n🌾 Crop: {crop}\n🏘 Village: {village}\n📍 District: {district}",
}

WELCOME_COMPLETE = {
    "Tamil":     "🌾 {name}, நீங்கள் இப்போது Agrithm-ல் பதிவு செய்யப்பட்டீர்கள்! கீழே உள்ள பொத்தான்களை பயன்படுத்தவும்.",
    "Telugu":    "🌾 {name}, మీరు Agrithm లో నమోదు చేయబడ్డారు! దయచేసి క్రింది బటన్లు ఉపయోగించండి.",
    "Kannada":   "🌾 {name}, ನೀವು Agrithm ನಲ್ಲಿ ನೋಂದಾಯಿಸಲಾಗಿದೆ! ದಯವಿಟ್ಟು ಕೆಳಗಿನ ಬಟನ್‌ಗಳನ್ನು ಬಳಸಿ.",
    "Malayalam": "🌾 {name}, നിങ്ങൾ Agrithm ൽ രജിസ്റ്റർ ചെയ്തു! ചുവടെ ഉള്ള ബട്ടണുകൾ ഉപയോഗിക്കൂ.",
    "Hindi":     "🌾 {name}, आप Agrithm में पंजीकृत हो गए हैं! नीचे दिए बटनों का उपयोग करें।",
    "Punjabi":   "🌾 {name}, ਤੁਸੀਂ Agrithm ਵਿੱਚ ਰਜਿਸਟਰ ਹੋ ਗਏ ਹੋ! ਕਿਰਪਾ ਕਰਕੇ ਹੇਠਾਂ ਦਿੱਤੇ ਬਟਨਾਂ ਦੀ ਵਰਤੋਂ ਕਰੋ।",
    "Gujarati":  "🌾 {name}, તમે Agrithm માં નોંધાઈ ગયા છો! નીચેના બટનો વાપરો.",
    "Marathi":   "🌾 {name}, तुम्ही Agrithm मध्ये नोंदणी केली! खालील बटणे वापरा.",
    "Bengali":   "🌾 {name}, আপনি Agrithm এ নিবন্ধিত হয়েছেন! নীচের বোতামগুলি ব্যবহার করুন।",
    "Odia":      "🌾 {name}, ଆପଣ Agrithm ରେ ପଞ୍ଜୀକୃତ ହୋଇଛନ୍ତି! ନିମ୍ନ ବଟଗୁଡ଼ିକ ବ୍ୟବହାର କରନ୍ତୁ।",
    "English":   "🌾 {name}, you are now registered with Agrithm! Use the buttons below.",
}

THINKING = {
    "Tamil":     "🤔 யோசிக்கிறேன்...",
    "Telugu":    "🤔 ఆలోచిస్తున్నాను...",
    "Kannada":   "🤔 ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🤔 ആലോചിക്കുന്നു...",
    "Hindi":     "🤔 सोच रहा हूँ...",
    "Punjabi":   "🤔 ਸੋਚ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "🤔 વિચારી રહ્યો છું...",
    "Marathi":   "🤔 विचार करत आहे...",
    "Bengali":   "🤔 ভাবছি...",
    "Odia":      "🤔 ଭାବୁଛି...",
    "English":   "🤔 Thinking...",
}

ASK_QUESTION_PROMPT = {
    "Tamil":     "உங்கள் விவசாய கேள்வியை தட்டச்சு செய்யவும் அல்லது குரல் செய்தியாக அனுப்பவும்:",
    "Telugu":    "మీ వ్యవసాయ ప్రశ్నను టైప్ చేయండి లేదా వాయిస్ మెసేజ్ పంపండి:",
    "Kannada":   "ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಕಳುಹಿಸಿ:",
    "Malayalam": "നിങ്ങളുടെ കൃഷി ചോദ്യം ടൈപ്പ് ചെയ്യൂ അല്ലെങ്കിൽ വോയ്സ് മെസേജ് അയക്കൂ:",
    "Hindi":     "अपना खेती सवाल टाइप करें या वॉइस मैसेज भेजें:",
    "Punjabi":   "ਆਪਣਾ ਖੇਤੀ ਸਵਾਲ ਟਾਈਪ ਕਰੋ ਜਾਂ ਵੌਇਸ ਮੈਸੇਜ ਭੇਜੋ:",
    "Gujarati":  "તમારો ખેતી પ્રશ્ન ટાઇપ કરો અથવા વૉઇસ મેસેજ મોકલો:",
    "Marathi":   "तुमचा शेती प्रश्न टाइप करा किंवा व्हॉइस मेसेज पाठवा:",
    "Bengali":   "আপনার কৃষি প্রশ্ন টাইপ করুন বা ভয়েস মেসেজ পাঠান:",
    "Odia":      "ଆପଣଙ୍କ ଚାଷ ପ୍ରଶ୍ନ ଟାଇପ କରନ୍ତୁ ବା ଭଏସ ମେସେଜ ପଠାନ୍ତୁ:",
    "English":   "Type your farming question or send a voice message:",
}

VOICE_DOWNLOAD_ERROR = {
    "Tamil":     "❌ குரல் கோப்பை பதிவிறக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.",
    "Telugu":    "❌ వాయిస్ ఫైల్ డౌన్లోడ్ చేయడం విఫలమైంది. మళ్ళీ ప్రయత్నించండి.",
    "Kannada":   "❌ ವಾಯ್ಸ್ ಫೈಲ್ ಡೌನ್ಲೋಡ್ ವಿಫಲವಾಗಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "Malayalam": "❌ വോയ്സ് ഫയൽ ഡൗൺലോഡ് ചെയ്യാൻ കഴിഞ്ഞില്ല. വീണ്ടും ശ്രമിക്കൂ.",
    "Hindi":     "❌ वॉइस फाइल डाउनलोड नहीं हो सकी। कृपया दोबारा कोशिश करें।",
    "Punjabi":   "❌ ਵੌਇਸ ਫਾਈਲ ਡਾਊਨਲੋਡ ਨਹੀਂ ਹੋ ਸਕੀ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
    "Gujarati":  "❌ વૉઇસ ફાઇલ ડાઉનલોડ થઈ નથી. ફરી પ્રયત્ન કરો.",
    "Marathi":   "❌ व्हॉइस फाइल डाउनलोड होऊ शकली नाही. पुन्हा प्रयत्न करा.",
    "Bengali":   "❌ ভয়েস ফাইল ডাউনলোড করা যায়নি। আবার চেষ্টা করুন।",
    "Odia":      "❌ ଭଏସ ଫାଇଲ ଡାଉନଲୋଡ ହୋଇ ପାରିଲା ନାହିଁ। ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।",
    "English":   "❌ Could not download your voice message. Please try again.",
}

VOICE_UNCLEAR = {
    "Tamil":     "🎙 குரல் செய்தி தெளிவாக இல்லை. மீண்டும் அனுப்பவும்.",
    "Telugu":    "🎙 వాయిస్ మెసేజ్ స్పష్టంగా లేదు. మళ్ళీ పంపండి.",
    "Kannada":   "🎙 ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಸ್ಪಷ್ಟವಾಗಿಲ್ಲ. ಮತ್ತೆ ಕಳುಹಿಸಿ.",
    "Malayalam": "🎙 വോയ്സ് മെസേജ് വ്യക്തമല്ല. വീണ്ടും അയക്കൂ.",
    "Hindi":     "🎙 आवाज संदेश स्पष्ट नहीं था। कृपया दोबारा भेजें।",
    "Punjabi":   "🎙 ਵੌਇਸ ਮੈਸੇਜ ਸਾਫ਼ ਨਹੀਂ ਸੀ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਭੇਜੋ।",
    "Gujarati":  "🎙 વૉઇસ મેસેજ સ્પષ્ટ ન હતો. ફરી મોકલો.",
    "Marathi":   "🎙 व्हॉइस मेसेज स्पष्ट नव्हता. पुन्हा पाठवा.",
    "Bengali":   "🎙 ভয়েস মেসেজ পরিষ্কার ছিল না। আবার পাঠান।",
    "Odia":      "🎙 ଭଏସ ମେସେଜ ସ୍ପଷ୍ଟ ନ ଥିଲା। ପୁଣି ପଠାନ୍ତୁ।",
    "English":   "🎙 Voice message wasn't clear. Please send it again.",
}

ASK_MANDI_CROP = {
    "Tamil":     "🌾 எந்த பயிரின் மண்டி விலை வேண்டும்?",
    "Telugu":    "🌾 ఏ పంట మండీ ధర కావాలి?",
    "Kannada":   "🌾 ಯಾವ ಬೆಳೆಯ ಮಂಡಿ ಬೆಲೆ ಬೇಕು?",
    "Malayalam": "🌾 ഏത് വിളയുടെ മണ്ടി വില അറിയണം?",
    "Hindi":     "🌾 किस फसल का मंडी भाव चाहिए?",
    "Punjabi":   "🌾 ਕਿਹੜੀ ਫਸਲ ਦਾ ਮੰਡੀ ਭਾਅ ਚਾਹੀਦਾ ਹੈ?",
    "Gujarati":  "🌾 કઈ ફસલ નો મંડી ભાવ જોઈએ?",
    "Marathi":   "🌾 कोणत्या पिकाचा मंडी भाव हवा आहे?",
    "Bengali":   "🌾 কোন ফসলের মান্ডি দাম জানতে চান?",
    "Odia":      "🌾 କେଉଁ ଫସଲ ମଣ୍ଡି ମୂଲ୍ୟ ଜାଣିବାକୁ ଚାହୁଁଛନ୍ତି?",
    "English":   "🌾 Which crop's mandi price do you want?",
}

ASK_MANDI_CROP_NAME = {
    "Tamil":     "பயிரின் பெயரை தட்டச்சு செய்யவும். (எ.கா: நெல், வேர்க்கடலை)",
    "Telugu":    "పంట పేరు టైప్ చేయండి. (ఉదా: వరి, వేరుశనగ)",
    "Kannada":   "ಬೆಳೆ ಹೆಸರು ಟೈಪ್ ಮಾಡಿ. (ಉದಾ: ಭತ್ತ, ಶೇಂಗಾ)",
    "Malayalam": "വിള പേര് ടൈപ്പ് ചെയ്യൂ. (ഉദാ: നെല്ല്, നിലക്കടല)",
    "Hindi":     "फसल का नाम टाइप करें। (जैसे: धान, मूंगफली)",
    "Punjabi":   "ਫਸਲ ਦਾ ਨਾਮ ਟਾਈਪ ਕਰੋ। (ਜਿਵੇਂ: ਝੋਨਾ, ਮੂੰਗਫਲੀ)",
    "Gujarati":  "ફસલ નું નામ ટાઇપ કરો. (ઉદા: ડાંગર, મગફળી)",
    "Marathi":   "पिकाचे नाव टाइप करा. (उदा: भात, भुईमूग)",
    "Bengali":   "ফসলের নাম টাইপ করুন। (যেমন: ধান, চিনাবাদাম)",
    "Odia":      "ଫସଲ ନାମ ଟାଇପ କରନ୍ତୁ। (ଯେପରି: ଧାନ, ଚିନାବାଦାମ)",
    "English":   "Type the crop name. (e.g. paddy, groundnut)",
}

FETCHING_MANDI = {
    "Tamil":     "🔍 {crop} மண்டி விலைகளை பெறுகிறேன்...",
    "Telugu":    "🔍 {crop} మండీ ధరలు తెస్తున్నాను...",
    "Kannada":   "🔍 {crop} ಮಂಡಿ ಬೆಲೆ ತರುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🔍 {crop} മണ്ടി വില കൊണ്ടുവരുന്നു...",
    "Hindi":     "🔍 {crop} मंडी भाव ला रहा हूँ...",
    "Punjabi":   "🔍 {crop} ਮੰਡੀ ਭਾਅ ਲਿਆ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "🔍 {crop} મંડી ભાવ લઈ આવું છું...",
    "Marathi":   "🔍 {crop} मंडी भाव आणत आहे...",
    "Bengali":   "🔍 {crop} মান্ডি দাম আনছি...",
    "Odia":      "🔍 {crop} ମଣ୍ଡି ମୂଲ୍ୟ ଆଣୁଛି...",
    "English":   "🔍 Fetching {crop} mandi prices...",
}

DISEASE_PROMPT = {
    "Tamil":     "📸 பயிர் நோய் படத்தை அனுப்பவும் அல்லது அறிகுறிகளை விவரிக்கவும்:",
    "Telugu":    "📸 పంట వ్యాధి ఫోటో పంపండి లేదా లక్షణాలు వివరించండి:",
    "Kannada":   "📸 ಬೆಳೆ ರೋಗದ ಫೋಟೋ ಕಳುಹಿಸಿ ಅಥವಾ ಲಕ್ಷಣಗಳನ್ನು ವಿವರಿಸಿ:",
    "Malayalam": "📸 കൃഷി രോഗത്തിന്റെ ഫോട്ടോ അയക്കൂ അല്ലെങ്കിൽ ലക്ഷണങ്ങൾ വിവരിക്കൂ:",
    "Hindi":     "📸 फसल की बीमारी की फोटो भेजें या लक्षण बताएं:",
    "Punjabi":   "📸 ਫਸਲ ਦੀ ਬੀਮਾਰੀ ਦੀ ਫੋਟੋ ਭੇਜੋ ਜਾਂ ਲੱਛਣ ਦੱਸੋ:",
    "Gujarati":  "📸 ફસલ ના રોગ નો ફોટો મોકલો અથવા લક્ષણો વર્ણવો:",
    "Marathi":   "📸 पिकाच्या रोगाचा फोटो पाठवा किंवा लक्षणे सांगा:",
    "Bengali":   "📸 ফসলের রোগের ছবি পাঠান বা লক্ষণ বর্ণনা করুন:",
    "Odia":      "📸 ଫସଲ ରୋଗ ଫୋଟୋ ପଠାନ୍ତୁ ବା ଲକ୍ଷଣ ବର୍ଣ୍ଣନା କରନ୍ତୁ:",
    "English":   "📸 Send a photo of the crop disease or describe the symptoms:",
}

ANALYSING_IMAGE = {
    "Tamil":     "🔬 படத்தை ஆய்வு செய்கிறேன்...",
    "Telugu":    "🔬 చిత్రాన్ని విశ్లేషిస్తున్నాను...",
    "Kannada":   "🔬 ಚಿತ್ರ ವಿಶ್ಲೇಷಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🔬 ചിത്രം വിശകലനം ചെയ്യുന്നു...",
    "Hindi":     "🔬 तस्वीर का विश्लेषण कर रहा हूँ...",
    "Punjabi":   "🔬 ਤਸਵੀਰ ਦਾ ਵਿਸ਼ਲੇਸ਼ਣ ਕਰ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "🔬 ચિત્ર વિશ્લેષણ કરું છું...",
    "Marathi":   "🔬 चित्राचे विश्लेषण करत आहे...",
    "Bengali":   "🔬 ছবি বিশ্লেষণ করছি...",
    "Odia":      "🔬 ଛବି ବିଶ୍ଲେଷଣ କରୁଛି...",
    "English":   "🔬 Analysing the image...",
}

CHECKING_SYMPTOMS = {
    "Tamil":     "🔍 அறிகுறிகளை சரிபார்க்கிறேன்...",
    "Telugu":    "🔍 లక్షణాలు తనిఖీ చేస్తున్నాను...",
    "Kannada":   "🔍 ಲಕ್ಷಣಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🔍 ലക്ഷണങ്ങൾ പരിശോധിക്കുന്നു...",
    "Hindi":     "🔍 लक्षण जाँच रहा हूँ...",
    "Punjabi":   "🔍 ਲੱਛਣ ਜਾਂਚ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "🔍 લક્ષણો તપાસું છું...",
    "Marathi":   "🔍 लक्षणे तपासत आहे...",
    "Bengali":   "🔍 লক্ষণ পরীক্ষা করছি...",
    "Odia":      "🔍 ଲକ୍ଷଣ ଯାଞ୍ଚ କରୁଛି...",
    "English":   "🔍 Checking the symptoms...",
}

DISEASE_VOICE_UNCLEAR = {
    "Tamil":     "🎙 குரல் செய்தி தெளிவாக இல்லை. நோய் அறிகுறிகளை விவரிக்கவும்.",
    "Telugu":    "🎙 వాయిస్ స్పష్టంగా లేదు. వ్యాధి లక్షణాలు వివరించండి.",
    "Kannada":   "🎙 ವಾಯ್ಸ್ ಸ್ಪಷ್ಟವಾಗಿಲ್ಲ. ರೋಗ ಲಕ್ಷಣಗಳನ್ನು ವಿವರಿಸಿ.",
    "Malayalam": "🎙 വോയ്സ് വ്യക്തമല്ല. ലക്ഷണങ്ങൾ വിവരിക്കൂ.",
    "Hindi":     "🎙 आवाज स्पष्ट नहीं। कृपया रोग के लक्षण बताएं।",
    "Punjabi":   "🎙 ਆਵਾਜ਼ ਸਾਫ਼ ਨਹੀਂ ਸੀ। ਕਿਰਪਾ ਕਰਕੇ ਬਿਮਾਰੀ ਦੇ ਲੱਛਣ ਦੱਸੋ।",
    "Gujarati":  "🎙 અવાજ સ્પષ્ટ ન હતો. કૃપા કરી રોગ ના લક્ષણો જણાવો.",
    "Marathi":   "🎙 आवाज स्पष्ट नव्हता. कृपया रोगाची लक्षणे सांगा.",
    "Bengali":   "🎙 আওয়াজ স্পষ্ট ছিল না। দয়া করে রোগের লক্ষণ বলুন।",
    "Odia":      "🎙 ଶବ୍ଦ ସ୍ପଷ୍ଟ ନ ଥିଲା। ଦୟାକରି ରୋଗ ଲକ୍ଷଣ ବୁଝାନ୍ତୁ।",
    "English":   "🎙 Voice wasn't clear. Please describe the disease symptoms.",
}

DISEASE_TEXT_PROMPT = {
    "Tamil":     "நோய் அறிகுறிகளை தட்டச்சு செய்யவும்:",
    "Telugu":    "వ్యాధి లక్షణాలను టైప్ చేయండి:",
    "Kannada":   "ರೋಗ ಲಕ್ಷಣಗಳನ್ನು ಟೈಪ್ ಮಾಡಿ:",
    "Malayalam": "ലക്ഷണങ്ങൾ ടൈപ്പ് ചെയ്യൂ:",
    "Hindi":     "रोग के लक्षण टाइप करें:",
    "Punjabi":   "ਬਿਮਾਰੀ ਦੇ ਲੱਛਣ ਟਾਈਪ ਕਰੋ:",
    "Gujarati":  "રોગ ના લક્ષણો ટાઇપ કરો:",
    "Marathi":   "रोगाची लक्षणे टाइप करा:",
    "Bengali":   "রোগের লক্ষণ টাইপ করুন:",
    "Odia":      "ରୋଗ ଲକ୍ଷଣ ଟାଇପ କରନ୍ତୁ:",
    "English":   "Type the disease symptoms:",
}

IMAGE_ANALYSE_FAIL = {
    "Tamil":     "❌ படத்தை ஆய்வு செய்ய முடியவில்லை. அறிகுறிகளை விவரிக்கவும்.",
    "Telugu":    "❌ చిత్రాన్ని విశ్లేషించలేకపోయాను. లక్షణాలు వివరించండి.",
    "Kannada":   "❌ ಚಿತ್ರ ವಿಶ್ಲೇಷಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ಲಕ್ಷಣಗಳನ್ನು ವಿವರಿಸಿ.",
    "Malayalam": "❌ ചിത്രം വിശകലനം ചെയ്യാൻ കഴിഞ്ഞില്ല. ലക്ഷണങ്ങൾ വിവരിക്കൂ.",
    "Hindi":     "❌ तस्वीर का विश्लेषण नहीं हो सका। लक्षण बताएं।",
    "Punjabi":   "❌ ਤਸਵੀਰ ਦਾ ਵਿਸ਼ਲੇਸ਼ਣ ਨਹੀਂ ਹੋ ਸਕਿਆ। ਲੱਛਣ ਦੱਸੋ।",
    "Gujarati":  "❌ ચિત્ર વિશ્લેષણ ન થઈ શક્યું. લક્ષણો જણાવો.",
    "Marathi":   "❌ चित्राचे विश्लेषण होऊ शकले नाही. लक्षणे सांगा.",
    "Bengali":   "❌ ছবি বিশ্লেষণ করা যায়নি। লক্ষণ বলুন।",
    "Odia":      "❌ ଛବି ବିଶ୍ଲେଷଣ ହୋଇ ପାରିଲା ନାହିଁ। ଲକ୍ଷଣ ବୁଝାନ୍ତୁ।",
    "English":   "❌ Could not analyse the image. Please describe the symptoms.",
}

SET_NEWS_TIME = {
    "Tamil":     "⏰ நீங்கள் தினசரி செய்திகளை எத்தனை மணிக்கு பெற விரும்புகிறீர்கள்?",
    "Telugu":    "⏰ మీరు ప్రతిరోజు వార్తలు ఏ సమయంలో అందుకోవాలనుకుంటున్నారు?",
    "Kannada":   "⏰ ನೀವು ಪ್ರತಿದಿನ ಸುದ್ದಿ ಯಾವ ಸಮಯದಲ್ಲಿ ಸ್ವೀಕರಿಸಲು ಬಯಸುತ್ತೀರಿ?",
    "Malayalam": "⏰ ദൈനംദിന വാർത്ത ഏത് സമയത്ത് ലഭിക്കണം?",
    "Hindi":     "⏰ आप रोज़ समाचार किस समय पाना चाहते हैं?",
    "Punjabi":   "⏰ ਤੁਸੀਂ ਰੋਜ਼ਾਨਾ ਖ਼ਬਰਾਂ ਕਿਸ ਸਮੇਂ ਪ੍ਰਾਪਤ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?",
    "Gujarati":  "⏰ તમે રોજ સમાચાર ક્યારે મેળવવા માંગો છો?",
    "Marathi":   "⏰ तुम्हाला दररोज बातम्या कोणत्या वेळी हव्या आहेत?",
    "Bengali":   "⏰ আপনি প্রতিদিন কখন সংবাদ পেতে চান?",
    "Odia":      "⏰ ଆପଣ ପ୍ରତିଦିନ କେତେ ସମୟ ଖବର ପ୍ରାପ୍ତ କରିବାକୁ ଚାହୁଁଛନ୍ତି?",
    "English":   "⏰ What time do you want to receive daily news?",
}

NEWS_TIME_SET = {
    "Tamil":     "✅ தினசரி செய்திகள் {time} ({tz}) மணிக்கு அனுப்பப்படும்.",
    "Telugu":    "✅ రోజువారీ వార్తలు {time} ({tz}) కి పంపబడతాయి.",
    "Kannada":   "✅ ದಿನದ ಸುದ್ದಿ {time} ({tz}) ಕ್ಕೆ ಕಳುಹಿಸಲಾಗುತ್ತದೆ.",
    "Malayalam": "✅ ദൈനംദിന വാർത്ത {time} ({tz}) ന് അയക്കും.",
    "Hindi":     "✅ दैनिक समाचार {time} ({tz}) बजे भेजे जाएंगे।",
    "Punjabi":   "✅ ਰੋਜ਼ਾਨਾ ਖ਼ਬਰਾਂ {time} ({tz}) ਵਜੇ ਭੇਜੀਆਂ ਜਾਣਗੀਆਂ।",
    "Gujarati":  "✅ દૈનિક સમાચાર {time} ({tz}) વાગ્યે મોકલાશે.",
    "Marathi":   "✅ दैनंदिन बातम्या {time} ({tz}) ला पाठवल्या जातील.",
    "Bengali":   "✅ প্রতিদিন {time} ({tz}) তে সংবাদ পাঠানো হবে।",
    "Odia":      "✅ ଦୈନିକ ସମ୍ବାଦ {time} ({tz}) ରେ ପଠାଯିବ।",
    "English":   "✅ Daily news will be sent at {time} ({tz}).",
}

PROFILE_VIEW = {
    "Tamil":     "👤 *என் விவரம்*\n\nபெயர்: {name}\nபயிர்: {crop}\nகிராமம்: {village}\nமாவட்டம்: {district}\nமொழி: {language}\nசெய்தி நேரம்: {time} ({tz})",
    "Telugu":    "👤 *నా ప్రొఫైల్*\n\nపేరు: {name}\nపంట: {crop}\nగ్రామం: {village}\nజిల్లా: {district}\nభాష: {language}\nవార్తా సమయం: {time} ({tz})",
    "Kannada":   "👤 *ನನ್ನ ಪ್ರೊಫೈಲ್*\n\nಹೆಸರು: {name}\nಬೆಳೆ: {crop}\nಗ್ರಾಮ: {village}\nಜಿಲ್ಲೆ: {district}\nಭಾಷೆ: {language}\nಸುದ್ದಿ ಸಮಯ: {time} ({tz})",
    "Malayalam": "👤 *എന്റെ പ്രൊഫൈൽ*\n\nപേര്: {name}\nവിള: {crop}\nഗ്രാമം: {village}\nജില്ല: {district}\nഭാഷ: {language}\nവാർത്ത സമയം: {time} ({tz})",
    "Hindi":     "👤 *मेरी प्रोफाइल*\n\nनाम: {name}\nफसल: {crop}\nगांव: {village}\nजिला: {district}\nभाषा: {language}\nसमाचार समय: {time} ({tz})",
    "Punjabi":   "👤 *ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ*\n\nਨਾਮ: {name}\nਫ਼ਸਲ: {crop}\nਪਿੰਡ: {village}\nਜ਼ਿਲ੍ਹਾ: {district}\nਭਾਸ਼ਾ: {language}\nਖ਼ਬਰ ਸਮਾਂ: {time} ({tz})",
    "Gujarati":  "👤 *મારી પ્રોફાઇલ*\n\nનામ: {name}\nફસલ: {crop}\nગામ: {village}\nજિલ્લો: {district}\nભાષા: {language}\nસમાચારનો સમય: {time} ({tz})",
    "Marathi":   "👤 *माझी प्रोफाइल*\n\nनाव: {name}\nपीक: {crop}\nगाव: {village}\nजिल्हा: {district}\nभाषा: {language}\nबातम्यांची वेळ: {time} ({tz})",
    "Bengali":   "👤 *আমার প্রোফাইল*\n\nনাম: {name}\nফসল: {crop}\nগ্রাম: {village}\nজেলা: {district}\nভাষা: {language}\nসংবাদের সময়: {time} ({tz})",
    "Odia":      "👤 *ମୋ ପ୍ରୋଫାଇଲ୍*\n\nନାମ: {name}\nଫସଲ: {crop}\nଗ୍ରାମ: {village}\nଜିଲ୍ଲା: {district}\nଭାଷା: {language}\nଖବର ସମୟ: {time} ({tz})",
    "English":   "👤 *My Profile*\n\nName: {name}\nCrop: {crop}\nVillage: {village}\nDistrict: {district}\nLanguage: {language}\nNews time: {time} ({tz})",
}

FINDING_FARMERS = {
    "Tamil":     "🔍 {crop} விவசாயிகளை தேடுகிறேன்...",
    "Telugu":    "🔍 {crop} రైతులను వెతుకుతున్నాను...",
    "Kannada":   "🔍 {crop} ರೈತರನ್ನು ಹುಡುಕುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🔍 {crop} കർഷകരെ തിരയുന്നു...",
    "Hindi":     "🔍 {crop} किसानों को ढूंढ रहा हूँ...",
    "Punjabi":   "🔍 {crop} ਕਿਸਾਨਾਂ ਨੂੰ ਲੱਭ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "🔍 {crop} ખેડૂતો શોધી રહ્યો છું...",
    "Marathi":   "🔍 {crop} शेतकऱ्यांना शोधत आहे...",
    "Bengali":   "🔍 {crop} কৃষকদের খুঁজছি...",
    "Odia":      "🔍 {crop} ଚାଷୀ ଖୋଜୁଛି...",
    "English":   "🔍 Looking for {crop} farmers near you...",
}

NO_FARMERS_NEARBY = {
    "Tamil":     "😔 உங்கள் பகுதியில் {crop} விவசாயிகள் யாரும் இல்லை.",
    "Telugu":    "😔 మీ ప్రాంతంలో {crop} రైతులు ఎవరూ లేరు.",
    "Kannada":   "😔 ನಿಮ್ಮ ಪ್ರದೇಶದಲ್ಲಿ {crop} ರೈತರು ಯಾರೂ ಇಲ್ಲ.",
    "Malayalam": "😔 നിങ്ങളുടെ പ്രദേശത്ത് {crop} കർഷകർ ആരും ഇല്ല.",
    "Hindi":     "😔 आपके क्षेत्र में {crop} के कोई किसान नहीं मिले।",
    "Punjabi":   "😔 ਤੁਹਾਡੇ ਖੇਤਰ ਵਿੱਚ {crop} ਦੇ ਕੋਈ ਕਿਸਾਨ ਨਹੀਂ ਮਿਲੇ।",
    "Gujarati":  "😔 તમારા વિસ્તારમાં {crop} ના ખેડૂત ન મળ્યા.",
    "Marathi":   "😔 तुमच्या परिसरात {crop} चे कोणते शेतकरी नाहीत.",
    "Bengali":   "😔 আপনার এলাকায় {crop} কৃষক পাওয়া যায়নি।",
    "Odia":      "😔 ଆପଣଙ୍କ ଅଞ୍ଚଳରେ {crop} ଚାଷୀ ମିଳିଲେ ନାହିଁ।",
    "English":   "😔 No {crop} farmers found in your area.",
}

FARMERS_FOUND_HEADER = {
    "Tamil":     "👥 *{crop} விவசாயிகள்* ({count} பேர் கண்டுபிடிக்கப்பட்டனர்):",
    "Telugu":    "👥 *{crop} రైతులు* ({count} మంది కనుగొనబడ్డారు):",
    "Kannada":   "👥 *{crop} ರೈತರು* ({count} ಜನರು ಕಂಡುಬಂದರು):",
    "Malayalam": "👥 *{crop} കർഷകർ* ({count} പേർ കണ്ടെത്തി):",
    "Hindi":     "👥 *{crop} किसान* ({count} मिले):",
    "Punjabi":   "👥 *{crop} ਕਿਸਾਨ* ({count} ਮਿਲੇ):",
    "Gujarati":  "👥 *{crop} ખેડૂત* ({count} મળ્યા):",
    "Marathi":   "👥 *{crop} शेतकरी* ({count} सापडले):",
    "Bengali":   "👥 *{crop} কৃষক* ({count} জন পাওয়া গেছে):",
    "Odia":      "👥 *{crop} ଚାଷୀ* ({count} ଜଣ ମିଳିଲେ):",
    "English":   "👥 *{crop} Farmers* ({count} found):",
}

COMPLETE_PROFILE_FIRST = {
    "Tamil":     "முதலில் உங்கள் விவரங்களை பூர்த்தி செய்யவும். /start என்று தட்டச்சு செய்யவும்.",
    "Telugu":    "మొదట మీ ప్రొఫైల్ పూర్తి చేయండి. /start అని టైప్ చేయండి.",
    "Kannada":   "ಮೊದಲು ನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ಪೂರ್ಣಗೊಳಿಸಿ. /start ಎಂದು ಟೈಪ್ ಮಾಡಿ.",
    "Malayalam": "ആദ്യം നിങ്ങളുടെ പ്രൊഫൈൽ പൂർത്തിയാക്കൂ. /start ടൈപ്പ് ചെയ്യൂ.",
    "Hindi":     "पहले अपनी प्रोफाइल पूरी करें। /start टाइप करें।",
    "Punjabi":   "ਪਹਿਲਾਂ ਆਪਣੀ ਪ੍ਰੋਫਾਈਲ ਪੂਰੀ ਕਰੋ। /start ਟਾਈਪ ਕਰੋ।",
    "Gujarati":  "પ્રથમ તમારી પ્રોફાઇલ પૂર્ણ કરો. /start ટાઇપ કરો.",
    "Marathi":   "आधी तुमची प्रोफाइल पूर्ण करा. /start टाइप करा.",
    "Bengali":   "প্রথমে আপনার প্রোফাইল সম্পূর্ণ করুন। /start টাইপ করুন।",
    "Odia":      "ପ୍ରଥମେ ଆପଣଙ୍କ ପ୍ରୋଫାଇଲ ସମ୍ପୂର୍ଣ୍ଣ କରନ୍ତୁ। /start ଟାଇପ କରନ୍ତୁ।",
    "English":   "Please complete your profile first. Type /start.",
}

USE_MENU = {
    "Tamil":     "கீழே உள்ள மெனுவைப் பயன்படுத்தவும்.",
    "Telugu":    "దయచేసి క్రింది మెనూని ఉపయోగించండి.",
    "Kannada":   "ದಯವಿಟ್ಟು ಕೆಳಗಿನ ಮೆನು ಬಳಸಿ.",
    "Malayalam": "ദയവായി ചുവടെ ഉള്ള മെനു ഉപയോഗിക്കൂ.",
    "Hindi":     "कृपया नीचे दिए मेनू का उपयोग करें।",
    "Punjabi":   "ਕਿਰਪਾ ਕਰਕੇ ਹੇਠਾਂ ਦਿੱਤੇ ਮੀਨੂ ਦੀ ਵਰਤੋਂ ਕਰੋ।",
    "Gujarati":  "કૃપા કરી નીચે આપેલ મેન્યૂ વાપરો.",
    "Marathi":   "कृपया खालील मेनू वापरा.",
    "Bengali":   "অনুগ্রহ করে নিচের মেনু ব্যবহার করুন।",
    "Odia":      "ଦୟାକରି ତଳ ମେନୁ ବ୍ୟବହାର କରନ୍ତୁ।",
    "English":   "Please use the menu below.",
}

TYPE_QUESTION = {
    "Tamil":     "உங்கள் கேள்வியை தட்டச்சு செய்யவும்:",
    "Telugu":    "మీ ప్రశ్న టైప్ చేయండి:",
    "Kannada":   "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ:",
    "Malayalam": "നിങ്ങളുടെ ചോദ്യം ടൈപ്പ് ചെയ്യൂ:",
    "Hindi":     "अपना सवाल टाइप करें:",
    "Punjabi":   "ਆਪਣਾ ਸਵਾਲ ਟਾਈਪ ਕਰੋ:",
    "Gujarati":  "તમારો પ્રશ્ન ટાઇપ કરો:",
    "Marathi":   "तुमचा प्रश्न टाइप करा:",
    "Bengali":   "আপনার প্রশ্ন টাইপ করুন:",
    "Odia":      "ଆପଣଙ୍କ ପ୍ରଶ୍ନ ଟାଇପ କରନ୍ତୁ:",
    "English":   "Type your question:",
}

CANCELLED = {
    "Tamil":     "❌ ரத்து செய்யப்பட்டது. மெனுவைப் பயன்படுத்தவும்.",
    "Telugu":    "❌ రద్దు చేయబడింది. మెనూని ఉపయోగించండి.",
    "Kannada":   "❌ ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ. ಮೆನು ಬಳಸಿ.",
    "Malayalam": "❌ റദ്ദാക്കി. മെനു ഉപയോഗിക്കൂ.",
    "Hindi":     "❌ रद्द किया गया। मेनू का उपयोग करें।",
    "Punjabi":   "❌ ਰੱਦ ਕੀਤਾ ਗਿਆ। ਮੀਨੂ ਵਰਤੋ।",
    "Gujarati":  "❌ રદ્દ કરવામાં આવ્યું. મેન્યૂ વાપરો.",
    "Marathi":   "❌ रद्द केले. मेनू वापरा.",
    "Bengali":   "❌ বাতিল করা হয়েছে। মেনু ব্যবহার করুন।",
    "Odia":      "❌ ବାତିଲ ହୋଇଛି। ମେନୁ ବ୍ୟବହାର କରନ୍ତୁ।",
    "English":   "❌ Cancelled. Use the menu.",
}

ERROR_GENERIC = {
    "Tamil":     "❌ ஒரு பிழை ஏற்பட்டது. மீண்டும் முயற்சிக்கவும்.",
    "Telugu":    "❌ లోపం వచ్చింది. మళ్ళీ ప్రయత్నించండి.",
    "Kannada":   "❌ ದೋಷ ಸಂಭವಿಸಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "Malayalam": "❌ ഒരു പിശക് ഉണ്ടായി. വീണ്ടും ശ്രമിക്കൂ.",
    "Hindi":     "❌ एक त्रुटि हुई। कृपया दोबारा कोशिश करें।",
    "Punjabi":   "❌ ਇੱਕ ਗਲਤੀ ਹੋਈ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
    "Gujarati":  "❌ ભૂલ થઈ. ફરી પ્રયત્ન કરો.",
    "Marathi":   "❌ एक चूक झाली. पुन्हा प्रयत्न करा.",
    "Bengali":   "❌ একটি ত্রুটি হয়েছে। আবার চেষ্টা করুন।",
    "Odia":      "❌ ଏକ ତ୍ରୁଟି ଘଟିଲା। ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।",
    "English":   "❌ An error occurred. Please try again.",
}

FALLBACK = {
    "Tamil":     "மன்னிக்கவும், புரிந்துகொள்ள முடியவில்லை. மெனுவைப் பயன்படுத்தவும்.",
    "Telugu":    "క్షమించండి, అర్థం కాలేదు. మెనూ వాడండి.",
    "Kannada":   "ಕ್ಷಮಿಸಿ, ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲಾಗಲಿಲ್ಲ. ಮೆನು ಬಳಸಿ.",
    "Malayalam": "ക്ഷമിക്കൂ, മനസ്സിലായില്ല. മെനു ഉപയോഗിക്കൂ.",
    "Hindi":     "माफ करें, समझ नहीं पाया। मेनू का उपयोग करें।",
    "Punjabi":   "ਮਾਫ਼ ਕਰਨਾ, ਸਮਝ ਨਹੀਂ ਆਇਆ। ਮੀਨੂ ਵਰਤੋ।",
    "Gujarati":  "માફ કરો, સમજ ન આવ્યું. મેન્યૂ વાપરો.",
    "Marathi":   "माफ करा, समजले नाही. मेनू वापरा.",
    "Bengali":   "দুঃখিত, বুঝতে পারিনি। মেনু ব্যবহার করুন।",
    "Odia":      "ମାଫ୍ କରନ୍ତୁ, ବୁଝି ହେଲା ନାହିଁ। ମେନୁ ବ୍ୟବହାର କରନ୍ତୁ।",
    "English":   "Sorry, I didn't understand. Please use the menu.",
}

LOCATION_DETECTED = {
    "Tamil":     "📍 கண்டறியப்பட்டது: {village}, {district} ({tz})\n\nதயவுசெய்து உங்கள் மொழியை தேர்ந்தெடுக்கவும்:",
    "Telugu":    "📍 గుర్తించబడింది: {village}, {district} ({tz})\n\nమీ భాషను ఎంచుకోండి:",
    "Kannada":   "📍 ಗುರುತಿಸಲಾಗಿದೆ: {village}, {district} ({tz})\n\nನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ:",
    "Malayalam": "📍 കണ്ടെത്തി: {village}, {district} ({tz})\n\nഭാഷ തിരഞ്ഞെടുക്കൂ:",
    "Hindi":     "📍 पहचाना गया: {village}, {district} ({tz})\n\nअपनी भाषा चुनें:",
    "Punjabi":   "📍 ਪਛਾਣਿਆ ਗਿਆ: {village}, {district} ({tz})\n\nਆਪਣੀ ਭਾਸ਼ਾ ਚੁਣੋ:",
    "Gujarati":  "📍 ઓળખાયું: {village}, {district} ({tz})\n\nતમારી ભાષા પસંદ કરો:",
    "Marathi":   "📍 ओळखले: {village}, {district} ({tz})\n\nतुमची भाषा निवडा:",
    "Bengali":   "📍 সনাক্ত হয়েছে: {village}, {district} ({tz})\n\nআপনার ভাষা বেছে নিন:",
    "Odia":      "📍 ଚିହ୍ନଟ ହୋଇଛି: {village}, {district} ({tz})\n\nଆପଣଙ୍କ ଭାଷା ବାଛନ୍ତୁ:",
    "English":   "📍 Detected: {village}, {district} ({tz})\n\nPlease choose your language:",
}

# ── Chat Room strings ──────────────────────────────────────────────────

CHAT_WITH = {
    "Tamil":     "💬 *{partner} உடன் அரட்டை*\n\n📜 கடைசி {n} செய்திகள்:\n{history}",
    "Telugu":    "💬 *{partner} తో చాట్*\n\n📜 చివరి {n} సందేశాలు:\n{history}",
    "Kannada":   "💬 *{partner} ಜೊತೆ ಚಾಟ್*\n\n📜 ಕೊನೆಯ {n} ಸಂದೇಶಗಳು:\n{history}",
    "Malayalam": "💬 *{partner} ഉമായി ചാറ്റ്*\n\n📜 അവസാന {n} സന്ദേശങ്ങൾ:\n{history}",
    "Hindi":     "💬 *{partner} के साथ चैट*\n\n📜 अंतिम {n} संदेश:\n{history}",
    "Punjabi":   "💬 *{partner} ਨਾਲ ਚੈਟ*\n\n📜 ਆਖਰੀ {n} ਸੁਨੇਹੇ:\n{history}",
    "Gujarati":  "💬 *{partner} સાથે ચેટ*\n\n📜 છેલ્લા {n} સંદેશ:\n{history}",
    "Marathi":   "💬 *{partner} सोबत चॅट*\n\n📜 शेवटचे {n} संदेश:\n{history}",
    "Bengali":   "💬 *{partner} এর সাথে চ্যাট*\n\n📜 শেষ {n} বার্তা:\n{history}",
    "Odia":      "💬 *{partner} ସହ ଚ୍ୟାଟ*\n\n📜 ଶେଷ {n} ବାର୍ତ୍ତା:\n{history}",
    "English":   "💬 *Chat with {partner}*\n\n📜 Last {n} messages:\n{history}",
}

CHOOSE_CHAT_PARTNER = {
    "Tamil":     "👥 *{crop} விவசாயிகள்*\nகதைக்க யாரை தேர்வு செய்கிறீர்கள்?",
    "Telugu":    "👥 *{crop} రైతులు*\nఎవరితో చాట్ చేయాలనుకుంటున్నారు?",
    "Kannada":   "👥 *{crop} ರೈತರು*\nಯಾರೊಂದಿಗೆ ಚಾಟ್ ಮಾಡಲು ಬಯಸುತ್ತೀರಿ?",
    "Malayalam": "👥 *{crop} കർഷകർ*\nആരുമായി ചാറ്റ് ചെയ്യണം?",
    "Hindi":     "👥 *{crop} किसान*\nकिसके साथ बात करना चाहते हैं?",
    "Punjabi":   "👥 *{crop} ਕਿਸਾਨ*\nਕਿਸ ਨਾਲ ਗੱਲ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?",
    "Gujarati":  "👥 *{crop} ખેડૂત*\nકોની સાથે વાત કરવી છે?",
    "Marathi":   "👥 *{crop} शेतकरी*\nकोणाशी बोलायचे आहे?",
    "Bengali":   "👥 *{crop} কৃষক*\nকার সাথে কথা বলতে চান?",
    "Odia":      "👥 *{crop} ଚାଷୀ*\nକାହା ସହ କଥା ହେବାକୁ ଚାହୁଁଛନ୍ତି?",
    "English":   "👥 *{crop} Farmers*\nWho would you like to chat with?",
}

CONNECTED_TO = {
    "Tamil":     "✅ *{partner}* உடன் இணைக்கப்பட்டீர்கள்!\n\n{history}",
    "Telugu":    "✅ *{partner}* తో కనెక్ట్ అయ్యారు!\n\n{history}",
    "Kannada":   "✅ *{partner}* ಜೊತೆ ಸಂಪರ್ಕ ಹೊಂದಿದ್ದೀರಿ!\n\n{history}",
    "Malayalam": "✅ *{partner}* ഉമായി ബന്ധിപ്പിച്ചു!\n\n{history}",
    "Hindi":     "✅ *{partner}* से जुड़ गए!\n\n{history}",
    "Punjabi":   "✅ *{partner}* ਨਾਲ ਜੁੜ ਗਏ!\n\n{history}",
    "Gujarati":  "✅ *{partner}* સાથે જોડાઈ ગયા!\n\n{history}",
    "Marathi":   "✅ *{partner}* शी जोडले गेले!\n\n{history}",
    "Bengali":   "✅ *{partner}* এর সাথে সংযুক্ত!\n\n{history}",
    "Odia":      "✅ *{partner}* ସହ ସଂଯୁକ୍ତ!\n\n{history}",
    "English":   "✅ Connected to *{partner}*!\n\n{history}",
}

LEFT_CHAT = {
    "Tamil":     "👋 நீங்கள் அரட்டையை விட்டு வெளியேறினீர்கள்.",
    "Telugu":    "👋 మీరు చాట్ వదిలి వెళ్ళారు.",
    "Kannada":   "👋 ನೀವು ಚಾಟ್ ಬಿಟ್ಟಿದ್ದೀರಿ.",
    "Malayalam": "👋 നിങ്ങൾ ചാറ്റ് വിട്ടു.",
    "Hindi":     "👋 आप चैट छोड़ चुके हैं।",
    "Punjabi":   "👋 ਤੁਸੀਂ ਚੈਟ ਛੱਡ ਦਿੱਤੀ ਹੈ।",
    "Gujarati":  "👋 તમે ચેટ છોડ્યું.",
    "Marathi":   "👋 तुम्ही चॅट सोडली.",
    "Bengali":   "👋 আপনি চ্যাট ছেড়ে দিয়েছেন।",
    "Odia":      "👋 ଆପଣ ଚ୍ୟାଟ ଛାଡ଼ିଛନ୍ତି।",
    "English":   "👋 You have left the chat.",
}

WANT_TO_CHAT = {
    "Tamil":     "💬 *{name}* உங்களுடன் அரட்டை அடிக்க விரும்புகிறார்!",
    "Telugu":    "💬 *{name}* మీతో చాట్ చేయాలనుకుంటున్నారు!",
    "Kannada":   "💬 *{name}* ನಿಮ್ಮೊಂದಿಗೆ ಚಾಟ್ ಮಾಡಲು ಬಯಸುತ್ತಾರೆ!",
    "Malayalam": "💬 *{name}* നിങ്ങളുമായി ചാറ്റ് ചെയ്യാൻ ആഗ്രഹിക്കുന്നു!",
    "Hindi":     "💬 *{name}* आपसे बात करना चाहते हैं!",
    "Punjabi":   "💬 *{name}* ਤੁਹਾਡੇ ਨਾਲ ਗੱਲ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹਨ!",
    "Gujarati":  "💬 *{name}* તમારી સાથે વાત કરવા ઇચ્છે છે!",
    "Marathi":   "💬 *{name}* तुमच्याशी बोलायचे आहे!",
    "Bengali":   "💬 *{name}* আপনার সাথে কথা বলতে চান!",
    "Odia":      "💬 *{name}* ଆପଣଙ୍କ ସହ ବାତ କରିବାକୁ ଚାହୁଁଛନ୍ତି!",
    "English":   "💬 *{name}* wants to chat with you!",
}

PARTNER_LEFT = {
    "Tamil":     "👋 *{name}* அரட்டையை விட்டு வெளியேறினார்.",
    "Telugu":    "👋 *{name}* చాట్ వదిలి వెళ్ళారు.",
    "Kannada":   "👋 *{name}* ಚಾಟ್ ಬಿಟ್ಟರು.",
    "Malayalam": "👋 *{name}* ചാറ്റ് വിട്ടു.",
    "Hindi":     "👋 *{name}* ने चैट छोड़ दी।",
    "Punjabi":   "👋 *{name}* ਨੇ ਚੈਟ ਛੱਡ ਦਿੱਤੀ।",
    "Gujarati":  "👋 *{name}* ચેટ છોડ્યો.",
    "Marathi":   "👋 *{name}* ने चॅट सोडली.",
    "Bengali":   "👋 *{name}* চ্যাট ছেড়ে দিয়েছেন।",
    "Odia":      "👋 *{name}* ଚ୍ୟାଟ ଛାଡ଼ିଛନ୍ତି।",
    "English":   "👋 *{name}* has left the chat.",
}

SEND_MSG_HINT = {
    "Tamil":     "✉️ செய்திகளை அனுப்பவும். குரல் செய்திகளும் ஏற்றுக்கொள்ளப்படும்.",
    "Telugu":    "✉️ సందేశాలు పంపండి. వాయిస్ మెసేజ్ కూడా పంపవచ్చు.",
    "Kannada":   "✉️ ಸಂದೇಶಗಳನ್ನು ಕಳುಹಿಸಿ. ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಕೂಡ ಸ್ವೀಕಾರ್ಯ.",
    "Malayalam": "✉️ സന്ദേശങ്ങൾ അയക്കൂ. വോയ്സ് മെസേജും ഉപയോഗിക്കാം.",
    "Hindi":     "✉️ संदेश भेजें। वॉइस मैसेज भी स्वीकार हैं।",
    "Punjabi":   "✉️ ਸੁਨੇਹੇ ਭੇਜੋ। ਵੌਇਸ ਮੈਸੇਜ ਵੀ ਮਨਜ਼ੂਰ ਹਨ।",
    "Gujarati":  "✉️ સંદેશ મોકલો. વૉઇસ મેસેજ પણ ચાલે.",
    "Marathi":   "✉️ संदेश पाठवा. व्हॉइस मेसेज पण चालतो.",
    "Bengali":   "✉️ বার্তা পাঠান। ভয়েস মেসেজও গ্রহণযোগ্য।",
    "Odia":      "✉️ ବାର୍ତ୍ତା ପଠାନ୍ତୁ। ଭଏସ ମେସେଜ ମଧ୍ୟ ଗ୍ରହଣୀୟ।",
    "English":   "✉️ Type messages or send voice notes to each other.",
}

NOT_IN_CHAT = {
    "Tamil":     "நீங்கள் தற்போது எந்த அரட்டையிலும் இல்லை.",
    "Telugu":    "మీరు ప్రస్తుతం ఏ చాట్ లోనూ లేరు.",
    "Kannada":   "ನೀವು ಪ್ರಸ್ತುತ ಯಾವ ಚಾಟ್ ನಲ್ಲೂ ಇಲ್ಲ.",
    "Malayalam": "നിങ്ങൾ ഇപ്പോൾ ഒരു ചാറ്റിലും ഇല്ല.",
    "Hindi":     "आप अभी किसी चैट में नहीं हैं।",
    "Punjabi":   "ਤੁਸੀਂ ਇਸ ਵੇਲੇ ਕਿਸੇ ਚੈਟ ਵਿੱਚ ਨਹੀਂ ਹੋ।",
    "Gujarati":  "તમે હાલ કોઈ ચેટ માં નથી.",
    "Marathi":   "तुम्ही सध्या कोणत्याही चॅट मध्ये नाही.",
    "Bengali":   "আপনি এখন কোনো চ্যাটে নেই।",
    "Odia":      "ଆପଣ ବର୍ତ୍ତମାନ କୌଣସି ଚ୍ୟାଟ ରେ ନାହାଁନ୍ତି।",
    "English":   "You are not currently in any chat.",
}

SENT = {
    "Tamil":     "✅ செய்தி அனுப்பப்பட்டது",
    "Telugu":    "✅ సందేశం పంపబడింది",
    "Kannada":   "✅ ಸಂದೇಶ ಕಳುಹಿಸಲಾಗಿದೆ",
    "Malayalam": "✅ സന്ദേശം അയച്ചു",
    "Hindi":     "✅ संदेश भेजा गया",
    "Punjabi":   "✅ ਸੁਨੇਹਾ ਭੇਜਿਆ ਗਿਆ",
    "Gujarati":  "✅ સંદેશ મોકલ્યો",
    "Marathi":   "✅ संदेश पाठवला",
    "Bengali":   "✅ বার্তা পাঠানো হয়েছে",
    "Odia":      "✅ ବାର୍ତ୍ତା ପଠାଯାଇଛି",
    "English":   "✅ Message sent",
}

SENT_OFFLINE = {
    "Tamil":     "📭 செய்தி சேமிக்கப்பட்டது (பங்காளர் இல்லை)",
    "Telugu":    "📭 సందేశం సేవ్ చేయబడింది (పార్ట్నర్ ఆఫ్లైన్)",
    "Kannada":   "📭 ಸಂದೇಶ ಉಳಿಸಲಾಗಿದೆ (ಪಾರ್ಟ್ನರ್ ಆಫ್ಲೈನ್)",
    "Malayalam": "📭 സന്ദേശം സൂക്ഷിച്ചു (പാർട്ണർ ഓഫ്‌ലൈൻ)",
    "Hindi":     "📭 संदेश सहेजा गया (साथी ऑफलाइन)",
    "Punjabi":   "📭 ਸੁਨੇਹਾ ਸੁਰੱਖਿਅਤ (ਸਾਥੀ ਆਫਲਾਈਨ)",
    "Gujarati":  "📭 સંદેશ સાચવ્યો (ભાગીદાર ઑફ્‌લાઇન)",
    "Marathi":   "📭 संदेश जतन (सहकारी ऑफलाइन)",
    "Bengali":   "📭 বার্তা সংরক্ষিত (সঙ্গী অফলাইন)",
    "Odia":      "📭 ବାର୍ତ୍ତା ସଞ୍ଚୟ (ସାଥୀ ଅଫଲାଇନ)",
    "English":   "📭 Message saved (partner offline)",
}

VOICE_SENT = {
    "Tamil":     "✅ குரல் அனுப்பப்பட்டது",
    "Telugu":    "✅ వాయిస్ పంపబడింది",
    "Kannada":   "✅ ವಾಯ್ಸ್ ಕಳುಹಿಸಲಾಗಿದೆ",
    "Malayalam": "✅ വോയ്സ് അയച്ചു",
    "Hindi":     "✅ वॉइस भेजा गया",
    "Punjabi":   "✅ ਵੌਇਸ ਭੇਜਿਆ ਗਿਆ",
    "Gujarati":  "✅ વૉઇસ મોકલ્યો",
    "Marathi":   "✅ व्हॉइस पाठवले",
    "Bengali":   "✅ ভয়েস পাঠানো হয়েছে",
    "Odia":      "✅ ଭଏସ ପଠାଯାଇଛି",
    "English":   "✅ Voice sent",
}

VOICE_SENT_OFFLINE = {
    "Tamil":     "📭 குரல் சேமிக்கப்பட்டது (பங்காளர் இல்லை)",
    "Telugu":    "📭 వాయిస్ సేవ్ చేయబడింది (పార్ట్నర్ ఆఫ్లైన్)",
    "Kannada":   "📭 ವಾಯ್ಸ್ ಉಳಿಸಲಾಗಿದೆ (ಪಾರ್ಟ್ನರ್ ಆಫ್ಲೈನ್)",
    "Malayalam": "📭 വോയ്സ് സൂക്ഷിച്ചു (പാർട്ണർ ഓഫ്‌ലൈൻ)",
    "Hindi":     "📭 वॉइस सहेजा गया (साथी ऑफलाइन)",
    "Punjabi":   "📭 ਵੌਇਸ ਸੁਰੱਖਿਅਤ (ਸਾਥੀ ਆਫਲਾਈਨ)",
    "Gujarati":  "📭 વૉઇસ સાચવ્યો (ભાગીદાર ઑફ્‌લાઇન)",
    "Marathi":   "📭 व्हॉइस जतन (सहकारी ऑफलाइन)",
    "Bengali":   "📭 ভয়েস সংরক্ষিত (সঙ্গী অফলাইন)",
    "Odia":      "📭 ଭଏସ ସଞ୍ଚୟ (ସାଥୀ ଅଫଲାଇନ)",
    "English":   "📭 Voice saved (partner offline)",
}

CHAT_CANCELLED = {
    "Tamil":     "❌ அரட்டை ரத்து செய்யப்பட்டது.",
    "Telugu":    "❌ చాట్ రద్దు చేయబడింది.",
    "Kannada":   "❌ ಚಾಟ್ ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ.",
    "Malayalam": "❌ ചാറ്റ് റദ്ദാക്കി.",
    "Hindi":     "❌ चैट रद्द की गई।",
    "Punjabi":   "❌ ਚੈਟ ਰੱਦ ਕੀਤੀ ਗਈ।",
    "Gujarati":  "❌ ચેટ રદ્દ કરવામાં આવ્યો.",
    "Marathi":   "❌ चॅट रद्द केले.",
    "Bengali":   "❌ চ্যাট বাতিল করা হয়েছে।",
    "Odia":      "❌ ଚ୍ୟାଟ ବାତିଲ ହୋଇଛି।",
    "English":   "❌ Chat cancelled.",
}

LAST_N_MESSAGES = {
    "Tamil":     "கடைசி {n} செய்திகள்:",
    "Telugu":    "చివరి {n} సందేశాలు:",
    "Kannada":   "ಕೊನೆಯ {n} ಸಂದೇಶಗಳು:",
    "Malayalam": "അവസാന {n} സന്ദേശങ്ങൾ:",
    "Hindi":     "अंतिम {n} संदेश:",
    "Punjabi":   "ਆਖਰੀ {n} ਸੁਨੇਹੇ:",
    "Gujarati":  "છેલ્લા {n} સંદેશ:",
    "Marathi":   "शेवटचे {n} संदेश:",
    "Bengali":   "শেষ {n} বার্তা:",
    "Odia":      "ଶେଷ {n} ବାର୍ତ୍ତା:",
    "English":   "Last {n} messages:",
}


# ═══════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def get_msg(msg_dict: dict, lang: str) -> str:
    """Return message in user's language, fallback to English."""
    return msg_dict.get(lang, msg_dict.get("English", ""))


def fmt(msg_dict: dict, language: str, **kwargs) -> str:
    """Get message and format with keyword args. Safe against KeyError."""
    template = get_msg(msg_dict, language)
    try:
        return template.format(**kwargs)
    except KeyError as e:
        import logging
        logging.getLogger(__name__).warning(
            "fmt() missing key %s for lang=%s msg=%s", e, language, list(msg_dict.keys())[:1]
        )
        return template