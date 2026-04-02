"""
messages.py — All UI strings for Agrithm in every supported language.

Rules:
- Never mention KVK or Krishi Vigyan Kendra anywhere.
- Every dict must have an "English" key as the final fallback.
- Use get_msg(dict, lang) everywhere — never index dicts directly.
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


# ═══════════════════════════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════════════════════════

def language_keyboard() -> ReplyKeyboardMarkup:
    """Builds keyboard from LANGUAGES in config — auto-updates when you add languages."""
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
    Returns a fully localised main menu keyboard.
    chat_unread > 0  →  appends unread count to the Chat Room button.
    """
    btn = MENU_BUTTONS.get(lang, MENU_BUTTONS["English"])
    chat_label = btn["chat"]
    if chat_unread:
        chat_label = f"{chat_label} ({chat_unread})"
    rows = [
        [btn["ask"],     btn["mandi"]],
        [btn["connect"], btn["disease"]],
        [btn["news"],    btn["profile"]],
        [chat_label],
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


# ═══════════════════════════════════════════════════════════════════
# MENU BUTTON LABELS  (used for routing AND display)
# ═══════════════════════════════════════════════════════════════════

MENU_BUTTONS = {
    "Tamil":     {"ask": "கேள்வி கேளுங்கள்", "mandi": "மண்டி விலைகள்",    "connect": "விவசாயிகளை இணைக்கவும்", "disease": "நோய் கண்டறிதல்", "news": "தினசரி செய்திகள்",   "profile": "என் சுயவிவரம்",  "chat": "அரட்டை அறை"},
    "Telugu":    {"ask": "ప్రశ్న అడగండి",      "mandi": "మండీ ధరలు",          "connect": "రైతులను కనెక్ట్ చేయి",  "disease": "వ్యాధి తనిఖీ",    "news": "దైనందిన వార్తలు",     "profile": "నా ప్రొఫైల్",     "chat": "చాట్ గది"},
    "Kannada":   {"ask": "ಪ್ರಶ್ನೆ ಕೇಳಿ",         "mandi": "ಮಂಡಿ ಬೆಲೆಗಳು",       "connect": "ರೈತರನ್ನು ಸಂಪರ್ಕಿಸಿ",   "disease": "ರೋಗ ಪರೀಕ್ಷೆ",     "news": "ದಿನದ ಸುದ್ದಿ",         "profile": "ನನ್ನ ಪ್ರೊಫೈಲ್",  "chat": "ಚಾಟ್ ರೂಮ್"},
    "Malayalam": {"ask": "ചോദ്യം ചോദിക്കൂ",     "mandi": "മണ്ടി വിലകൾ",         "connect": "കർഷകരെ ബന്ധിപ്പിക്കൂ", "disease": "രോഗ പരിശോധന",     "news": "ദൈനംദിന വാർത്ത",      "profile": "എന്റെ പ്രൊഫൈൽ",   "chat": "ചാറ്റ് റൂം"},
    "Hindi":     {"ask": "सवाल पूछें",           "mandi": "मंडी भाव",            "connect": "किसानों से जुड़ें",     "disease": "रोग जाँच",         "news": "दैनिक समाचार",        "profile": "मेरी प्रोफाइल",   "chat": "चैट रूम"},
    "Punjabi":   {"ask": "ਸਵਾਲ ਪੁੱਛੋ",           "mandi": "ਮੰਡੀ ਭਾਅ",            "connect": "ਕਿਸਾਨਾਂ ਨਾਲ ਜੁੜੋ",   "disease": "ਰੋਗ ਜਾਂਚ",        "news": "ਰੋਜ਼ਾਨਾ ਖ਼ਬਰਾਂ",      "profile": "ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ",  "chat": "ਚੈਟ ਰੂਮ"},
    "Gujarati":  {"ask": "પ્રશ્ન પૂછો",           "mandi": "મંડી ભાવ",             "connect": "ખેડૂતોને જોડો",        "disease": "રોગ તપાસ",         "news": "દૈનિક સમાચાર",        "profile": "મારી પ્રોફાઇલ",   "chat": "ચેટ રૂમ"},
    "Marathi":   {"ask": "प्रश्न विचारा",         "mandi": "मंडी भाव",             "connect": "शेतकऱ्यांशी जोडा",    "disease": "रोग तपासणी",       "news": "दैनंदिन बातम्या",     "profile": "माझी प्रोफाइल",   "chat": "चॅट रूम"},
    "Bengali":   {"ask": "প্রশ্ন করুন",           "mandi": "মান্ডি দাম",           "connect": "কৃষকদের সাথে যুক্ত হন","disease": "রোগ পরীক্ষা",      "news": "দৈনিক সংবাদ",        "profile": "আমার প্রোফাইল",   "chat": "চ্যাট রুম"},
    "Odia":      {"ask": "ପ୍ରଶ୍ନ କରନ୍ତୁ",          "mandi": "ମଣ୍ଡି ମୂଲ୍ୟ",          "connect": "କୃଷକଙ୍କ ସହ ଯୋଡ଼ନ୍ତୁ",  "disease": "ରୋଗ ପରୀକ୍ଷା",     "news": "ଦୈନିକ ସମ୍ବାଦ",        "profile": "ମୋ ପ୍ରୋଫାଇଲ୍",   "chat": "ଚ୍ୟାଟ୍ ରୁମ୍"},
    "English":   {"ask": "Ask Question",         "mandi": "Mandi Prices",        "connect": "Connect Farmers",       "disease": "Disease Check",    "news": "Daily News",          "profile": "My Profile",       "chat": "Chat Room"},
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


# ═══════════════════════════════════════════════════════════════════
# MESSAGE DICTIONARIES
# ═══════════════════════════════════════════════════════════════════

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
    "Malayalam": "നിങ്ങൾ എന്ത് വിള കൃഷി ചെയ്യുന്നു? (ഉദാ: നെല്ല്, വാഴ, കരിമ്പ്)",
    "Hindi":     "आप कौन सी फसल उगाते हैं? (जैसे: धान, गेहूं, गन्ना)",
    "Punjabi":   "ਤੁਸੀਂ ਕਿਹੜੀ ਫ਼ਸਲ ਉਗਾਉਂਦੇ ਹੋ? (ਜਿਵੇਂ: ਝੋਨਾ, ਕਣਕ, ਗੰਨਾ)",
    "Gujarati":  "તમે કઈ ફસલ ઉગાડો છો? (જેમ કે: ડાંગર, કેળ, શેરડી)",
    "Marathi":   "तुम्ही कोणते पीक घेता? (उदा: भात, केळी, ऊस)",
    "Bengali":   "আপনি কোন ফসল চাষ করেন? (যেমন: ধান, কলা, আখ)",
    "Odia":      "ଆପଣ କେଉଁ ଫସଲ ଚାଷ କରନ୍ତି? (ଯଥା: ଧାନ, କଦଳୀ, ଆଖୁ)",
    "English":   "What crop do you mainly grow? (e.g. paddy, banana, sugarcane)",
}

ASK_VILLAGE = {
    "Tamil":     "உங்கள் கிராமத்தின் பெயர் என்ன?",
    "Telugu":    "మీ గ్రామం పేరు ఏమిటి?",
    "Kannada":   "ನಿಮ್ಮ ಗ್ರಾಮದ ಹೆಸರು ಏನು?",
    "Malayalam": "നിങ്ങളുടെ ഗ്രാമത്തിന്റെ പേര് എന്താണ്?",
    "Hindi":     "आपके गाँव का नाम क्या है?",
    "Punjabi":   "ਤੁਹਾਡੇ ਪਿੰਡ ਦਾ ਨਾਮ ਕੀ ਹੈ?",
    "Gujarati":  "તમારા ગામનું નામ શું છે?",
    "Marathi":   "तुमच्या गावाचे नाव काय आहे?",
    "Bengali":   "আপনার গ্রামের নাম কী?",
    "Odia":      "ଆପଣଙ୍କ ଗ୍ରାମର ନାମ କ'ଣ?",
    "English":   "What is your village name?",
}

ASK_VILLAGE_GPS = {
    "Tamil":     "உங்கள் கிராமத்தின் பெயர் என்ன?\n(GPS: {village} — சரிபார்க்கவும் அல்லது திருத்தவும்)",
    "Telugu":    "మీ గ్రామం పేరు ఏమిటి?\n(GPS: {village} — నిర్ధారించండి లేదా సరిచేయండి)",
    "Kannada":   "ನಿಮ್ಮ ಗ್ರಾಮದ ಹೆಸರು?\n(GPS: {village} — ದೃಢೀಕರಿಸಿ ಅಥವಾ ಸರಿಪಡಿಸಿ)",
    "Malayalam": "നിങ്ങളുടെ ഗ്രാമത്തിന്റെ പേര്?\n(GPS: {village} — സ്ഥിരീകരിക്കൂ അല്ലെങ്കിൽ തിരുത്തൂ)",
    "Hindi":     "आपके गाँव का नाम?\n(GPS: {village} — पुष्टि करें या सुधारें)",
    "Punjabi":   "ਤੁਹਾਡੇ ਪਿੰਡ ਦਾ ਨਾਮ?\n(GPS: {village} — ਪੁਸ਼ਟੀ ਕਰੋ ਜਾਂ ਸੁਧਾਰੋ)",
    "Gujarati":  "તમારા ગામનું નામ?\n(GPS: {village} — પુષ્ટિ કરો અથવા સુધારો)",
    "Marathi":   "तुमच्या गावाचे नाव?\n(GPS: {village} — पुष्टी करा किंवा दुरुस्त करा)",
    "Bengali":   "আপনার গ্রামের নাম?\n(GPS: {village} — নিশ্চিত করুন বা সংশোধন করুন)",
    "Odia":      "ଆପଣଙ୍କ ଗ୍ରାମ ନାମ?\n(GPS: {village} — ନିଶ୍ଚିତ କରନ୍ତୁ ବା ସଂଶୋଧନ କରନ୍ତୁ)",
    "English":   "What is your village name?\n(GPS suggests: {village} — confirm or correct)",
}

PROFILE_SAVED = {
    "Tamil":     "சுயவிவரம் சேமிக்கப்பட்டது!\n\nபெயர்: {name}\nபயிர்: {crop}\nகிராமம்: {village}\nமாவட்டம்: {district}\n\nஇப்போது விவசாய கேள்விகள் கேளுங்கள்!",
    "Telugu":    "ప్రొఫైల్ సేవ్ అయింది!\n\nపేరు: {name}\nపంట: {crop}\nగ్రామం: {village}\nజిల్లా: {district}\n\nఇప్పుడు వ్యవసాయ ప్రశ్నలు అడగండి!",
    "Kannada":   "ಪ್ರೊಫೈಲ್ ಉಳಿಸಲಾಗಿದೆ!\n\nಹೆಸರು: {name}\nಬೆಳೆ: {crop}\nಗ್ರಾಮ: {village}\nಜಿಲ್ಲೆ: {district}\n\nಈಗ ಕೃಷಿ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ!",
    "Malayalam": "പ്രൊഫൈൽ സേവ് ചെയ്തു!\n\nപേര്: {name}\nവിള: {crop}\nഗ്രാമം: {village}\nജില്ല: {district}\n\nഇനി കൃഷി ചോദ്യങ്ങൾ ചോദിക്കൂ!",
    "Hindi":     "प्रोफाइल सेव हो गई!\n\nनाम: {name}\nफसल: {crop}\nगाँव: {village}\nजिला: {district}\n\nअब खेती के सवाल पूछें!",
    "Punjabi":   "ਪ੍ਰੋਫਾਈਲ ਸੇਵ ਹੋ ਗਈ!\n\nਨਾਮ: {name}\nਫ਼ਸਲ: {crop}\nਪਿੰਡ: {village}\nਜ਼ਿਲ੍ਹਾ: {district}\n\nਹੁਣ ਖੇਤੀ ਸਵਾਲ ਪੁੱਛੋ!",
    "Gujarati":  "પ્રોફાઇલ સેવ થઈ!\n\nનામ: {name}\nફસલ: {crop}\nગામ: {village}\nજિલ્લો: {district}\n\nહવે ખેતી પ્રશ્નો પૂછો!",
    "Marathi":   "प्रोफाइल सेव झाली!\n\nनाव: {name}\nपीक: {crop}\nगाव: {village}\nजिल्हा: {district}\n\nआता शेती प्रश्न विचारा!",
    "Bengali":   "প্রোফাইল সেভ হয়েছে!\n\nনাম: {name}\nফসল: {crop}\nগ্রাম: {village}\nজেলা: {district}\n\nএখন কৃষি প্রশ্ন করুন!",
    "Odia":      "ପ୍ରୋଫାଇଲ୍ ସଂରକ୍ଷିତ!\n\nନାମ: {name}\nଫସଲ: {crop}\nଗ୍ରାମ: {village}\nଜିଲ୍ଲା: {district}\n\nଏବେ କୃଷି ପ୍ରଶ୍ନ କରନ୍ତୁ!",
    "English":   "Profile saved!\n\nName: {name}\nCrop: {crop}\nVillage: {village}\nDistrict: {district}\n\nYou can now ask me any farming question!",
}

WELCOME_COMPLETE = {
    "Tamil":     "வரவேற்கிறோம் {name}! விவசாயம் வளமாகட்டும்!",
    "Telugu":    "స్వాగతం {name}! వ్యవసాయం అభివృద్ధి చెందాలి!",
    "Kannada":   "ಸ್ವಾಗತ {name}! ಕೃಷಿ ಯಶಸ್ಸಿನಿಂದ ಬೆಳೆಯಲಿ!",
    "Malayalam": "സ്വാഗതം {name}! കൃഷി സഫലമാകട്ടെ!",
    "Hindi":     "स्वागत है {name}! खेती फले-फूले!",
    "Punjabi":   "ਜੀ ਆਇਆਂ {name}! ਖੇਤੀ ਵਧਦੀ ਫੁੱਲਦੀ ਰਹੇ!",
    "Gujarati":  "સ્વાગત છે {name}! ખેતી ફૂલેફાલે!",
    "Marathi":   "स्वागत {name}! शेती भरभराटीस येवो!",
    "Bengali":   "স্বাগতম {name}! কৃষি সমৃদ্ধ হোক!",
    "Odia":      "ସ୍ୱାଗତ {name}! କୃଷି ସମୃଦ୍ଧ ହୋଉ!",
    "English":   "Welcome {name}! Happy farming!",
}

THINKING = {
    "Tamil":     "சரிபார்க்கிறேன்...",
    "Telugu":    "తనిఖీ చేస్తున్నాను...",
    "Kannada":   "ಪರಿಶೀಲಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "പരിശോധിക്കുന്നു...",
    "Hindi":     "जाँच रहा हूँ...",
    "Punjabi":   "ਜਾਂਚ ਕਰ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "તપાસ કરું છું...",
    "Marathi":   "तपासत आहे...",
    "Bengali":   "যাচাই করছি...",
    "Odia":      "ଯାଞ୍ଚ କରୁଛି...",
    "English":   "Checking...",
}

ASK_QUESTION_PROMPT = {
    "Tamil":     "உங்கள் விவசாய கேள்வியை தட்டச்சு செய்யவும் அல்லது குரல் செய்தியாக அனுப்பவும்.\n/cancel என்று அனுப்பி மெனுவிற்கு திரும்பவும்.",
    "Telugu":    "మీ వ్యవసాయ ప్రశ్నను టైప్ చేయండి లేదా వాయిస్ మెసేజ్ పంపండి.\nమెనుకి తిరిగి వెళ్ళడానికి /cancel పంపండి.",
    "Kannada":   "ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಕಳುಹಿಸಿ.\nಮೆನುಗೆ ಹಿಂತಿರುಗಲು /cancel ಕಳುಹಿಸಿ.",
    "Malayalam": "നിങ്ങളുടെ കൃഷി ചോദ്യം ടൈപ്പ് ചെയ്യൂ അല്ലെങ്കിൽ വോയ്സ് മെസേജ് അയക്കൂ.\nമെനുവിലേക്ക് മടങ്ങാൻ /cancel അയക്കൂ.",
    "Hindi":     "अपना खेती सवाल टाइप करें या वॉइस मैसेज भेजें।\nमेनू पर वापस जाने के लिए /cancel भेजें।",
    "Punjabi":   "ਆਪਣਾ ਖੇਤੀ ਸਵਾਲ ਟਾਈਪ ਕਰੋ ਜਾਂ ਵੌਇਸ ਮੈਸੇਜ ਭੇਜੋ।\nਮੀਨੂ 'ਤੇ ਵਾਪਸ ਜਾਣ ਲਈ /cancel ਭੇਜੋ।",
    "Gujarati":  "તમારો ખેતી પ્રશ્ન ટાઇપ કરો અથવા વૉઇસ મેસેજ મોકલો.\nમેનૂ પર પાછા જવા /cancel મોકલો.",
    "Marathi":   "तुमचा शेती प्रश्न टाइप करा किंवा व्हॉइस मेसेज पाठवा.\nमेनूवर परत जाण्यासाठी /cancel पाठवा.",
    "Bengali":   "আপনার কৃষি প্রশ্ন টাইপ করুন বা ভয়েস মেসেজ পাঠান।\nমেনুতে ফিরতে /cancel পাঠান।",
    "Odia":      "ଆପଣଙ୍କ କୃଷି ପ୍ରଶ୍ନ ଟାଇପ୍ କରନ୍ତୁ ବା ଭଏସ୍ ମେସେଜ୍ ପଠାନ୍ତୁ।\nମେନୁକୁ ଫେରିବା ପାଇଁ /cancel ପଠାନ୍ତୁ।",
    "English":   "Type or send a voice question!\nSend /cancel to return to menu.",
}

VOICE_DOWNLOAD_ERROR = {
    "Tamil":     "ஒலி பதிவிறக்கம் தோல்வியடைந்தது. மீண்டும் முயற்சிக்கவும்.",
    "Telugu":    "ఆడియో డౌన్లోడ్ విఫలమైంది. మళ్ళీ ప్రయత్నించండి.",
    "Kannada":   "ಧ್ವನಿ ಡೌನ್ಲೋಡ್ ವಿಫಲವಾಗಿದೆ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "Malayalam": "ഓഡിയോ ഡൗൺലോഡ് പരാജയപ്പെട്ടു. വീണ്ടും ശ്രമിക്കൂ.",
    "Hindi":     "ऑडियो डाउनलोड विफल। कृपया फिर से प्रयास करें।",
    "Punjabi":   "ਆਡੀਓ ਡਾਊਨਲੋਡ ਅਸਫਲ। ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
    "Gujarati":  "ઑડિઓ ડાઉનલોડ નિષ્ફળ. ફરી પ્રયાસ કરો.",
    "Marathi":   "ऑडिओ डाउनलोड अयशस्वी. पुन्हा प्रयत्न करा.",
    "Bengali":   "অডিও ডাউনলোড ব্যর্থ। আবার চেষ্টা করুন।",
    "Odia":      "ଅଡିଓ ଡାଉନଲୋଡ ବିଫଳ। ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।",
    "English":   "Could not download audio. Please try again.",
}

VOICE_UNCLEAR = {
    "Tamil":     "தெளிவாக கேட்கவில்லை. மீண்டும் முயற்சிக்கவும்.",
    "Telugu":    "స్పష్టంగా వినిపించలేదు. మళ్ళీ ప్రయత్నించండి.",
    "Kannada":   "ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "Malayalam": "വ്യക്തമായി കേൾക്കാൻ കഴിഞ്ഞില്ല. വീണ്ടും ശ്രമിക്കൂ.",
    "Hindi":     "स्पष्ट रूप से सुनाई नहीं दिया। कृपया फिर से प्रयास करें।",
    "Punjabi":   "ਸਾਫ਼ ਸੁਣਾਈ ਨਹੀਂ ਦਿੱਤਾ। ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
    "Gujarati":  "સ્પષ્ટ સંભળાયું નહીં. ફરી પ્રયાસ કરો.",
    "Marathi":   "स्पष्ट ऐकू आले नाही. पुन्हा प्रयत्न करा.",
    "Bengali":   "স্পষ্টভাবে শোনা যায়নি। আবার চেষ্টা করুন।",
    "Odia":      "ସ୍ପଷ୍ଟ ଶୁଣି ହେଲାନି। ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।",
    "English":   "Could not hear clearly. Please try again.",
}

ASK_MANDI_CROP = {
    "Tamil":     "எந்த பயிருக்கான மண்டி விலை வேண்டும்?",
    "Telugu":    "ఏ పంటకు మండీ ధర కావాలి?",
    "Kannada":   "ಯಾವ ಬೆಳೆಯ ಮಂಡಿ ಬೆಲೆ ಬೇಕು?",
    "Malayalam": "ഏത് വിളയുടെ മണ്ടി വില വേണം?",
    "Hindi":     "किस फसल की मंडी कीमत चाहिए?",
    "Punjabi":   "ਕਿਹੜੀ ਫ਼ਸਲ ਦਾ ਮੰਡੀ ਭਾਅ ਚਾਹੀਦਾ ਹੈ?",
    "Gujarati":  "કઈ ફસલ માટે મંડી ભાવ જોઈએ છે?",
    "Marathi":   "कोणत्या पिकाचा मंडी भाव हवा आहे?",
    "Bengali":   "কোন ফসলের মান্ডি দাম দরকার?",
    "Odia":      "କେଉଁ ଫସଲ ପାଇଁ ମଣ୍ଡି ମୂଲ୍ୟ ଦରକାର?",
    "English":   "Which crop do you want mandi prices for?",
}

ASK_MANDI_CROP_NAME = {
    "Tamil":     "பயிர் பெயரை தட்டச்சு செய்யவும்.",
    "Telugu":    "పంట పేరు టైప్ చేయండి.",
    "Kannada":   "ಬೆಳೆ ಹೆಸರು ಟೈಪ್ ಮಾಡಿ.",
    "Malayalam": "വിളയുടെ പേര് ടൈപ്പ് ചെയ്യൂ.",
    "Hindi":     "फसल का नाम टाइप करें।",
    "Punjabi":   "ਫ਼ਸਲ ਦਾ ਨਾਮ ਟਾਈਪ ਕਰੋ।",
    "Gujarati":  "ફસલ નું નામ ટાઇપ કરો.",
    "Marathi":   "पिकाचे नाव टाइप करा.",
    "Bengali":   "ফসলের নাম টাইপ করুন।",
    "Odia":      "ଫସଲ ନାମ ଟାଇପ୍ କରନ୍ତୁ।",
    "English":   "Please type the crop name.",
}

FETCHING_MANDI = {
    "Tamil":     "{crop} மண்டி விலைகளை பெறுகிறேன்...",
    "Telugu":    "{crop} మండీ ధరలు తెస్తున్నాను...",
    "Kannada":   "{crop} ಮಂಡಿ ಬೆಲೆಗಳನ್ನು ತರುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "{crop} മണ്ടി വിലകൾ എടുക്കുന്നു...",
    "Hindi":     "{crop} के मंडी भाव ला रहा हूँ...",
    "Punjabi":   "{crop} ਦੇ ਮੰਡੀ ਭਾਅ ਲੈ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "{crop} ના મંડી ભાવ લાવી રહ્યો છું...",
    "Marathi":   "{crop} चे मंडी भाव आणत आहे...",
    "Bengali":   "{crop} এর মান্ডি দাম আনছি...",
    "Odia":      "{crop} ମଣ୍ଡି ମୂଲ୍ୟ ଆଣୁଛି...",
    "English":   "Fetching mandi prices for {crop}...",
}

DISEASE_PROMPT = {
    "Tamil":     "நோய்வாய்ப்பட்ட பயிரின் புகைப்படம் அனுப்பவும் அல்லது அறிகுறிகளை விவரிக்கவும்.",
    "Telugu":    "వ్యాధి సోకిన పంట ఫోటో పంపండి లేదా లక్షణాలు వివరించండి.",
    "Kannada":   "ರೋಗ ಬಿದ್ದ ಬೆಳೆಯ ಫೋಟೋ ಕಳುಹಿಸಿ ಅಥವಾ ಲಕ್ಷಣಗಳನ್ನು ವಿವರಿಸಿ.",
    "Malayalam": "രോഗം ബാധിച്ച വിളയുടെ ഫോട്ടോ അയക്കൂ അല്ലെങ്കിൽ ലക്ഷണങ്ങൾ വിവരിക്കൂ.",
    "Hindi":     "रोग ग्रस्त फसल की फोटो भेजें या लक्षणों का वर्णन करें।",
    "Punjabi":   "ਰੋਗੀ ਫ਼ਸਲ ਦੀ ਫ਼ੋਟੋ ਭੇਜੋ ਜਾਂ ਲੱਛਣਾਂ ਦਾ ਵਰਣਨ ਕਰੋ।",
    "Gujarati":  "રોગ ગ્રસ્ત પાકનો ફોટો મોકલો અથવા લક્ષણો જણાવો.",
    "Marathi":   "रोगग्रस्त पिकाचा फोटो पाठवा किंवा लक्षणे सांगा.",
    "Bengali":   "রোগাক্রান্ত ফসলের ছবি পাঠান বা লক্ষণ বর্ণনা করুন।",
    "Odia":      "ରୋଗ ଫସଲ ଛବି ପଠାନ୍ତୁ ବା ଲକ୍ଷଣ ବର୍ଣ୍ଣନା କରନ୍ତୁ।",
    "English":   "Send a photo of the diseased crop, or describe symptoms by voice or text.",
}

ANALYSING_IMAGE = {
    "Tamil":     "படத்தை பகுப்பாய்வு செய்கிறேன்...",
    "Telugu":    "చిత్రాన్ని విశ్లేషిస్తున్నాను...",
    "Kannada":   "ಚಿತ್ರ ವಿಶ್ಲೇಷಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "ചിത്രം വിശകലനം ചെയ്യുന്നു...",
    "Hindi":     "फोटो का विश्लेषण कर रहा हूँ...",
    "Punjabi":   "ਫ਼ੋਟੋ ਦਾ ਵਿਸ਼ਲੇਸ਼ਣ ਕਰ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "ફોટો વિશ્લેષણ કરું છું...",
    "Marathi":   "फोटो विश्लेषण करत आहे...",
    "Bengali":   "ছবি বিশ্লেষণ করছি...",
    "Odia":      "ଛବି ବିଶ୍ଲେଷଣ କରୁଛି...",
    "English":   "Analysing your crop image...",
}

CHECKING_SYMPTOMS = {
    "Tamil":     "அறிகுறிகளை சரிபார்க்கிறேன்...",
    "Telugu":    "లక్షణాలు తనిఖీ చేస్తున్నాను...",
    "Kannada":   "ಲಕ್ಷಣಗಳನ್ನು ಪರಿಶೀಲಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "ലക്ഷണങ്ങൾ പരിശോധിക്കുന്നു...",
    "Hindi":     "लक्षण जाँच रहा हूँ...",
    "Punjabi":   "ਲੱਛਣ ਜਾਂਚ ਕਰ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "લક્ષણો તપાસ કરું છું...",
    "Marathi":   "लक्षणे तपासत आहे...",
    "Bengali":   "লক্ষণ যাচাই করছি...",
    "Odia":      "ଲକ୍ଷଣ ଯାଞ୍ଚ କରୁଛି...",
    "English":   "Checking symptoms...",
}

DISEASE_VOICE_UNCLEAR = {
    "Tamil":     "தெளிவாக கேட்கவில்லை. மீண்டும் முயற்சிக்கவும் அல்லது புகைப்படம் அனுப்பவும்.",
    "Telugu":    "స్పష్టంగా వినిపించలేదు. మళ్ళీ ప్రయత్నించండి లేదా ఫోటో పంపండి.",
    "Kannada":   "ಸ್ಪಷ್ಟವಾಗಿ ಕೇಳಿಸಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ ಅಥವಾ ಫೋಟೋ ಕಳುಹಿಸಿ.",
    "Malayalam": "വ്യക്തമായി കേൾക്കാൻ കഴിഞ്ഞില്ല. വീണ്ടും ശ്രമിക്കൂ അല്ലെങ്കിൽ ഫോട്ടോ അയക്കൂ.",
    "Hindi":     "स्पष्ट नहीं सुना। फिर से बोलें या फोटो भेजें।",
    "Punjabi":   "ਸਾਫ਼ ਨਹੀਂ ਸੁਣਿਆ। ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ ਜਾਂ ਫ਼ੋਟੋ ਭੇਜੋ।",
    "Gujarati":  "સ્પષ્ટ ના સંભળ્યું. ફરી પ્રયાસ કરો અથવા ફોટો મોકલો.",
    "Marathi":   "स्पष्ट ऐकू नाही. पुन्हा प्रयत्न करा किंवा फोटो पाठवा.",
    "Bengali":   "স্পষ্ট শোনা যায়নি। আবার চেষ্টা করুন বা ছবি পাঠান।",
    "Odia":      "ସ୍ପଷ୍ଟ ଶୁଣି ହେଲାନି। ପୁଣି ଚେଷ୍ଟା ବା ଛବି ପଠାନ୍ତୁ।",
    "English":   "Could not hear clearly. Try again or send a photo.",
}

DISEASE_TEXT_PROMPT = {
    "Tamil":     "அறிகுறிகளை விவரிக்கவும் அல்லது புகைப்படம் அனுப்பவும்.",
    "Telugu":    "లక్షణాలు వివరించండి లేదా ఫోటో పంపండి.",
    "Kannada":   "ಲಕ್ಷಣಗಳನ್ನು ವಿವರಿಸಿ ಅಥವಾ ಫೋಟೋ ಕಳುಹಿಸಿ.",
    "Malayalam": "ലക്ഷണങ്ങൾ വിവരിക്കൂ അല്ലെങ്കിൽ ഫോട്ടോ അയക്കൂ.",
    "Hindi":     "लक्षणों का वर्णन करें या फोटो भेजें।",
    "Punjabi":   "ਲੱਛਣਾਂ ਦਾ ਵਰਣਨ ਕਰੋ ਜਾਂ ਫ਼ੋਟੋ ਭੇਜੋ।",
    "Gujarati":  "લક્ષણો જણાવો અથવા ફોટો મોકલો.",
    "Marathi":   "लक्षणे सांगा किंवा फोटो पाठवा.",
    "Bengali":   "লক্ষণ বর্ণনা করুন বা ছবি পাঠান।",
    "Odia":      "ଲକ୍ଷଣ ବର୍ଣ୍ଣନା ଦିଅନ୍ତୁ ବା ଛବି ପଠାନ୍ତୁ।",
    "English":   "Please describe the symptoms or send a photo.",
}

IMAGE_ANALYSE_FAIL = {
    "Tamil":     "படத்தை பகுப்பாய்வு செய்ய முடியவில்லை. அறிகுறிகளை விவரிக்கவும்.",
    "Telugu":    "చిత్రాన్ని విశ్లేషించడం సాధ్యపడలేదు. లక్షణాలు వివరించండి.",
    "Kannada":   "ಚಿತ್ರ ವಿಶ್ಲೇಷಣೆ ವಿಫಲ. ಲಕ್ಷಣಗಳನ್ನು ವಿವರಿಸಿ.",
    "Malayalam": "ചിത്രം വിശകലനം ചെയ്യാൻ കഴിഞ്ഞില്ല. ലക്ഷണങ്ങൾ വിവരിക്കൂ.",
    "Hindi":     "फोटो का विश्लेषण नहीं हो सका। लक्षण बताएं।",
    "Punjabi":   "ਫ਼ੋਟੋ ਵਿਸ਼ਲੇਸ਼ਣ ਨਹੀਂ ਹੋ ਸਕਿਆ। ਲੱਛਣ ਦੱਸੋ।",
    "Gujarati":  "ફોટો વિશ્લેષણ થઈ શક્યું નહિ. લક્ષણો જણાવો.",
    "Marathi":   "फोटो विश्लेषण झाले नाही. लक्षणे सांगा.",
    "Bengali":   "ছবি বিশ্লেষণ হয়নি। লক্ষণ বলুন।",
    "Odia":      "ଛବି ବିଶ୍ଲେଷଣ ବିଫଳ। ଲକ୍ଷଣ ବର୍ଣ୍ଣନା ଦିଅନ୍ତୁ।",
    "English":   "Could not analyse the image. Please describe symptoms instead.",
}

SET_NEWS_TIME = {
    "Tamil":     "தினசரி செய்திகளுக்கான நேரத்தை அமைக்கவும்:",
    "Telugu":    "రోజువారీ వార్తల సమయం సెట్ చేయండి:",
    "Kannada":   "ದಿನದ ಸುದ್ದಿಯ ಸಮಯ ಹೊಂದಿಸಿ:",
    "Malayalam": "ദൈനംദിന വാർത്തയ്ക്കുള്ള സമയം സജ്ജമാക്കൂ:",
    "Hindi":     "दैनिक समाचार का समय सेट करें:",
    "Punjabi":   "ਰੋਜ਼ਾਨਾ ਖ਼ਬਰਾਂ ਦਾ ਸਮਾਂ ਸੈੱਟ ਕਰੋ:",
    "Gujarati":  "દૈનિક સમાચારનો સમય સેટ કરો:",
    "Marathi":   "दैनंदिन बातम्यांची वेळ सेट करा:",
    "Bengali":   "দৈনিক সংবাদের সময় সেট করুন:",
    "Odia":      "ଦୈନିକ ସମ୍ବାଦ ସମୟ ସେଟ୍ କରନ୍ତୁ:",
    "English":   "Set your daily news time:",
}

NEWS_TIME_SET = {
    "Tamil":     "செய்தி நேரம் {time} ஆக அமைக்கப்பட்டது\nநேர மண்டலம்: {tz}",
    "Telugu":    "వార్తల సమయం {time} కు సెట్ అయింది\nటైమ్‌జోన్: {tz}",
    "Kannada":   "ಸುದ್ದಿ ಸಮಯ {time} ಗೆ ಹೊಂದಿಸಲಾಗಿದೆ\nಟೈಮ್‌ಜೋನ್: {tz}",
    "Malayalam": "വാർത്ത സമയം {time} ആക്കി സജ്ജമാക്കി\nടൈംസോൺ: {tz}",
    "Hindi":     "समाचार समय {time} पर सेट किया गया\nटाइमज़ोन: {tz}",
    "Punjabi":   "ਖ਼ਬਰਾਂ ਦਾ ਸਮਾਂ {time} 'ਤੇ ਸੈੱਟ ਹੋਇਆ\nਟਾਈਮਜ਼ੋਨ: {tz}",
    "Gujarati":  "સમાચારનો સમય {time} પર સેટ થઈ ગયો\nટાઇમઝોન: {tz}",
    "Marathi":   "बातम्यांची वेळ {time} वर सेट झाली\nटाइमझोन: {tz}",
    "Bengali":   "সংবাদের সময় {time} সেট হয়েছে\nটাইমজোন: {tz}",
    "Odia":      "ସମ୍ବାଦ ସମୟ {time} ରେ ସେଟ୍ ହୋଇଛି\nଟାଇମ୍‌ଜୋନ୍: {tz}",
    "English":   "Daily news time set to {time}\nTimezone: {tz}",
}

PROFILE_VIEW = {
    "Tamil":     "என் சுயவிவரம்\n\nபெயர்    : {name}\nபயிர்    : {crop}\nகிராமம்  : {village}\nமாவட்டம்: {district}\nசெய்தி  : {time} ({tz})\nமொழி    : {lang}",
    "Telugu":    "నా ప్రొఫైల్\n\nపేరు    : {name}\nపంట    : {crop}\nగ్రామం  : {village}\nజిల్లా  : {district}\nవార్తలు : {time} ({tz})\nభాష    : {lang}",
    "Kannada":   "ನನ್ನ ಪ್ರೊಫೈಲ್\n\nಹೆಸರು   : {name}\nಬೆಳೆ    : {crop}\nಗ್ರಾಮ   : {village}\nಜಿಲ್ಲೆ  : {district}\nಸುದ್ದಿ  : {time} ({tz})\nಭಾಷೆ    : {lang}",
    "Malayalam": "എന്റെ പ്രൊഫൈൽ\n\nപേര്    : {name}\nവിള    : {crop}\nഗ്രാമം  : {village}\nജില്ല  : {district}\nവാർത്ത : {time} ({tz})\nഭാഷ    : {lang}",
    "Hindi":     "मेरी प्रोफाइल\n\nनाम    : {name}\nफसल   : {crop}\nगाँव   : {village}\nजिला   : {district}\nसमाचार: {time} ({tz})\nभाषा   : {lang}",
    "Punjabi":   "ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ\n\nਨਾਮ    : {name}\nਫ਼ਸਲ   : {crop}\nਪਿੰਡ   : {village}\nਜ਼ਿਲ੍ਹਾ : {district}\nਖ਼ਬਰਾਂ : {time} ({tz})\nਭਾਸ਼ਾ  : {lang}",
    "Gujarati":  "મારી પ્રોફાઇલ\n\nનામ    : {name}\nફસલ   : {crop}\nગામ    : {village}\nજિલ્લો : {district}\nસમાચાર: {time} ({tz})\nભાષા   : {lang}",
    "Marathi":   "माझी प्रोफाइल\n\nनाव    : {name}\nपीक    : {crop}\nगाव    : {village}\nजिल्हा : {district}\nबातम्या: {time} ({tz})\nभाषा   : {lang}",
    "Bengali":   "আমার প্রোফাইল\n\nনাম    : {name}\nফসল   : {crop}\nগ্রাম  : {village}\nজেলা   : {district}\nসংবাদ  : {time} ({tz})\nভাষা   : {lang}",
    "Odia":      "ମୋ ପ୍ରୋଫାଇଲ୍\n\nନାମ    : {name}\nଫସଲ   : {crop}\nଗ୍ରାମ  : {village}\nଜିଲ୍ଲା : {district}\nସମ୍ବାଦ : {time} ({tz})\nଭାଷା   : {lang}",
    "English":   "My Profile\n\nName     : {name}\nCrop     : {crop}\nVillage  : {village}\nDistrict : {district}\nNews at  : {time} ({tz})\nLanguage : {lang}",
}

FINDING_FARMERS = {
    "Tamil":     "{crop} விவசாயிகளை தேடுகிறேன்...",
    "Telugu":    "{crop} రైతులను వెతుకుతున్నాను...",
    "Kannada":   "{crop} ರೈತರನ್ನು ಹುಡುಕುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "{crop} കർഷകരെ തിരയുന്നു...",
    "Hindi":     "{crop} किसानों को खोज रहा हूँ...",
    "Punjabi":   "{crop} ਕਿਸਾਨਾਂ ਨੂੰ ਲੱਭ ਰਿਹਾ ਹਾਂ...",
    "Gujarati":  "{crop} ખેડૂતોને શોધ કરું છું...",
    "Marathi":   "{crop} शेतकऱ्यांना शोधत आहे...",
    "Bengali":   "{crop} কৃষকদের খুঁজছি...",
    "Odia":      "{crop} କୃଷକ ଖୋଜୁଛି...",
    "English":   "Finding {crop} farmers near you...",
}

NO_FARMERS_NEARBY = {
    "Tamil":     "இன்னும் {crop} விவசாயிகள் Agrithm-ல் இல்லை. உங்கள் அண்டை வீட்டாரை அழைக்கவும்!",
    "Telugu":    "ఇంకా {crop} రైతులు Agrithm లో లేరు. మీ పొరుగువారిని ఆహ్వానించండి!",
    "Kannada":   "ಇನ್ನೂ {crop} ರೈತರು Agrithm ನಲ್ಲಿ ಇಲ್ಲ. ನಿಮ್ಮ ನೆರೆಹೊರೆಯವರನ್ನು ಆಹ್ವಾನಿಸಿ!",
    "Malayalam": "ഇതുവരെ {crop} കർഷകർ Agrithm-ൽ ഇല്ല. അയൽക്കാരെ ക്ഷണിക്കൂ!",
    "Hindi":     "अभी {crop} किसान Agrithm पर नहीं हैं। अपने पड़ोसियों को आमंत्रित करें!",
    "Punjabi":   "ਅਜੇ {crop} ਕਿਸਾਨ Agrithm 'ਤੇ ਨਹੀਂ ਹਨ। ਆਪਣੇ ਗੁਆਂਢੀਆਂ ਨੂੰ ਸੱਦੋ!",
    "Gujarati":  "હજુ {crop} ખેડૂતો Agrithm પર નથી. તમારા પડોશીઓને આમંત્રિત કરો!",
    "Marathi":   "अजून {crop} शेतकरी Agrithm वर नाहीत. शेजाऱ्यांना आमंत्रित करा!",
    "Bengali":   "এখনও {crop} কৃষকরা Agrithm-এ নেই। প্রতিবেশীদের আমন্ত্রণ জানান!",
    "Odia":      "ଏପର୍ଯ୍ୟନ୍ତ {crop} କୃଷକ Agrithm ରେ ନାହାନ୍ତି। ପ୍ରତିବେଶୀଙ୍କୁ ଆମନ୍ତ୍ରଣ ଦିଅନ୍ତୁ!",
    "English":   "No {crop} farmers found nearby yet. Invite your neighbours!",
}

FARMERS_FOUND_HEADER = {
    "Tamil":     "{crop} விவசாயிகள் ({count} கண்டுபிடிக்கப்பட்டனர்)\n\nஒரு பெயரை தட்டவும் அல்லது அரட்டைக்கு Chat தட்டவும்:",
    "Telugu":    "{crop} రైతులు ({count} కనుగొనబడ్డారు)\n\nపేరు తాకండి లేదా Chat నొక్కండి:",
    "Kannada":   "{crop} ರೈತರು ({count} ಕಂಡುಬಂದಿದ್ದಾರೆ)\n\nಹೆಸರು ಟ್ಯಾಪ್ ಮಾಡಿ ಅಥವಾ Chat ಒತ್ತಿ:",
    "Malayalam": "{crop} കർഷകർ ({count} കണ്ടെത്തി)\n\nഒരു പേര് ടാപ്പ് ചെയ്യൂ അല്ലെങ്കിൽ Chat ടാപ്പ് ചെയ്യൂ:",
    "Hindi":     "{crop} किसान ({count} मिले)\n\nनाम दबाएं या Chat टैप करें:",
    "Punjabi":   "{crop} ਕਿਸਾਨ ({count} ਮਿਲੇ)\n\nਨਾਮ ਦਬਾਓ ਜਾਂ Chat ਟੈਪ ਕਰੋ:",
    "Gujarati":  "{crop} ખેડૂત ({count} મળ્યા)\n\nનામ ટૅપ કરો અથવા Chat ટૅપ કરો:",
    "Marathi":   "{crop} शेतकरी ({count} सापडले)\n\nनाव दाबा किंवा Chat दाबा:",
    "Bengali":   "{crop} কৃষক ({count} পাওয়া গেছে)\n\nনাম ট্যাপ করুন বা Chat ট্যাপ করুন:",
    "Odia":      "{crop} କୃଷକ ({count} ମିଳିଲେ)\n\nନାମ ଟ୍ୟାପ କରନ୍ତୁ ବା Chat ଟ୍ୟାପ କରନ୍ତୁ:",
    "English":   "{crop} Farmers Near You ({count} found)\n\nTap a name to see their profile, or tap Chat to connect:",
}

COMPLETE_PROFILE_FIRST = {
    "Tamil":     "முதலில் உங்கள் சுயவிவரத்தை பூர்த்திசெய்யவும்.",
    "Telugu":    "ముందు మీ ప్రొఫైల్ పూర్తి చేయండి.",
    "Kannada":   "ಮೊದಲು ನಿಮ್ಮ ಪ್ರೊಫೈಲ್ ಪೂರ್ಣಗೊಳಿಸಿ.",
    "Malayalam": "ആദ്യം നിങ്ങളുടെ പ്രൊഫൈൽ പൂർത്തിയാക്കൂ.",
    "Hindi":     "पहले अपनी प्रोफाइल पूरी करें।",
    "Punjabi":   "ਪਹਿਲਾਂ ਆਪਣੀ ਪ੍ਰੋਫਾਈਲ ਪੂਰੀ ਕਰੋ।",
    "Gujarati":  "પ્રથમ તમારી પ્રોફાઇલ પૂર્ण કરો.",
    "Marathi":   "आधी तुमची प्रोफाइल पूर्ण करा.",
    "Bengali":   "প্রথমে আপনার প্রোফাইল সম্পূর্ণ করুন।",
    "Odia":      "ପ୍ରଥମେ ଆପଣଙ୍କ ପ୍ରୋଫାଇଲ୍ ସମ୍ପୂର୍ଣ କରନ୍ତୁ।",
    "English":   "Complete your profile first.",
}

USE_MENU = {
    "Tamil":     "மெனு பொத்தான்களை பயன்படுத்தவும் அல்லது முழு விவசாய கேள்வியை தட்டச்சு செய்யவும்.",
    "Telugu":    "మెనూ బటన్లు ఉపయోగించండి లేదా పూర్తి వ్యవసాయ ప్రశ్న టైప్ చేయండి.",
    "Kannada":   "ಮೆನು ಬಟನ್ ಉಪಯೋಗಿಸಿ ಅಥವಾ ಪೂರ್ಣ ಕೃಷಿ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ.",
    "Malayalam": "മെനു ബട്ടണുകൾ ഉപയോഗിക്കൂ അല്ലെങ്കിൽ കൃഷി ചോദ്യം ടൈപ്പ് ചെയ്യൂ.",
    "Hindi":     "मेनू बटन का उपयोग करें या पूरा खेती सवाल टाइप करें।",
    "Punjabi":   "ਮੀਨੂ ਬਟਨ ਵਰਤੋ ਜਾਂ ਪੂਰਾ ਖੇਤੀ ਸਵਾਲ ਟਾਈਪ ਕਰੋ।",
    "Gujarati":  "મેનૂ બટન વાપરો અથવા પૂર્ણ ખેતી પ્રશ્ન ટાઇપ કરો.",
    "Marathi":   "मेनू बटणे वापरा किंवा पूर्ण शेती प्रश्न टाइप करा.",
    "Bengali":   "মেনু বোতাম ব্যবহার করুন বা কৃষি প্রশ্ন টাইপ করুন।",
    "Odia":      "ମେନୁ ବଟନ୍ ବ୍ୟବହାର କରନ୍ତୁ ବା ପୂର୍ଣ ପ୍ରଶ୍ନ ଟାଇପ୍ କରନ୍ତୁ।",
    "English":   "Please use the menu buttons or type a full farming question.",
}

TYPE_QUESTION = {
    "Tamil":     "உங்கள் விவசாய கேள்வியை தட்டச்சு செய்யவும்.",
    "Telugu":    "మీ వ్యవసాయ ప్రశ్న టైప్ చేయండి.",
    "Kannada":   "ನಿಮ್ಮ ಕೃಷಿ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ.",
    "Malayalam": "നിങ്ങളുടെ കൃഷി ചോദ്യം ടൈപ്പ് ചെയ്യൂ.",
    "Hindi":     "अपना खेती सवाल टाइप करें।",
    "Punjabi":   "ਆਪਣਾ ਖੇਤੀ ਸਵਾਲ ਟਾਈਪ ਕਰੋ।",
    "Gujarati":  "તમારો ખેતી પ્રશ્ન ટાઇપ કરો.",
    "Marathi":   "तुमचा शेती प्रश्न टाइप करा.",
    "Bengali":   "আপনার কৃষি প্রশ্ন টাইপ করুন।",
    "Odia":      "ଆପଣଙ୍କ କୃଷି ପ୍ରଶ୍ନ ଟାଇପ୍ କରନ୍ତୁ।",
    "English":   "Please type your farming question.",
}

CANCELLED = {
    "Tamil":     "ரத்து செய்யப்பட்டது.",
    "Telugu":    "రద్దు చేయబడింది.",
    "Kannada":   "ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ.",
    "Malayalam": "റദ്ദാക്കി.",
    "Hindi":     "रद्द किया गया।",
    "Punjabi":   "ਰੱਦ ਕੀਤਾ ਗਿਆ।",
    "Gujarati":  "રદ્દ કરવામાં આવ્યું.",
    "Marathi":   "रद्द केले.",
    "Bengali":   "বাতিল করা হয়েছে।",
    "Odia":      "ବାତିଲ ହୋଇଛି।",
    "English":   "Cancelled.",
}

ERROR_GENERIC = {
    "Tamil":     "மன்னிக்கவும், ஏதோ தவறு நடந்தது. மீண்டும் முயற்சிக்கவும்.",
    "Telugu":    "క్షమించండి, ఏదో తప్పు జరిగింది. మళ్ళీ ప్రయత్నించండి.",
    "Kannada":   "ಕ್ಷಮಿಸಿ, ಏನೋ ತಪ್ಪಾಯಿತು. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "Malayalam": "ക്ഷമിക്കൂ, എന്തോ തകരാർ. വീണ്ടും ശ്രമിക്കൂ.",
    "Hindi":     "माफ करें, कुछ गड़बड़ हुई। कृपया फिर से प्रयास करें।",
    "Punjabi":   "ਮਾਫ਼ ਕਰਨਾ, ਕੁਝ ਗਲਤ ਹੋ ਗਿਆ। ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
    "Gujarati":  "માફ કરો, કંઈ ખોટું થઈ ગયું. ફરી પ્રયાસ કરો.",
    "Marathi":   "माफ करा, काहीतरी चुकले. पुन्हा प्रयत्न करा.",
    "Bengali":   "দুঃখিত, কিছু ভুল হয়েছে। আবার চেষ্টা করুন।",
    "Odia":      "କ୍ଷମା କରନ୍ତୁ, କିଛି ଭୁଲ ହୋଇଛି। ପୁଣି ଚେଷ୍ଟା କରନ୍ତୁ।",
    "English":   "Sorry, something went wrong. Please try again.",
}

# FALLBACK — no KVK reference anywhere
FALLBACK = {
    "Tamil":     "இந்த தகவல் என்னிடம் இல்லை. வேறு கேள்வி கேளுங்கள்.",
    "Telugu":    "ఈ సమాచారం నా దగ్గర లేదు. మరో ప్రశ్న అడగండి.",
    "Kannada":   "ಈ ಮಾಹಿತಿ ನನ್ನ ಬಳಿ ಇಲ್ಲ. ಮತ್ತೊಂದು ಪ್ರಶ್ನೆ ಕೇಳಿ.",
    "Malayalam": "ഈ വിവരം എന്റെ കൈവശമില്ല. മറ്റൊരു ചോദ്യം ചോദിക്കൂ.",
    "Hindi":     "यह जानकारी मेरे पास नहीं है। कोई और सवाल पूछें।",
    "Punjabi":   "ਇਹ ਜਾਣਕਾਰੀ ਮੇਰੇ ਕੋਲ ਨਹੀਂ ਹੈ। ਕੋਈ ਹੋਰ ਸਵਾਲ ਪੁੱਛੋ।",
    "Gujarati":  "આ માહિતી મારી પાસે નથી. બીજો પ્રશ્ન પૂછો.",
    "Marathi":   "ही माहिती माझ्याकडे नाही. दुसरा प्रश्न विचारा.",
    "Bengali":   "এই তথ্য আমার কাছে নেই। অন্য প্রশ্ন করুন।",
    "Odia":      "ଏହି ତଥ୍ୟ ମୋ ପାଖରେ ନାହିଁ। ଅନ୍ୟ ପ୍ରଶ୍ନ କରନ୍ତୁ।",
    "English":   "I do not have enough information on this topic right now. Please ask another question.",
}

LOCATION_DETECTED = {
    "Tamil":     "இருப்பிடம் கண்டறியப்பட்டது!\nகிராமம்: {village}\nமாவட்டம்: {district}\nநேர மண்டலம்: {tz}\n\nமொழியை தேர்ந்தெடுக்கவும்:",
    "Telugu":    "స్థానం గుర్తించబడింది!\nగ్రామం: {village}\nజిల్లా: {district}\nటైమ్‌జోన్: {tz}\n\nమీ భాష ఎంచుకోండి:",
    "Kannada":   "ಸ್ಥಳ ಪತ್ತೆ!\nಗ್ರಾಮ: {village}\nಜಿಲ್ಲೆ: {district}\nಟೈಮ್‌ಜೋನ್: {tz}\n\nಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ:",
    "Malayalam": "സ്ഥലം കണ്ടെത്തി!\nഗ്രാമം: {village}\nജില്ല: {district}\nടൈംസോൺ: {tz}\n\nഭാഷ തിരഞ്ഞെടുക്കൂ:",
    "Hindi":     "स्थान मिल गया!\nगाँव: {village}\nजिला: {district}\nटाइमज़ोन: {tz}\n\nभाषा चुनें:",
    "Punjabi":   "ਸਥਾਨ ਮਿਲਿਆ!\nਪਿੰਡ: {village}\nਜ਼ਿਲ੍ਹਾ: {district}\nਟਾਈਮਜ਼ੋਨ: {tz}\n\nਭਾਸ਼ਾ ਚੁਣੋ:",
    "Gujarati":  "સ્થાન મળ્યું!\nગામ: {village}\nજિલ્લો: {district}\nટાઇમઝોન: {tz}\n\nભાષા પસંદ કરો:",
    "Marathi":   "स्थान सापडले!\nगाव: {village}\nजिल्हा: {district}\nटाइमझोन: {tz}\n\nभाषा निवडा:",
    "Bengali":   "অবস্থান পাওয়া গেছে!\nগ্রাম: {village}\nজেলা: {district}\nটাইমজোন: {tz}\n\nভাষা বেছে নিন:",
    "Odia":      "ସ୍ଥାନ ମିଳିଲା!\nଗ୍ରାମ: {village}\nଜିଲ୍ଲା: {district}\nଟାଇମ୍‌ଜୋନ୍: {tz}\n\nଭାଷା ବାଛନ୍ତୁ:",
    "English":   "Location detected!\nVillage: {village}\nDistrict: {district}\nTimezone: {tz}\n\nNow choose your language:",
}

CHAT_WITH = {
    "Tamil":     "{partner} உடன் அரட்டை (கடந்த {n} செய்திகள்)\n\n{history}\n\nதட்டச்சு செய்யவும் அல்லது குரல் அனுப்பவும். வெளியேற Leave Chat சொல்லவும்.",
    "Telugu":    "{partner} తో చాట్ (చివరి {n} సందేశాలు)\n\n{history}\n\nటైప్ చేయండి లేదా వాయిస్ పంపండి. వెళ్ళడానికి Leave Chat అనండి.",
    "Kannada":   "{partner} ಜೊತೆ ಚಾಟ್ (ಕೊನೆಯ {n} ಸಂದೇಶಗಳು)\n\n{history}\n\nಟೈಪ್ ಮಾಡಿ ಅಥವಾ ವಾಯ್ಸ್ ಕಳುಹಿಸಿ. ಬಿಡಲು Leave Chat ಹೇಳಿ.",
    "Malayalam": "{partner} മായി ചാറ്റ് (അവസാന {n} സന്ദേശങ്ങൾ)\n\n{history}\n\nടൈപ്പ് ചെയ്യൂ അല്ലെങ്കിൽ വോയ്സ് അയക്കൂ. ഇറങ്ങാൻ Leave Chat പറയൂ.",
    "Hindi":     "{partner} के साथ चैट (अंतिम {n} संदेश)\n\n{history}\n\nटाइप करें या वॉइस भेजें। छोड़ने के लिए Leave Chat कहें।",
    "Punjabi":   "{partner} ਨਾਲ ਚੈਟ (ਪਿਛਲੇ {n} ਸੁਨੇਹੇ)\n\n{history}\n\nਟਾਈਪ ਕਰੋ ਜਾਂ ਵੌਇਸ ਭੇਜੋ। ਛੱਡਣ ਲਈ Leave Chat ਕਹੋ।",
    "Gujarati":  "{partner} સાથે ચેટ (છેલ્લા {n} સંદેશ)\n\n{history}\n\nટાઇપ કરો અથવા વૉઇસ મોકલો. છોડવા Leave Chat કહો.",
    "Marathi":   "{partner} सोबत चॅट (शेवटचे {n} संदेश)\n\n{history}\n\nटाइप करा किंवा व्हॉइस पाठवा. सोडण्यासाठी Leave Chat म्हणा.",
    "Bengali":   "{partner} এর সাথে চ্যাট (শেষ {n} বার্তা)\n\n{history}\n\nটাইপ করুন বা ভয়েস পাঠান। ছাড়তে Leave Chat বলুন।",
    "Odia":      "{partner} ସହ ଚ୍ୟାଟ (ଶେଷ {n} ବାର୍ତ୍ତା)\n\n{history}\n\nଟାଇପ ବା ଭଏସ ପଠାନ୍ତୁ। ଛାଡ଼ିବା ପାଇଁ Leave Chat କୁହନ୍ତୁ।",
    "English":   "Chat with {partner} (last {n} messages)\n\n{history}\n\nType or send voice. Say Leave Chat to exit.",
}

CHOOSE_CHAT_PARTNER = {
    "Tamil":     "{crop} விவசாயிகள்:\nயாருடன் பேச விரும்புகிறீர்கள்?",
    "Telugu":    "{crop} రైతులు:\nఎవరితో చాట్ చేయాలనుకుంటున్నారు?",
    "Kannada":   "{crop} ರೈತರು:\nಯಾರೊಂದಿಗೆ ಚಾಟ್ ಮಾಡಲು ಬಯಸುತ್ತೀರಿ?",
    "Malayalam": "{crop} കർഷകർ:\nആരോടൊപ്പം ചാറ്റ് ചെയ്യണം?",
    "Hindi":     "{crop} किसान:\nकिसके साथ चैट करना चाहते हैं?",
    "Punjabi":   "{crop} ਕਿਸਾਨ:\nਕਿਸ ਨਾਲ ਚੈਟ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹੋ?",
    "Gujarati":  "{crop} ખેડૂત:\nકોની સાથે ચેટ કરવા ઇચ્છો છો?",
    "Marathi":   "{crop} शेतकरी:\nकोणाशी चॅट करायचे आहे?",
    "Bengali":   "{crop} কৃষক:\nকার সাথে চ্যাট করতে চান?",
    "Odia":      "{crop} କୃଷକ:\nକାହା ସହ ଚ୍ୟାଟ କରିବେ?",
    "English":   "{crop} farmers near you:\nChoose someone to chat with:",
}

CONNECTED_TO = {
    "Tamil":     "{partner} உடன் இணைக்கப்பட்டீர்கள்!\n\n{history}\n\nஒரு செய்தி அனுப்பவும்.",
    "Telugu":    "{partner} తో కనెక్ట్ అయ్యారు!\n\n{history}\n\nఒక సందేశం పంపండి.",
    "Kannada":   "{partner} ಜೊತೆ ಸಂಪರ್ಕ!\n\n{history}\n\nಒಂದು ಸಂದೇಶ ಕಳುಹಿಸಿ.",
    "Malayalam": "{partner} മായി ബന്ധിപ്പിച്ചു!\n\n{history}\n\nഒരു സന്ദേശം അയക്കൂ.",
    "Hindi":     "{partner} से जुड़ गए!\n\n{history}\n\nएक संदेश भेजें।",
    "Punjabi":   "{partner} ਨਾਲ ਜੁੜ ਗਏ!\n\n{history}\n\nਇੱਕ ਸੁਨੇਹਾ ਭੇਜੋ।",
    "Gujarati":  "{partner} સાથે કનેક્ટ!\n\n{history}\n\nએક સંદેશ મોકલો.",
    "Marathi":   "{partner} शी कनेक्ट!\n\n{history}\n\nएक संदेश पाठवा.",
    "Bengali":   "{partner} এর সাথে সংযুক্ত!\n\n{history}\n\nএকটি বার্তা পাঠান।",
    "Odia":      "{partner} ସହ ସଂଯୁକ୍ତ!\n\n{history}\n\nଏକ ବାର୍ତ୍ତା ପଠାନ୍ତୁ।",
    "English":   "Connected to {partner}!\n\n{history}\n\nSend a message.",
}

LEFT_CHAT = {
    "Tamil":     "நீங்கள் அரட்டை அறையை விட்டு வெளியேறினீர்கள்.",
    "Telugu":    "మీరు చాట్ రూమ్ వదిలారు.",
    "Kannada":   "ನೀವು ಚಾಟ್ ರೂಮ್ ಬಿಟ್ಟಿದ್ದೀರಿ.",
    "Malayalam": "നിങ്ങൾ ചാറ്റ് റൂം വിട്ടു.",
    "Hindi":     "आपने चैट रूम छोड़ दिया।",
    "Punjabi":   "ਤੁਸੀਂ ਚੈਟ ਰੂਮ ਛੱਡ ਦਿੱਤਾ।",
    "Gujarati":  "તમે ચેટ રૂમ છોડ્યો.",
    "Marathi":   "तुम्ही चॅट रूम सोडले.",
    "Bengali":   "আপনি চ্যাট রুম ছেড়ে গেছেন।",
    "Odia":      "ଆପଣ ଚ୍ୟାଟ ରୁମ ଛାଡ଼ିଲେ।",
    "English":   "You left the chat room.",
}

WANT_TO_CHAT = {
    "Tamil":     "{name} உங்களுடன் பேச விரும்புகிறார்! Chat Room திறக்கவும்.",
    "Telugu":    "{name} మీతో చాట్ చేయాలనుకుంటున్నారు! Chat Room తెరవండి.",
    "Kannada":   "{name} ನಿಮ್ಮೊಂದಿಗೆ ಚಾಟ್ ಮಾಡಲು ಬಯಸುತ್ತಾರೆ! Chat Room ತೆರೆಯಿರಿ.",
    "Malayalam": "{name} നിങ്ങളോടൊപ്പം ചാറ്റ് ചെയ്യാൻ ആഗ്രഹിക്കുന്നു! Chat Room തുറക്കൂ.",
    "Hindi":     "{name} आपसे चैट करना चाहते हैं! Chat Room खोलें।",
    "Punjabi":   "{name} ਤੁਹਾਡੇ ਨਾਲ ਚੈਟ ਕਰਨਾ ਚਾਹੁੰਦੇ ਹਨ! Chat Room ਖੋਲ੍ਹੋ।",
    "Gujarati":  "{name} તમારી સાથે ચેટ કરવા ઇચ્છે છે! Chat Room ખોલો.",
    "Marathi":   "{name} तुमच्याशी चॅट करायचे आहे! Chat Room उघडा.",
    "Bengali":   "{name} আপনার সাথে চ্যাট করতে চান! Chat Room খুলুন।",
    "Odia":      "{name} ଆପଣଙ୍କ ସହ ଚ୍ୟାଟ କରିବାକୁ ଚାହୁଁଛନ୍ତି! Chat Room ଖୋଲନ୍ତୁ।",
    "English":   "{name} wants to chat with you! Tap Chat Room to open.",
}

PARTNER_LEFT = {
    "Tamil":     "{name} அரட்டையை விட்டு வெளியேறினார்.",
    "Telugu":    "{name} చాట్ వదిలారు.",
    "Kannada":   "{name} ಚಾಟ್ ಬಿಟ್ಟರು.",
    "Malayalam": "{name} ചാറ്റ് വിട്ടു.",
    "Hindi":     "{name} ने चैट छोड़ दी।",
    "Punjabi":   "{name} ਨੇ ਚੈਟ ਛੱਡ ਦਿੱਤੀ।",
    "Gujarati":  "{name} ચેટ છોડ્યો.",
    "Marathi":   "{name} ने चॅट सोडले.",
    "Bengali":   "{name} চ্যাট ছেড়ে গেছেন।",
    "Odia":      "{name} ଚ୍ୟାଟ ଛାଡ଼ିଲେ।",
    "English":   "{name} has left the chat.",
}

SEND_MSG_HINT = {
    "Tamil":     "செய்தி அனுப்பவும் | வெளியேற Leave Chat சொல்லவும்",
    "Telugu":    "సందేశం పంపండి | వెళ్ళడానికి Leave Chat అనండి",
    "Kannada":   "ಸಂದೇಶ ಕಳುಹಿಸಿ | ಬಿಡಲು Leave Chat ಹೇಳಿ",
    "Malayalam": "സന്ദേശം അയക്കൂ | ഇറങ്ങാൻ Leave Chat പറയൂ",
    "Hindi":     "संदेश भेजें | छोड़ने के लिए Leave Chat कहें",
    "Punjabi":   "ਸੁਨੇਹਾ ਭੇਜੋ | ਛੱਡਣ ਲਈ Leave Chat ਕਹੋ",
    "Gujarati":  "સંદેશ મોકલો | છોડવા Leave Chat કહો",
    "Marathi":   "संदेश पाठवा | सोडण्यासाठी Leave Chat म्हणा",
    "Bengali":   "বার্তা পাঠান | ছাড়তে Leave Chat বলুন",
    "Odia":      "ବାର୍ତ୍ତା ପଠାନ୍ତୁ | ଛାଡ଼ିବା ପାଇଁ Leave Chat କୁହନ୍ତୁ",
    "English":   "Send a message | Say Leave Chat to exit",
}

NOT_IN_CHAT = {
    "Tamil":     "நீங்கள் எந்த அரட்டையிலும் இல்லை.",
    "Telugu":    "మీరు ఏ చాట్‌లో లేరు.",
    "Kannada":   "ನೀವು ಯಾವ ಚಾಟ್‌ನಲ್ಲೂ ಇಲ್ಲ.",
    "Malayalam": "നിങ്ങൾ ഒരു ചാറ്റിലും ഇല്ല.",
    "Hindi":     "आप किसी चैट में नहीं हैं।",
    "Punjabi":   "ਤੁਸੀਂ ਕਿਸੇ ਵੀ ਚੈਟ ਵਿੱਚ ਨਹੀਂ ਹੋ।",
    "Gujarati":  "તમે કોઈ ચેટમાં નથી.",
    "Marathi":   "तुम्ही कोणत्याही चॅटमध्ये नाही.",
    "Bengali":   "আপনি কোনো চ্যাটে নেই।",
    "Odia":      "ଆପଣ କୌଣସି ଚ୍ୟାଟରେ ନାହାନ୍ତି।",
    "English":   "You are not in a chat.",
}

SENT = {
    "Tamil":     "அனுப்பப்பட்டது",
    "Telugu":    "పంపబడింది",
    "Kannada":   "ಕಳುಹಿಸಲಾಗಿದೆ",
    "Malayalam": "അയച്ചു",
    "Hindi":     "भेजा गया",
    "Punjabi":   "ਭੇਜਿਆ ਗਿਆ",
    "Gujarati":  "મોકલ્યો",
    "Marathi":   "पाठवले",
    "Bengali":   "পাঠানো হয়েছে",
    "Odia":      "ପଠାଯାଇଛି",
    "English":   "Sent",
}

SENT_OFFLINE = {
    "Tamil":     "அனுப்பப்பட்டது (ஆஃப்லைன்)",
    "Telugu":    "పంపబడింది (ఆఫ్‌లైన్)",
    "Kannada":   "ಕಳುಹಿಸಲಾಗಿದೆ (ಆಫ್‌ಲೈನ್)",
    "Malayalam": "അയച്ചു (ഓഫ്‌ലൈൻ)",
    "Hindi":     "भेजा गया (ऑफलाइन)",
    "Punjabi":   "ਭੇਜਿਆ ਗਿਆ (ਆਫਲਾਈਨ)",
    "Gujarati":  "મોકલ્યો (ઑફ્‌લાઇન)",
    "Marathi":   "पाठवले (ऑफलाइन)",
    "Bengali":   "পাঠানো হয়েছে (অফলাইন)",
    "Odia":      "ପଠାଯାଇଛି (ଅଫଲାଇନ)",
    "English":   "Sent (offline)",
}

LAST_N_MESSAGES = {
    "Tamil":     "கடந்த {n} செய்திகள்:",
    "Telugu":    "చివరి {n} సందేశాలు:",
    "Kannada":   "ಕೊನೆಯ {n} ಸಂದೇಶಗಳು:",
    "Malayalam": "അവസാന {n} സന்ദേශങ്ങൾ:",
    "Hindi":     "अंतिम {n} संदेश:",
    "Punjabi":   "ਪਿਛਲੇ {n} ਸੁਨੇਹੇ:",
    "Gujarati":  "છેલ્લા {n} સંદેશ:",
    "Marathi":   "शेवटचे {n} संदेश:",
    "Bengali":   "শেষ {n} বার্তা:",
    "Odia":      "ଶେଷ {n} ବାର୍ତ୍ତା:",
    "English":   "Last {n} messages:",
}

VOICE_SENT = {
    "Tamil":     "குரல் அனுப்பப்பட்டது",
    "Telugu":    "వాయిస్ పంపబడింది",
    "Kannada":   "ವಾಯ್ಸ್ ಕಳುಹಿಸಲಾಗಿದೆ",
    "Malayalam": "വോയ്സ് അയച്ചു",
    "Hindi":     "वॉइस भेजा गया",
    "Punjabi":   "ਵੌਇਸ ਭੇਜਿਆ ਗਿਆ",
    "Gujarati":  "વૉઇસ મોકલ્યો",
    "Marathi":   "व्हॉइस पाठवले",
    "Bengali":   "ভয়েস পাঠানো হয়েছে",
    "Odia":      "ଭଏସ ପଠାଯାଇଛି",
    "English":   "Voice sent",
}

VOICE_SENT_OFFLINE = {
    "Tamil":     "குரல் அனுப்பப்பட்டது (ஆஃப்லைன்)",
    "Telugu":    "వాయిస్ పంపబడింది (ఆఫ్‌లైన్)",
    "Kannada":   "ವಾಯ್ಸ್ ಕಳುಹಿಸಲಾಗಿದೆ (ಆಫ್‌ಲೈನ್)",
    "Malayalam": "വോയ്സ് അയച്ചു (ഓഫ്‌ലൈൻ)",
    "Hindi":     "वॉइस भेजा गया (ऑफलाइन)",
    "Punjabi":   "ਵੌਇਸ ਭੇਜਿਆ ਗਿਆ (ਆਫਲਾਈਨ)",
    "Gujarati":  "વૉઇસ મોકલ્યો (ઑફ્‌લાઇન)",
    "Marathi":   "व्हॉइस पाठवले (ऑफलाइन)",
    "Bengali":   "ভয়েস পাঠানো হয়েছে (অফলাইন)",
    "Odia":      "ଭଏସ ପଠାଯାଇଛି (ଅଫଲାଇନ)",
    "English":   "Voice sent (offline)",
}

CHAT_CANCELLED = {
    "Tamil":     "அரட்டை ரத்து செய்யப்பட்டது.",
    "Telugu":    "చాట్ రద్దు చేయబడింది.",
    "Kannada":   "ಚಾಟ್ ರದ್ದುಗೊಳಿಸಲಾಗಿದೆ.",
    "Malayalam": "ചാറ്റ് റദ്ദാക്കി.",
    "Hindi":     "चैट रद्द की गई।",
    "Punjabi":   "ਚੈਟ ਰੱਦ ਕੀਤੀ ਗਈ।",
    "Gujarati":  "ચેટ રદ્દ કરવામાં આવ્યો.",
    "Marathi":   "चॅट रद्द केले.",
    "Bengali":   "চ্যাট বাতিল করা হয়েছে।",
    "Odia":      "ଚ୍ୟାଟ ବାତିଲ ହୋଇଛି।",
    "English":   "Chat cancelled.",
}


# ═══════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════

def get_msg(msg_dict: dict, lang: str) -> str:
    """Return message in user's language, fallback to English."""
    return msg_dict.get(lang, msg_dict["English"])


def fmt(msg_dict: dict, language: str, **kwargs) -> str:
    """Get message and format with keyword args."""
    return get_msg(msg_dict, language).format(**kwargs)