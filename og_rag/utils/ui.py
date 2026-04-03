"""
utils/ui.py  — v2
──────────────────
All UI strings, keyboards, and helpers for Agrithm.

Changes vs v1:
  • Full alarm UI section added at the bottom:
      - alarm_list_keyboard()       — rich inline keyboard with category icons
      - alarm_confirm_keyboard()    — confirm / edit / cancel after set
      - alarm_set_success_text()    — formatted alarm-set confirmation
      - alarm_list_header_text()    — header for alarm list messages
      - alarm_empty_text()          — no-alarms state
      - alarm_next_text()           — "next alarm in X min" line
      - alarm_fire_text()           — the ring message sent to user
      - voice_hint_text()           — voice command hint shown in menus
  • All existing exports preserved — bot.py requires no changes.
"""

from __future__ import annotations

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

# ══════════════════════════════════════════════════════════════════
# LANGUAGE LIST
# ══════════════════════════════════════════════════════════════════

SUPPORTED_LANGUAGES = [
    "English", "Hindi", "Telugu", "Tamil",
    "Kannada", "Malayalam", "Marathi", "Gujarati",
]

# ══════════════════════════════════════════════════════════════════
# MENU BUTTON LABELS  (action_key → display label, per language)
# ══════════════════════════════════════════════════════════════════

MENU_BUTTONS: dict[str, dict[str, str]] = {
    "English": {
        "ask":     "🌾 Ask Question",
        "mandi":   "📊 Mandi Prices",
        "connect": "👥 Connect Farmers",
        "disease": "🔬 Disease Check",
        "news":    "📰 Daily News",
        "profile": "👤 My Profile",
        "chat":    "💬 Chat Room",
        "alarm":   "⏰ My Alarms",
    },
    "Hindi": {
        "ask":     "🌾 सवाल पूछें",
        "mandi":   "📊 मंडी भाव",
        "connect": "👥 किसान जोड़ें",
        "disease": "🔬 रोग जांच",
        "news":    "📰 खेती समाचार",
        "profile": "👤 मेरी प्रोफाइल",
        "chat":    "💬 चैट रूम",
        "alarm":   "⏰ मेरे अलार्म",
    },
    "Telugu": {
        "ask":     "🌾 ప్రశ్న అడగండి",
        "mandi":   "📊 మండి ధరలు",
        "connect": "👥 రైతులను కలపండి",
        "disease": "🔬 వ్యాధి తనిఖీ",
        "news":    "📰 వ్యవసాయ వార్తలు",
        "profile": "👤 నా ప్రొఫైల్",
        "chat":    "💬 చాట్ రూమ్",
        "alarm":   "⏰ నా అలారాలు",
    },
    "Tamil": {
        "ask":     "🌾 கேள்வி கேளுங்கள்",
        "mandi":   "📊 மண்டி விலைகள்",
        "connect": "👥 விவசாயிகளை இணைக்கவும்",
        "disease": "🔬 நோய் சோதனை",
        "news":    "📰 வேளாண் செய்திகள்",
        "profile": "👤 என் சுயவிவரம்",
        "chat":    "💬 அரட்டை அறை",
        "alarm":   "⏰ என் அலாரங்கள்",
    },
    "Kannada": {
        "ask":     "🌾 ಪ್ರಶ್ನೆ ಕೇಳಿ",
        "mandi":   "📊 ಮಂಡಿ ಬೆಲೆಗಳು",
        "connect": "👥 ರೈತರನ್ನು ಸಂಪರ್ಕಿಸಿ",
        "disease": "🔬 ರೋಗ ತಪಾಸಣೆ",
        "news":    "📰 ಕೃಷಿ ಸುದ್ದಿ",
        "profile": "👤 ನನ್ನ ಪ್ರೊಫೈಲ್",
        "chat":    "💬 ಚಾಟ್ ರೂಮ್",
        "alarm":   "⏰ ನನ್ನ ಅಲಾರಂಗಳು",
    },
    "Malayalam": {
        "ask":     "🌾 ചോദ്യം ചോദിക്കൂ",
        "mandi":   "📊 മണ്ടി വില",
        "connect": "👥 കർഷകരെ ബന്ധിപ്പിക്കൂ",
        "disease": "🔬 രോഗ പരിശോധന",
        "news":    "📰 കൃഷി വാർത്ത",
        "profile": "👤 എന്റെ പ്രൊഫൈൽ",
        "chat":    "💬 ചാറ്റ് റൂം",
        "alarm":   "⏰ എന്റെ അലാറങ്ങൾ",
    },
    "Marathi": {
        "ask":     "🌾 प्रश्न विचारा",
        "mandi":   "📊 मंडी भाव",
        "connect": "👥 शेतकरी जोडा",
        "disease": "🔬 रोग तपासणी",
        "news":    "📰 शेती बातम्या",
        "profile": "👤 माझी प्रोफाईल",
        "chat":    "💬 चॅट रूम",
        "alarm":   "⏰ माझे अलार्म",
    },
    "Gujarati": {
        "ask":     "🌾 પ્રશ્ન પૂછો",
        "mandi":   "📊 મંડી ભાવ",
        "connect": "👥 ખેડૂત જોડો",
        "disease": "🔬 રોગ તપાસ",
        "news":    "📰 ખેતી સમાચાર",
        "profile": "👤 મારી પ્રોફાઇલ",
        "chat":    "💬 ચેટ રૂમ",
        "alarm":   "⏰ મારા એલાર્મ",
    },
}

CHAT_BUTTONS: dict[str, dict[str, str]] = {
    "English":   {"leave": "🚪 Leave Chat",    "history": "📜 View History"},
    "Hindi":     {"leave": "🚪 चैट छोड़ें",     "history": "📜 इतिहास देखें"},
    "Telugu":    {"leave": "🚪 చాట్ వదలండి",    "history": "📜 చరిత్ర చూడండి"},
    "Tamil":     {"leave": "🚪 அரட்டையை விடு", "history": "📜 வரலாற்றைப் பார்"},
    "Kannada":   {"leave": "🚪 ಚಾಟ್ ಬಿಡಿ",      "history": "📜 ಇತಿಹಾಸ ನೋಡಿ"},
    "Malayalam": {"leave": "🚪 ചാറ്റ് വിടൂ",     "history": "📜 ചരിത്രം കാണൂ"},
    "Marathi":   {"leave": "🚪 चॅट सोडा",       "history": "📜 इतिहास पहा"},
    "Gujarati":  {"leave": "🚪 ચેટ છોડો",       "history": "📜 ઇતિહાસ જુઓ"},
}

# ══════════════════════════════════════════════════════════════════
# UI STRING CONSTANTS  (multilingual dict, key → {lang: text})
# ══════════════════════════════════════════════════════════════════

GREETINGS: dict[str, str] = {
    "English":   "👋 Welcome to *Agrithm* — Your AI Farming Assistant!\n\nLet's get you set up in seconds.",
    "Hindi":     "👋 *Agrithm* में आपका स्वागत है — आपका AI कृषि सहायक!\n\nचलिए कुछ सेकंड में शुरू करते हैं।",
    "Telugu":    "👋 *Agrithm* కి స్వాగతం — మీ AI వ్యవసాయ సహాయకుడు!\n\nకొన్ని సెకన్లలో ప్రారంభిద్దాం.",
    "Tamil":     "👋 *Agrithm* வரவேற்கிறோம் — உங்கள் AI விவசாய உதவியாளர்!\n\nசில வினாடிகளில் தொடங்குவோம்.",
    "Kannada":   "👋 *Agrithm* ಗೆ ಸ್ವಾಗತ — ನಿಮ್ಮ AI ಕೃಷಿ ಸಹಾಯಕ!\n\nಕೆಲವು ಸೆಕೆಂಡ್‌ಗಳಲ್ಲಿ ಪ್ರಾರಂಭಿಸೋಣ.",
    "Malayalam": "👋 *Agrithm* ലേക്ക് സ്വാഗതം — നിങ്ങളുടെ AI കൃഷി സഹായി!\n\nചില സെക്കൻഡുകളിൽ ആരംഭിക്കാം.",
    "Marathi":   "👋 *Agrithm* मध्ये आपले स्वागत आहे — आपला AI शेती सहाय्यक!\n\nकाही सेकंदात सुरुवात करूया.",
    "Gujarati":  "👋 *Agrithm* માં આપનું સ્વાગત છે — તમારો AI ખેતી સહાયક!\n\nચાલો થોડી સેકન્ડમાં શરૂ કરીએ.",
}

WELCOME_BACK: dict[str, str] = {
    "English":   "👋 Welcome back, *{name}*!\n\n🌾 Crop: {crop}\n📍 {village}\n\nWhat do you need help with today?",
    "Hindi":     "👋 वापस आपका स्वागत है, *{name}*!\n\n🌾 फसल: {crop}\n📍 {village}\n\nआज क्या मदद चाहिए?",
    "Telugu":    "👋 తిరిగి స్వాగతం, *{name}*!\n\n🌾 పంట: {crop}\n📍 {village}\n\nఈరోజు ఏమి కావాలి?",
    "Tamil":     "👋 மீண்டும் வரவேற்கிறோம், *{name}*!\n\n🌾 பயிர்: {crop}\n📍 {village}\n\nஇன்று என்ன உதவி வேண்டும்?",
    "Kannada":   "👋 ಮತ್ತೆ ಸ್ವಾಗತ, *{name}*!\n\n🌾 ಬೆಳೆ: {crop}\n📍 {village}\n\nಇಂದು ಏನು ಸಹಾಯ ಬೇಕು?",
    "Malayalam": "👋 തിരിച്ചുവരവ് സ്വാഗതം, *{name}*!\n\n🌾 വിള: {crop}\n📍 {village}\n\nഇന്ന് എന്ത് സഹായം വേണം?",
    "Marathi":   "👋 परत स्वागत, *{name}*!\n\n🌾 पीक: {crop}\n📍 {village}\n\nआज काय मदत हवी आहे?",
    "Gujarati":  "👋 પાછા સ્વાગત, *{name}*!\n\n🌾 પાક: {crop}\n📍 {village}\n\nઆજે શું મદદ જોઈએ?",
}

SHARE_LOCATION: dict[str, str] = {
    "English":   "📍 Please share your location so we can personalise advice for your region.",
    "Hindi":     "📍 कृपया अपनी लोकेशन शेयर करें ताकि हम आपके क्षेत्र के अनुसार सलाह दे सकें।",
    "Telugu":    "📍 దయచేసి మీ స్థానం షేర్ చేయండి, మేము మీ ప్రాంతానికి సలహా ఇవ్వగలం.",
    "Tamil":     "📍 உங்கள் இருப்பிடத்தை பகிருங்கள், நாங்கள் உங்கள் பகுதிக்கு ஆலோசனை தரலாம்.",
    "Kannada":   "📍 ನಿಮ್ಮ ಸ್ಥಳ ಹಂಚಿಕೊಳ್ಳಿ, ನಾವು ನಿಮ್ಮ ಪ್ರದೇಶಕ್ಕೆ ಸಲಹೆ ನೀಡಬಹುದು.",
    "Malayalam": "📍 നിങ്ങളുടെ സ്ഥാനം പങ്കിടൂ, നിങ്ങളുടെ പ്രദേശത്തിന് ഉപദേശം നൽകാൻ കഴിയും.",
    "Marathi":   "📍 कृपया आपले स्थान शेअर करा जेणेकरून आम्ही आपल्या क्षेत्रासाठी सल्ला देऊ शकतो.",
    "Gujarati":  "📍 કૃપા કરીને તમારું સ્થાન શેર કરો જેથી અમે તમારા વિસ્તાર માટે સલાહ આપી શકીએ.",
}

CHOOSE_LANGUAGE: dict[str, str] = {
    "English":   "🌐 Choose your language:",
    "Hindi":     "🌐 अपनी भाषा चुनें:",
    "Telugu":    "🌐 మీ భాషను ఎంచుకోండి:",
    "Tamil":     "🌐 உங்கள் மொழியை தேர்ந்தெடுங்கள்:",
    "Kannada":   "🌐 ನಿಮ್ಮ ಭಾಷೆ ಆಯ್ಕೆ ಮಾಡಿ:",
    "Malayalam": "🌐 നിങ്ങളുടെ ഭാഷ തിരഞ്ഞെടുക്കൂ:",
    "Marathi":   "🌐 तुमची भाषा निवडा:",
    "Gujarati":  "🌐 તમારી ભાષા પસંદ કરો:",
}

ASK_NAME: dict[str, str] = {
    "English":   "👤 What's your name? (Type or send a voice message)",
    "Hindi":     "👤 आपका नाम क्या है? (टाइप करें या वॉइस मैसेज भेजें)",
    "Telugu":    "👤 మీ పేరు ఏమిటి? (టైప్ చేయండి లేదా వాయిస్ మెసేజ్ పంపండి)",
    "Tamil":     "👤 உங்கள் பெயர் என்ன? (தட்டச்சு செய்யுங்கள் அல்லது குரல் செய்தி அனுப்புங்கள்)",
    "Kannada":   "👤 ನಿಮ್ಮ ಹೆಸರೇನು? (ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಕಳುಹಿಸಿ)",
    "Malayalam": "👤 നിങ്ങളുടെ പേരെന്താണ്? (ടൈപ്പ് ചെയ്യൂ അല്ലെങ്കിൽ ശബ്ദ സന്ദേശം അയക്കൂ)",
    "Marathi":   "👤 तुमचे नाव काय आहे? (टाइप करा किंवा व्हॉइस मेसेज पाठवा)",
    "Gujarati":  "👤 તમારું નામ શું છે? (ટાઇપ કરો અથવા વૉઇસ સંદેશ મોકલો)",
}

HELLO_NAME: dict[str, str] = {
    "English":   "👋 Hello, *{name}*! Great to meet you.",
    "Hindi":     "👋 नमस्ते, *{name}*! आपसे मिलकर अच्छा लगा।",
    "Telugu":    "👋 హలో, *{name}*! మిమ్మల్ని కలిసి సంతోషం.",
    "Tamil":     "👋 வணக்கம், *{name}*! உங்களை சந்தித்து மகிழ்ச்சி.",
    "Kannada":   "👋 ಹಲೋ, *{name}*! ನಿಮ್ಮನ್ನು ಭೇಟಿಯಾಗಿ ಸಂತೋಷ.",
    "Malayalam": "👋 ഹലോ, *{name}*! നിങ്ങളെ കണ്ടതിൽ സന്തോഷം.",
    "Marathi":   "👋 नमस्कार, *{name}*! तुम्हाला भेटून आनंद झाला.",
    "Gujarati":  "👋 હેલો, *{name}*! તમને મળીને ખૂબ ખુશી.",
}

ASK_CROP: dict[str, str] = {
    "English":   "🌾 What crop do you mainly grow? (e.g. Rice, Wheat, Cotton)",
    "Hindi":     "🌾 आप मुख्य रूप से कौन सी फसल उगाते हैं? (जैसे: चावल, गेहूं, कपास)",
    "Telugu":    "🌾 మీరు ప్రధానంగా ఏ పంట పండిస్తారు? (ఉదా: వరి, గోధుమ, పత్తి)",
    "Tamil":     "🌾 நீங்கள் முக்கியமாக என்ன பயிர் விளைவிக்கிறீர்கள்? (எ.கா: அரிசி, கோதுமை, பருத்தி)",
    "Kannada":   "🌾 ನೀವು ಮುಖ್ಯವಾಗಿ ಯಾವ ಬೆಳೆ ಬೆಳೆಯುತ್ತೀರಿ? (ಉದಾ: ಅಕ್ಕಿ, ಗೋಧಿ, ಹತ್ತಿ)",
    "Malayalam": "🌾 നിങ്ങൾ പ്രധാനമായും ഏത് വിള കൃഷി ചെയ്യുന്നു? (ഉദാ: നെല്ല്, ഗോതമ്പ്, പരുത്തി)",
    "Marathi":   "🌾 तुम्ही मुख्यतः कोणते पीक घेता? (उदा: तांदूळ, गहू, कापूस)",
    "Gujarati":  "🌾 તમે મુખ્યત્વે કઈ ખેતી કરો છો? (દા.ત. ચોખા, ઘઉં, કપાસ)",
}

ASK_VILLAGE: dict[str, str] = {
    "English":   "🏘️ What is the name of your village or town?",
    "Hindi":     "🏘️ आपके गाँव या कस्बे का नाम क्या है?",
    "Telugu":    "🏘️ మీ గ్రామం లేదా పట్టణం పేరు ఏమిటి?",
    "Tamil":     "🏘️ உங்கள் கிராமம் அல்லது நகரத்தின் பெயர் என்ன?",
    "Kannada":   "🏘️ ನಿಮ್ಮ ಗ್ರಾಮ ಅಥವಾ ಪಟ್ಟಣದ ಹೆಸರೇನು?",
    "Malayalam": "🏘️ നിങ്ങളുടെ ഗ്രാമം അല്ലെങ്കിൽ പട്ടണത്തിന്റെ പേരെന്ത്?",
    "Marathi":   "🏘️ तुमच्या गावाचे किंवा शहराचे नाव काय आहे?",
    "Gujarati":  "🏘️ તમારા ગામ અથવા નગરનું નામ શું છે?",
}

ASK_VILLAGE_GPS: dict[str, str] = {
    "English":   "📍 Village detected from GPS: *{village}*\n\nIs this correct?",
    "Hindi":     "📍 GPS से गाँव मिला: *{village}*\n\nक्या यह सही है?",
    "Telugu":    "📍 GPS నుండి గ్రామం గుర్తించబడింది: *{village}*\n\nఇది సరైనదా?",
    "Tamil":     "📍 GPS மூலம் கிராமம் கண்டறியப்பட்டது: *{village}*\n\nஇது சரியா?",
    "Kannada":   "📍 GPS ಮೂಲಕ ಗ್ರಾಮ ಪತ್ತೆಯಾಯಿತು: *{village}*\n\nಇದು ಸರಿಯೇ?",
    "Malayalam": "📍 GPS ഉപയോഗിച്ച് ഗ്രാമം കണ്ടെത്തി: *{village}*\n\nഇത് ശരിയാണോ?",
    "Marathi":   "📍 GPS द्वारे गाव आढळले: *{village}*\n\nहे बरोबर आहे का?",
    "Gujarati":  "📍 GPS દ્વારા ગામ મળ્યું: *{village}*\n\nશું આ સાચું છે?",
}

PROFILE_SAVED: dict[str, str] = {
    "English":   "✅ Profile saved!\n\n👤 *{name}*\n🌾 {crop}\n📍 {village}",
    "Hindi":     "✅ प्रोफाइल सेव हो गई!\n\n👤 *{name}*\n🌾 {crop}\n📍 {village}",
    "Telugu":    "✅ ప్రొఫైల్ సేవ్ అయింది!\n\n👤 *{name}*\n🌾 {crop}\n📍 {village}",
    "Tamil":     "✅ சுயவிவரம் சேமிக்கப்பட்டது!\n\n👤 *{name}*\n🌾 {crop}\n📍 {village}",
    "Kannada":   "✅ ಪ್ರೊಫೈಲ್ ಉಳಿಸಲಾಗಿದೆ!\n\n👤 *{name}*\n🌾 {crop}\n📍 {village}",
    "Malayalam": "✅ പ്രൊഫൈൽ സേവ് ചെയ്തു!\n\n👤 *{name}*\n🌾 {crop}\n📍 {village}",
    "Marathi":   "✅ प्रोफाईल जतन केली!\n\n👤 *{name}*\n🌾 {crop}\n📍 {village}",
    "Gujarati":  "✅ પ્રોફાઇલ સાચવવામાં આવ્યો!\n\n👤 *{name}*\n🌾 {crop}\n📍 {village}",
}

WELCOME_COMPLETE: dict[str, str] = {
    "English":   "🎉 You're all set, *{name}*! Welcome to Agrithm.\n\nUse the menu below to get started.",
    "Hindi":     "🎉 सब तैयार है, *{name}*! Agrithm में स्वागत है।\n\nनीचे मेनू से शुरू करें।",
    "Telugu":    "🎉 అన్నీ సిద్ధం, *{name}*! Agrithm కి స్వాగతం.\n\nక్రింది మెనూ ఉపయోగించండి.",
    "Tamil":     "🎉 தயாராகிவிட்டது, *{name}*! Agrithm வரவேற்கிறது.\n\nகீழே உள்ள மெனுவை பயன்படுத்துங்கள்.",
    "Kannada":   "🎉 ಎಲ್ಲ ಸಿದ್ಧ, *{name}*! Agrithm ಗೆ ಸ್ವಾಗತ.\n\nಕೆಳಗಿನ ಮೆನು ಬಳಸಿ.",
    "Malayalam": "🎉 എല്ലാം ശരിയായി, *{name}*! Agrithm ലേക്ക് സ്വാഗതം.\n\nചുവടെയുള്ള മെനു ഉപയോഗിക്കൂ.",
    "Marathi":   "🎉 सगळं तयार आहे, *{name}*! Agrithm मध्ये स्वागत.\n\nखाली मेनू वापरा.",
    "Gujarati":  "🎉 બધું તૈયાર છે, *{name}*! Agrithm માં સ્વાગત.\n\nનીચેના મેનુ ઉપયોગ કરો.",
}

THINKING: dict[str, str] = {
    "English":   "🤔 Analysing your question...",
    "Hindi":     "🤔 आपका सवाल विश्लेषण कर रहे हैं...",
    "Telugu":    "🤔 మీ ప్రశ్నను విశ్లేషిస్తున్నాను...",
    "Tamil":     "🤔 உங்கள் கேள்வியை பகுப்பாய்வு செய்கிறேன்...",
    "Kannada":   "🤔 ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ವಿಶ್ಲೇಷಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🤔 നിങ്ങളുടെ ചോദ്യം വിശകലനം ചെയ്യുന്നു...",
    "Marathi":   "🤔 तुमचा प्रश्न विश्लेषण करतोय...",
    "Gujarati":  "🤔 તમારો પ્રશ્ન વિશ્લેષણ કરી રહ્યો છું...",
}

ASK_QUESTION_PROMPT: dict[str, str] = {
    "English":   "🌾 What farming question can I help you with?\n\n_(You can type or send a voice message)_",
    "Hindi":     "🌾 खेती से जुड़ा कौन सा सवाल पूछना चाहते हैं?\n\n_(टाइप करें या वॉइस मैसेज भेजें)_",
    "Telugu":    "🌾 వ్యవసాయ ప్రశ్న ఏమిటి?\n\n_(టైప్ చేయండి లేదా వాయిస్ మెసేజ్ పంపండి)_",
    "Tamil":     "🌾 என்ன விவசாய கேள்வி கேட்கலாம்?\n\n_(தட்டச்சு செய்யுங்கள் அல்லது குரல் செய்தி அனுப்புங்கள்)_",
    "Kannada":   "🌾 ಯಾವ ಕೃಷಿ ಪ್ರಶ್ನೆ ಕೇಳಲಿ?\n\n_(ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ವಾಯ್ಸ್ ಕಳುಹಿಸಿ)_",
    "Malayalam": "🌾 ഏത് കൃഷി ചോദ്യം ചോദിക്കണം?\n\n_(ടൈപ്പ് ചെയ്യൂ അല്ലെങ്കിൽ ശബ്ദ സന്ദേശം അയക്കൂ)_",
    "Marathi":   "🌾 शेतीबद्दल कोणता प्रश्न विचारायचा आहे?\n\n_(टाइप करा किंवा व्हॉइस मेसेज पाठवा)_",
    "Gujarati":  "🌾 ખેતી વિષે કઈ પ્રશ્ન પૂછવો છે?\n\n_(ટાઇપ કરો અથવા વૉઇસ મોકલો)_",
}

VOICE_DOWNLOAD_ERROR: dict[str, str] = {
    "English":   "❌ Couldn't download your voice message. Please try again.",
    "Hindi":     "❌ वॉइस मैसेज डाउनलोड नहीं हो सका। कृपया पुनः प्रयास करें।",
    "Telugu":    "❌ వాయిస్ మెసేజ్ డౌన్లోడ్ అవ్వలేదు. దయచేసి మళ్ళీ ప్రయత్నించండి.",
    "Tamil":     "❌ குரல் செய்தி பதிவிறக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்.",
    "Kannada":   "❌ ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಡೌನ್ಲೋಡ್ ಆಗಲಿಲ್ಲ. ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "Malayalam": "❌ ശബ്ദ സന്ദേശം ഡൗൺലോഡ് ചെയ്യാൻ കഴിഞ്ഞില്ല. വീണ്ടും ശ്രമിക്കൂ.",
    "Marathi":   "❌ व्हॉइस मेसेज डाउनलोड झाला नाही. पुन्हा प्रयत्न करा.",
    "Gujarati":  "❌ વૉઇસ સંદેશ ડાઉનલોડ થઈ શક્યો નહીં. ફરી પ્રયાસ કરો.",
}

VOICE_UNCLEAR: dict[str, str] = {
    "English":   "🎤 Couldn't understand your voice. Please speak clearly or type your question.",
    "Hindi":     "🎤 आपकी आवाज़ समझ नहीं आई। कृपया स्पष्ट बोलें या टाइप करें।",
    "Telugu":    "🎤 మీ వాయిస్ అర్థం కాలేదు. దయచేసి స్పష్టంగా మాట్లాడండి లేదా టైప్ చేయండి.",
    "Tamil":     "🎤 உங்கள் குரல் புரியவில்லை. தெளிவாக பேசுங்கள் அல்லது தட்டச்சு செய்யுங்கள்.",
    "Kannada":   "🎤 ನಿಮ್ಮ ಧ್ವನಿ ಅರ್ಥವಾಗಲಿಲ್ಲ. ಸ್ಪಷ್ಟವಾಗಿ ಮಾತನಾಡಿ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ.",
    "Malayalam": "🎤 നിങ്ങളുടെ ശബ്ദം മനസ്സിലായില്ല. വ്യക്തമായി സംസാരിക്കൂ അല്ലെങ്കിൽ ടൈപ്പ് ചെയ്യൂ.",
    "Marathi":   "🎤 तुमचा आवाज समजला नाही. स्पष्टपणे बोला किंवा टाइप करा.",
    "Gujarati":  "🎤 તમારો અવાજ સમજ ન આવ્યો. સ્પષ્ટ બોલો અથવા ટાઇપ કરો.",
}

ASK_MANDI_CROP: dict[str, str] = {
    "English":   "📊 Which crop do you want mandi prices for?",
    "Hindi":     "📊 किस फसल का मंडी भाव चाहिए?",
    "Telugu":    "📊 ఏ పంట మండి ధర కావాలి?",
    "Tamil":     "📊 எந்த பயிரின் மண்டி விலை வேண்டும்?",
    "Kannada":   "📊 ಯಾವ ಬೆಳೆಯ ಮಂಡಿ ಬೆಲೆ ಬೇಕು?",
    "Malayalam": "📊 ഏത് വിളയുടെ മണ്ടി വില വേണം?",
    "Marathi":   "📊 कोणत्या पिकाचा मंडी भाव हवा आहे?",
    "Gujarati":  "📊 કઈ ખેતીનો મંડી ભાવ જોઈએ?",
}

ASK_MANDI_CROP_NAME: dict[str, str] = {
    "English":   "📊 Type the crop name (e.g. Tomato, Onion, Rice):",
    "Hindi":     "📊 फसल का नाम लिखें (जैसे: टमाटर, प्याज, चावल):",
    "Telugu":    "📊 పంట పేరు టైప్ చేయండి (ఉదా: టమాటా, ఉల్లి, వరి):",
    "Tamil":     "📊 பயிர் பெயரை தட்டச்சு செய்யுங்கள் (எ.கா: தக்காளி, வெங்காயம், அரிசி):",
    "Kannada":   "📊 ಬೆಳೆ ಹೆಸರು ಟೈಪ್ ಮಾಡಿ (ಉದಾ: ಟೊಮ್ಯಾಟೊ, ಈರುಳ್ಳಿ, ಅಕ್ಕಿ):",
    "Malayalam": "📊 വിളയുടെ പേര് ടൈപ്പ് ചെയ്യൂ (ഉദാ: തക്കാളി, ഉള്ളി, നെല്ല്):",
    "Marathi":   "📊 पिकाचे नाव टाइप करा (उदा: टोमॅटो, कांदा, तांदूळ):",
    "Gujarati":  "📊 પાકનું નામ ટાઇપ કરો (દા.ત. ટામેટા, ડુંગળી, ચોખા):",
}

FETCHING_MANDI: dict[str, str] = {
    "English":   "📡 Fetching latest mandi prices...",
    "Hindi":     "📡 ताज़ा मंडी भाव ला रहे हैं...",
    "Telugu":    "📡 తాజా మండి ధరలు తీసుకుంటున్నాను...",
    "Tamil":     "📡 சமீபத்திய மண்டி விலைகளை பெறுகிறேன்...",
    "Kannada":   "📡 ತಾಜಾ ಮಂಡಿ ಬೆಲೆ ತರುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "📡 ഏറ്റവും പുതിയ മണ്ടി വില ലഭ്യമാക്കുന്നു...",
    "Marathi":   "📡 ताजे मंडी भाव आणत आहे...",
    "Gujarati":  "📡 તાજા મંડી ભાવ મેળવી રહ્યો છું...",
}

DISEASE_PROMPT: dict[str, str] = {
    "English":   "🔬 *Disease Check*\n\nSend a photo of your crop OR describe the symptoms in text or voice.",
    "Hindi":     "🔬 *रोग जांच*\n\nअपनी फसल की फोटो भेजें या लक्षण टेक्स्ट / वॉइस में बताएं।",
    "Telugu":    "🔬 *వ్యాధి తనిఖీ*\n\nమీ పంట ఫోటో పంపండి లేదా లక్షణాలు వివరించండి.",
    "Tamil":     "🔬 *நோய் சோதனை*\n\nபயிர் புகைப்படம் அனுப்புங்கள் அல்லது அறிகுறிகளை விவரியுங்கள்.",
    "Kannada":   "🔬 *ರೋಗ ತಪಾಸಣೆ*\n\nನಿಮ್ಮ ಬೆಳೆ ಫೋಟೋ ಕಳುಹಿಸಿ ಅಥವಾ ರೋಗಲಕ್ಷಣ ವಿವರಿಸಿ.",
    "Malayalam": "🔬 *രോഗ പരിശോധന*\n\nവിളയുടെ ഫോട്ടോ അയക്കൂ അല്ലെങ്കിൽ ലക്ഷണങ്ങൾ വിവരിക്കൂ.",
    "Marathi":   "🔬 *रोग तपासणी*\n\nपिकाचा फोटो पाठवा किंवा लक्षणे सांगा.",
    "Gujarati":  "🔬 *રોગ તપાસ*\n\nતમારા પાકનો ફોટો મોકલો અથવા લક્ષણો વર્ણવો.",
}

ANALYSING_IMAGE: dict[str, str] = {
    "English":   "🔍 Analysing your crop image...",
    "Hindi":     "🔍 आपकी फसल की छवि का विश्लेषण कर रहे हैं...",
    "Telugu":    "🔍 మీ పంట చిత్రాన్ని విశ్లేషిస్తున్నాను...",
    "Tamil":     "🔍 உங்கள் பயிர் படத்தை பகுப்பாய்வு செய்கிறேன்...",
    "Kannada":   "🔍 ನಿಮ್ಮ ಬೆಳೆ ಚಿತ್ರ ವಿಶ್ಲೇಷಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🔍 നിങ്ങളുടെ വിളയുടെ ചിത്രം വിശകലനം ചെയ്യുന്നു...",
    "Marathi":   "🔍 तुमच्या पिकाचे चित्र विश्लेषण करतोय...",
    "Gujarati":  "🔍 તમારા પાકની છબી વિશ્લેષણ કરી રહ્યો છું...",
}

CHECKING_SYMPTOMS: dict[str, str] = {
    "English":   "🔍 Checking symptoms...",
    "Hindi":     "🔍 लक्षण जाँच रहे हैं...",
    "Telugu":    "🔍 లక్షణాలు తనిఖీ చేస్తున్నాను...",
    "Tamil":     "🔍 அறிகுறிகளை சரிபார்க்கிறேன்...",
    "Kannada":   "🔍 ರೋಗಲಕ್ಷಣ ಪರಿಶೀಲಿಸುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🔍 ലക്ഷണങ്ങൾ പരിശോധിക്കുന്നു...",
    "Marathi":   "🔍 लक्षणे तपासत आहे...",
    "Gujarati":  "🔍 લક્ષણો તપાસી રહ્યો છું...",
}

DISEASE_VOICE_UNCLEAR: dict[str, str] = {
    "English":   "🎤 Couldn't understand the disease symptoms from your voice. Please describe in text.",
    "Hindi":     "🎤 वॉइस से रोग के लक्षण समझ नहीं आए। कृपया टेक्स्ट में बताएं।",
    "Telugu":    "🎤 వాయిస్ నుండి వ్యాధి లక్షణాలు అర్థం కాలేదు. దయచేసి టెక్స్ట్ లో వివరించండి.",
    "Tamil":     "🎤 குரலிலிருந்து நோயின் அறிகுறிகள் புரியவில்லை. உரையில் விவரியுங்கள்.",
    "Kannada":   "🎤 ವಾಯ್ಸ್ ನಿಂದ ರೋಗಲಕ್ಷಣ ತಿಳಿಯಲಿಲ್ಲ. ದಯವಿಟ್ಟು ಪಠ್ಯದಲ್ಲಿ ವಿವರಿಸಿ.",
    "Malayalam": "🎤 ശബ്ദത്തിൽ നിന്ന് രോഗലക്ഷണം മനസ്സിലായില്ല. ടെക്സ്റ്റിൽ വിവരിക്കൂ.",
    "Marathi":   "🎤 आवाजातून रोगाची लक्षणे समजली नाही. कृपया मजकूरात सांगा.",
    "Gujarati":  "🎤 અવાજ પરથી રોગના લક્ષણો સમજ ન આવ્યા. ટેક્સ્ટમાં જણાવો.",
}

DISEASE_TEXT_PROMPT: dict[str, str] = {
    "English":   "📝 Describe the disease symptoms in text:",
    "Hindi":     "📝 रोग के लक्षण टेक्स्ट में बताएं:",
    "Telugu":    "📝 వ్యాధి లక్షణాలు టెక్స్ట్ లో వివరించండి:",
    "Tamil":     "📝 நோயின் அறிகுறிகளை உரையில் விவரியுங்கள்:",
    "Kannada":   "📝 ರೋಗಲಕ್ಷಣ ಪಠ್ಯದಲ್ಲಿ ವಿವರಿಸಿ:",
    "Malayalam": "📝 രോഗലക്ഷണങ്ങൾ ടെക്സ്റ്റിൽ വിവരിക്കൂ:",
    "Marathi":   "📝 रोगाची लक्षणे मजकूरात सांगा:",
    "Gujarati":  "📝 રોગના લક્ષણો ટેક્સ્ટમાં વર્ણવો:",
}

IMAGE_ANALYSE_FAIL: dict[str, str] = {
    "English":   "❌ Couldn't analyse the image. Please describe the symptoms in text.",
    "Hindi":     "❌ छवि का विश्लेषण नहीं हो सका। कृपया लक्षण टेक्स्ट में बताएं।",
    "Telugu":    "❌ చిత్రం విశ్లేషించలేకపోయాను. దయచేసి లక్షణాలు టెక్స్ట్ లో వివరించండి.",
    "Tamil":     "❌ படத்தை பகுப்பாய்வு செய்ய முடியவில்லை. அறிகுறிகளை உரையில் விவரியுங்கள்.",
    "Kannada":   "❌ ಚಿತ್ರ ವಿಶ್ಲೇಷಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ. ರೋಗಲಕ್ಷಣ ಪಠ್ಯದಲ್ಲಿ ವಿವರಿಸಿ.",
    "Malayalam": "❌ ചിത്രം വിശകലനം ചെയ്യാൻ കഴിഞ്ഞില്ല. ലക്ഷണങ്ങൾ ടെക്സ്റ്റിൽ വിവരിക്കൂ.",
    "Marathi":   "❌ चित्र विश्लेषण करता आले नाही. लक्षणे मजकूरात सांगा.",
    "Gujarati":  "❌ છબી વિશ્લેષણ થઈ શક્યું નહીં. ટેક્સ્ટમાં લક્ષણો વર્ણવો.",
}

SET_NEWS_TIME: dict[str, str] = {
    "English":   "⏰ Set your daily news & alarm time using the clock below.",
    "Hindi":     "⏰ नीचे घड़ी से अपना दैनिक समाचार और अलार्म समय सेट करें।",
    "Telugu":    "⏰ క్రింద గడియారం ద్వారా మీ రోజువారీ వార్తలు & అలారం సమయం సెట్ చేయండి.",
    "Tamil":     "⏰ கீழே உள்ள கடிகாரம் மூலம் உங்கள் தினசரி செய்தி & அலாரம் நேரத்தை அமைக்கவும்.",
    "Kannada":   "⏰ ಕೆಳಗಿನ ಗಡಿಯಾರ ಮೂಲಕ ನಿಮ್ಮ ದೈನಂದಿನ ಸುದ್ದಿ & ಅಲಾರಂ ಸಮಯ ಹೊಂದಿಸಿ.",
    "Malayalam": "⏰ ചുവടെ ക്ലോക്ക് ഉപയോഗിച്ച് ദൈനദിന വാർത്ത & അലാറം സമയം ക്രമീകരിക്കൂ.",
    "Marathi":   "⏰ खाली घड्याळ वापरून तुमचे दैनिक बातम्या & अलार्म वेळ सेट करा.",
    "Gujarati":  "⏰ નીચે ઘડિયાળ દ્વારા તમારા દૈનિક સમાચાર & એલાર્મ સમય સેટ કરો.",
}

NEWS_TIME_SET: dict[str, str] = {
    "English":   "✅ Alarm & news time set to *{time}*.\n\nYou'll receive a farming tip and news every day at this time.",
    "Hindi":     "✅ अलार्म और समाचार का समय *{time}* पर सेट हो गया।\n\nआपको हर दिन इस समय खेती टिप और समाचार मिलेंगे।",
    "Telugu":    "✅ అలారం & వార్తలు సమయం *{time}* కి సెట్ అయింది.\n\nప్రతిరోజూ ఈ సమయంలో వ్యవసాయ చిట్కాలు & వార్తలు వస్తాయి.",
    "Tamil":     "✅ அலாரம் & செய்தி நேரம் *{time}* க்கு அமைக்கப்பட்டது.\n\nதினமும் இந்த நேரத்தில் விவசாய குறிப்புகள் & செய்திகள் கிடைக்கும்.",
    "Kannada":   "✅ ಅಲಾರಂ & ಸುದ್ದಿ ಸಮಯ *{time}* ಕ್ಕೆ ಹೊಂದಿಸಲಾಗಿದೆ.\n\nಪ್ರತಿ ದಿನ ಈ ಸಮಯದಲ್ಲಿ ಕೃಷಿ ಸಲಹೆ & ಸುದ್ದಿ ಸಿಗುತ್ತದೆ.",
    "Malayalam": "✅ അലാറം & വാർത്ത സമയം *{time}* ആക്കി.\n\nദൈനദിന ഈ സമയത്ത് കൃഷി ടിപ്സ് & വാർത്ത ലഭിക്കും.",
    "Marathi":   "✅ अलार्म & बातम्यांची वेळ *{time}* वर सेट झाली.\n\nदररोज या वेळी शेती टिप आणि बातम्या मिळतील.",
    "Gujarati":  "✅ એલાર્મ & સમાચારનો સમય *{time}* પર સેટ થઈ ગયો.\n\nદરરોજ આ સમયે ખેતી ટીપ્સ & સમાચાર મળશે.",
}

PROFILE_VIEW: dict[str, str] = {
    "English": (
        "👤 *Your Profile*\n\n"
        "🏷 Name     : {name}\n"
        "🌾 Crop     : {crop}\n"
        "🏘 Village  : {village}\n"
        "🗺 District : {district}\n"
        "🌐 Language : {language}\n"
        "⏰ News Time: {news_time}\n"
        "🌍 Timezone : {timezone}"
    ),
}

FINDING_FARMERS: dict[str, str] = {
    "English":   "🔍 Looking for farmers near you who grow {crop}...",
    "Hindi":     "🔍 आपके नज़दीक {crop} उगाने वाले किसान ढूंढ रहे हैं...",
    "Telugu":    "🔍 మీ దగ్గర {crop} పండించే రైతులను కనుగొంటున్నాను...",
    "Tamil":     "🔍 உங்களுக்கு அருகில் {crop} பயிரிடும் விவசாயிகளை தேடுகிறேன்...",
    "Kannada":   "🔍 ನಿಮ್ಮ ಹತ್ತಿರ {crop} ಬೆಳೆಯುವ ರೈತರನ್ನು ಹುಡುಕುತ್ತಿದ್ದೇನೆ...",
    "Malayalam": "🔍 നിങ്ങൾക്ക് സമീപം {crop} കൃഷി ചെയ്യുന്ന കർഷകരെ തിരയുന്നു...",
    "Marathi":   "🔍 तुमच्या जवळ {crop} पिकवणारे शेतकरी शोधत आहे...",
    "Gujarati":  "🔍 તમારી નજીક {crop} ઉગાડનારા ખેડૂઓ શોધી રહ્યો છું...",
}

NO_FARMERS_NEARBY: dict[str, str] = {
    "English":   "😔 No farmers found nearby growing {crop}.",
    "Hindi":     "😔 {crop} उगाने वाला कोई किसान नज़दीक नहीं मिला।",
    "Telugu":    "😔 దగ్గరలో {crop} పండించే రైతులు కనుగొనబడలేదు.",
    "Tamil":     "😔 {crop} பயிரிடும் விவசாயிகள் அருகில் இல்லை.",
    "Kannada":   "😔 ಹತ್ತಿರ {crop} ಬೆಳೆಯುವ ರೈತರು ಸಿಗಲಿಲ್ಲ.",
    "Malayalam": "😔 {crop} കൃഷി ചെയ്യുന്ന കർഷകർ ഇവിടെ കണ്ടെത്തിയില്ല.",
    "Marathi":   "😔 जवळपास {crop} पिकवणारे शेतकरी सापडले नाहीत.",
    "Gujarati":  "😔 નજીક {crop} ઉગાડતા ખેડૂઓ મળ્યા નહીં.",
}

FARMERS_FOUND_HEADER: dict[str, str] = {
    "English":   "👥 *{n} farmer(s) found near you growing {crop}:*",
    "Hindi":     "👥 *{n} किसान मिले जो {crop} उगाते हैं:*",
    "Telugu":    "👥 *{n} రైతులు {crop} పండిస్తున్నారు:*",
    "Tamil":     "👥 *{n} விவசாயிகள் {crop} பயிரிடுகின்றனர்:*",
    "Kannada":   "👥 *{n} ರೈತರು {crop} ಬೆಳೆಯುತ್ತಿದ್ದಾರೆ:*",
    "Malayalam": "👥 *{n} കർഷകർ {crop} കൃഷി ചെയ്യുന്നു:*",
    "Marathi":   "👥 *{n} शेतकरी {crop} पिकवतात:*",
    "Gujarati":  "👥 *{n} ખેડૂઓ {crop} ઉગાડે છે:*",
}

COMPLETE_PROFILE_FIRST: dict[str, str] = {
    "English":   "⚠️ Please complete your profile first by running /start.",
    "Hindi":     "⚠️ कृपया पहले /start चलाकर अपनी प्रोफाइल पूरी करें।",
    "Telugu":    "⚠️ దయచేసి ముందు /start నడిపి మీ ప్రొఫైల్ పూర్తి చేయండి.",
    "Tamil":     "⚠️ முதலில் /start இயக்கி உங்கள் சுயவிவரத்தை நிறைவு செய்யுங்கள்.",
    "Kannada":   "⚠️ ದಯವಿಟ್ಟು ಮೊದಲು /start ಚಲಾಯಿಸಿ ಪ್ರೊಫೈಲ್ ಪೂರ್ಣಗೊಳಿಸಿ.",
    "Malayalam": "⚠️ ആദ്യം /start ഉപയോഗിച്ച് നിങ്ങളുടെ പ്രൊഫൈൽ പൂർത്തിയാക്കൂ.",
    "Marathi":   "⚠️ कृपया आधी /start चालवून प्रोफाईल पूर्ण करा.",
    "Gujarati":  "⚠️ કૃપા કરીને પહેલા /start ચલાવીને પ્રોફાઇલ પૂર્ણ કરો.",
}

USE_MENU: dict[str, str] = {
    "English":   "👇 Please use the menu below.",
    "Hindi":     "👇 कृपया नीचे मेनू का उपयोग करें।",
    "Telugu":    "👇 దయచేసి క్రింద మెనూ ఉపయోగించండి.",
    "Tamil":     "👇 கீழே உள்ள மெனுவை பயன்படுத்துங்கள்.",
    "Kannada":   "👇 ದಯವಿಟ್ಟು ಕೆಳಗಿನ ಮೆನು ಬಳಸಿ.",
    "Malayalam": "👇 ചുവടെ മെനു ഉപയോഗിക്കൂ.",
    "Marathi":   "👇 कृपया खाली मेनू वापरा.",
    "Gujarati":  "👇 કૃપા કરીને નીચે મેનુ ઉપયોગ કરો.",
}

TYPE_QUESTION: dict[str, str] = {
    "English":   "💬 Type your question or use a menu option:",
    "Hindi":     "💬 अपना सवाल टाइप करें या मेनू विकल्प चुनें:",
    "Telugu":    "💬 మీ ప్రశ్న టైప్ చేయండి లేదా మెనూ ఎంపిక చేయండి:",
    "Tamil":     "💬 உங்கள் கேள்வியை தட்டச்சு செய்யுங்கள் அல்லது மெனு விருப்பம் தேர்வு செய்யுங்கள்:",
    "Kannada":   "💬 ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಟೈಪ್ ಮಾಡಿ ಅಥವಾ ಮೆನು ಆಯ್ಕೆ ಮಾಡಿ:",
    "Malayalam": "💬 നിങ്ങളുടെ ചോദ്യം ടൈപ്പ് ചെയ്യൂ അല്ലെങ്കിൽ മെനു ഓപ്ഷൻ ഉപയോഗിക്കൂ:",
    "Marathi":   "💬 तुमचा प्रश्न टाइप करा किंवा मेनू पर्याय वापरा:",
    "Gujarati":  "💬 તમારો પ્રશ્ન ટાઇપ કરો અથવા મેનુ વિકલ્પ ઉપયોગ કરો:",
}

CANCELLED: dict[str, str] = {
    "English":   "❌ Cancelled.",
    "Hindi":     "❌ रद्द किया।",
    "Telugu":    "❌ రద్దు చేయబడింది.",
    "Tamil":     "❌ ரத்து செய்யப்பட்டது.",
    "Kannada":   "❌ ರದ್ದಾಯಿತು.",
    "Malayalam": "❌ റദ്ദ് ചെയ്തു.",
    "Marathi":   "❌ रद्द केले.",
    "Gujarati":  "❌ રદ્દ કર્યું.",
}

ERROR_GENERIC: dict[str, str] = {
    "English":   "⚠️ Something went wrong. Please try again.",
    "Hindi":     "⚠️ कुछ गलत हुआ। कृपया पुनः प्रयास करें।",
    "Telugu":    "⚠️ ఏదో తప్పు జరిగింది. దయచేసి మళ్ళీ ప్రయత్నించండి.",
    "Tamil":     "⚠️ ஏதோ தவறு நடந்தது. மீண்டும் முயற்சிக்கவும்.",
    "Kannada":   "⚠️ ಏನೋ ತಪ್ಪಾಗಿದೆ. ದಯವಿಟ್ಟು ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ.",
    "Malayalam": "⚠️ എന്തോ കുഴപ്പം. വീണ്ടും ശ്രമിക്കൂ.",
    "Marathi":   "⚠️ काहीतरी चूक झाली. पुन्हा प्रयत्न करा.",
    "Gujarati":  "⚠️ કંઈક ભૂલ થઈ. ફરી પ્રયાસ કરો.",
}

FALLBACK: dict[str, str] = {
    "English":   "🤷 I didn't understand that. Please use the menu or type a farming question.",
    "Hindi":     "🤷 मैं यह नहीं समझा। कृपया मेनू का उपयोग करें या खेती का सवाल पूछें।",
    "Telugu":    "🤷 అర్థం కాలేదు. మెనూ ఉపయోగించండి లేదా వ్యవసాయ ప్రశ్న టైప్ చేయండి.",
    "Tamil":     "🤷 புரியவில்லை. மெனுவை பயன்படுத்துங்கள் அல்லது விவசாய கேள்வி கேளுங்கள்.",
    "Kannada":   "🤷 ಅರ್ಥವಾಗಲಿಲ್ಲ. ಮೆನು ಬಳಸಿ ಅಥವಾ ಕೃಷಿ ಪ್ರಶ್ನೆ ಕೇಳಿ.",
    "Malayalam": "🤷 മനസ്സിലായില്ല. മെനു ഉപയോഗിക്കൂ അല്ലെങ്കിൽ കൃഷി ചോദ്യം ചോദിക്കൂ.",
    "Marathi":   "🤷 समजले नाही. मेनू वापरा किंवा शेती प्रश्न विचारा.",
    "Gujarati":  "🤷 સમજ ન આવ્યું. મેનુ ઉપયોગ કરો અથવા ખેતી પ્રશ્ન પૂછો.",
}

LOCATION_DETECTED: dict[str, str] = {
    "English":   "📍 Location detected!\n\n🏘 Village : {village}\n🗺 District: {district}\n🌍 Timezone: {timezone}",
    "Hindi":     "📍 लोकेशन मिल गई!\n\n🏘 गाँव   : {village}\n🗺 जिला   : {district}\n🌍 टाइमज़ोन: {timezone}",
    "Telugu":    "📍 లొకేషన్ గుర్తించబడింది!\n\n🏘 గ్రామం  : {village}\n🗺 జిల్లా  : {district}\n🌍 సమయమండలం: {timezone}",
    "Tamil":     "📍 இருப்பிடம் கண்டறியப்பட்டது!\n\n🏘 கிராமம்: {village}\n🗺 மாவட்டம்: {district}\n🌍 நேர மண்டலம்: {timezone}",
    "Kannada":   "📍 ಸ್ಥಳ ಪತ್ತೆಯಾಯಿತು!\n\n🏘 ಗ್ರಾಮ    : {village}\n🗺 ಜಿಲ್ಲೆ  : {district}\n🌍 ಸಮಯ ವಲಯ: {timezone}",
    "Malayalam": "📍 സ്ഥാനം കണ്ടെത്തി!\n\n🏘 ഗ്രാമം   : {village}\n🗺 ജില്ല    : {district}\n🌍 ടൈംസോൺ : {timezone}",
    "Marathi":   "📍 स्थान सापडले!\n\n🏘 गाव     : {village}\n🗺 जिल्हा  : {district}\n🌍 टाइमझोन: {timezone}",
    "Gujarati":  "📍 સ્થાન મળ્યું!\n\n🏘 ગામ      : {village}\n🗺 જિલ્લો  : {district}\n🌍 ટાઇમઝોન : {timezone}",
}

# Chat room strings
CHAT_WITH        = {"English": "💬 Chat with *{name}* ({crop}, {village})"}
CHOOSE_CHAT_PARTNER = {"English": "👥 Choose a farmer to chat with:"}
CONNECTED_TO     = {"English": "✅ Connected to *{name}*! Start chatting."}
LEFT_CHAT        = {"English": "🚪 You left the chat."}
WANT_TO_CHAT     = {"English": "💬 *{name}* wants to chat with you!\n\nCrop: {crop} | Village: {village}"}
PARTNER_LEFT     = {"English": "👋 *{name}* left the chat."}
SEND_MSG_HINT    = {"English": "💬 Send a message to *{name}*"}
NOT_IN_CHAT      = {"English": "⚠️ You're not in a chat. Use the menu to connect."}
SENT             = {"English": "✅ Sent"}
SENT_OFFLINE     = {"English": "✅ Sent (partner offline — will notify when they return)"}
VOICE_SENT       = {"English": "🎤 Voice sent to *{name}*"}
VOICE_SENT_OFFLINE = {"English": "🎤 Voice sent (partner offline)"}
CHAT_CANCELLED   = {"English": "❌ Chat request cancelled."}
LAST_N_MESSAGES  = {"English": "📜 Last {n} messages with *{name}*:"}


# ══════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════

def get_msg(msg_dict: dict[str, str], lang: str) -> str:
    """Return the message for the given language, falling back to English."""
    return msg_dict.get(lang) or msg_dict.get("English", "")


from collections import defaultdict

def fmt(msg_dict: dict[str, str], lang: str, **kwargs) -> str:
    msg = get_msg(msg_dict, lang)
    return msg.format_map(defaultdict(lambda: "N/A", kwargs))

# ══════════════════════════════════════════════════════════════════
# KEYBOARDS
# ══════════════════════════════════════════════════════════════════

def language_keyboard() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton("English"),  KeyboardButton("Hindi")],
        [KeyboardButton("Telugu"),   KeyboardButton("Tamil")],
        [KeyboardButton("Kannada"),  KeyboardButton("Malayalam")],
        [KeyboardButton("Marathi"),  KeyboardButton("Gujarati")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Share My Location", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def main_menu_keyboard(lang: str = "English", chat_unread: int = 0) -> ReplyKeyboardMarkup:
    buttons = MENU_BUTTONS.get(lang) or MENU_BUTTONS["English"]
    chat_label = buttons.get("chat", "💬 Chat Room")
    if chat_unread > 0:
        chat_label = f"{chat_label} ({chat_unread}🔔)"

    rows = [
        [KeyboardButton(buttons.get("ask",     "🌾 Ask Question")),
         KeyboardButton(buttons.get("mandi",   "📊 Mandi Prices"))],
        [KeyboardButton(buttons.get("connect", "👥 Connect Farmers")),
         KeyboardButton(buttons.get("disease", "🔬 Disease Check"))],
        [KeyboardButton(buttons.get("news",    "📰 Daily News")),
         KeyboardButton(buttons.get("profile", "👤 My Profile"))],
        [KeyboardButton(chat_label),
         KeyboardButton(buttons.get("alarm",   "⏰ My Alarms"))],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def chat_room_keyboard(lang: str = "English", in_chat: bool = False) -> ReplyKeyboardMarkup:
    buttons = CHAT_BUTTONS.get(lang) or CHAT_BUTTONS["English"]
    if in_chat:
        rows = [
            [KeyboardButton(buttons.get("leave",   "🚪 Leave Chat"))],
            [KeyboardButton(buttons.get("history", "📜 View History"))],
        ]
    else:
        rows = [[KeyboardButton(buttons.get("leave", "🚪 Leave Chat"))]]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ══════════════════════════════════════════════════════════════════
# ▼▼▼  ALARM UI — NEW IN v2  ▼▼▼
# ══════════════════════════════════════════════════════════════════

# Category icons and background colours shown in Telegram messages
_ALARM_CATEGORY_ICONS: dict[str, str] = {
    "irrigation": "💧",
    "spray":      "🌿",
    "harvest":    "🌾",
    "market":     "🏪",
    "feed":       "🐄",
    "other":      "⏰",
}

_ALARM_CATEGORY_LABELS: dict[str, str] = {
    "irrigation": "Irrigation",
    "spray":      "Spray / Pesticide",
    "harvest":    "Harvest time",
    "market":     "Market / Mandi",
    "feed":       "Animal feeding",
    "other":      "Alarm",
}

_DAY_SHORT = {
    "mon": "Mon", "tue": "Tue", "wed": "Wed", "thu": "Thu",
    "fri": "Fri", "sat": "Sat", "sun": "Sun", "daily": "Every day",
}


def _fmt_days(days: list[str]) -> str:
    if not days or "daily" in days:
        return "Every day"
    return ", ".join(_DAY_SHORT.get(d, d.capitalize()) for d in days)


def _alarm_icon(alarm: dict) -> str:
    cat = alarm.get("cat") or alarm.get("category", "other")
    return _ALARM_CATEGORY_ICONS.get(cat, "⏰")


def _alarm_category_label(alarm: dict) -> str:
    cat = alarm.get("cat") or alarm.get("category", "other")
    return _ALARM_CATEGORY_LABELS.get(cat, "Alarm")


# ── Inline keyboards ─────────────────────────────────────────────

def alarm_list_keyboard(alarms: list[dict]) -> InlineKeyboardMarkup:
    """
    Rich inline keyboard for the alarm list.
    Each alarm gets its own row: [icon+label+time] [🗑 Delete] [toggle]
    Bottom row: ➕ New alarm
    """
    rows = []
    for a in alarms:
        icon       = _alarm_icon(a)
        status     = "✅" if a.get("active") else "⏸"
        time_str   = a.get("time", "??:??")
        label      = a.get("label", "Alarm")
        days_str   = _fmt_days(a.get("days", ["daily"]))
        toggle_btn = "⏸" if a.get("active") else "▶"

        display = f"{status} {icon} {label} — {time_str}"
        rows.append([
            InlineKeyboardButton(display,    callback_data=f"alarm_noop_{a['id']}"),
            InlineKeyboardButton("🗑",       callback_data=f"alarm_del_{a['id']}"),
            InlineKeyboardButton(toggle_btn, callback_data=f"alarm_tog_{a['id']}"),
        ])
        # Sub-row: days info (non-interactive, shown as a noop button)
        rows.append([
            InlineKeyboardButton(
                f"     📅 {days_str}",
                callback_data=f"alarm_noop_{a['id']}",
            ),
        ])

    rows.append([InlineKeyboardButton("➕ New alarm", callback_data="alarm_new")])
    return InlineKeyboardMarkup(rows)


def alarm_confirm_keyboard(alarm_id: str) -> InlineKeyboardMarkup:
    """Confirm / Edit / Cancel keyboard shown right after an alarm is set."""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Confirm", callback_data=f"alarm_confirm_{alarm_id}"),
        InlineKeyboardButton("✏️ Edit",   callback_data=f"alarm_edit_{alarm_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"alarm_cancel_{alarm_id}"),
    ]])


# ── Message builders ─────────────────────────────────────────────

def alarm_set_success_text(alarm: dict, tz_name: str) -> str:
    """
    Formatted alarm-set confirmation message.
    Mirrors the interactive widget's card layout in text form.
    """
    icon      = _alarm_icon(alarm)
    label     = alarm.get("label", "Alarm")
    time_str  = alarm.get("time", "??:??")
    days_str  = _fmt_days(alarm.get("days", ["daily"]))
    cat_label = _alarm_category_label(alarm)

    return (
        f"{icon} *Alarm Set!*\n\n"
        f"🏷 Label    : {label}\n"
        f"📂 Category : {cat_label}\n"
        f"🕐 Time     : *{time_str}*\n"
        f"📅 Days     : {days_str}\n"
        f"🌍 Timezone : {tz_name}\n\n"
        f"I will ring you at *{time_str}* {days_str.lower()}. 🔔"
    )


def alarm_list_header_text(n: int) -> str:
    """Header line for the alarm list message."""
    if n == 0:
        return "⏰ *Your Alarms*"
    active_word = "alarm" if n == 1 else "alarms"
    return f"⏰ *Your Alarms* — {n} {active_word}"


def alarm_empty_text() -> str:
    """Message when a user has no alarms."""
    return (
        "⏰ You have no alarms set.\n\n"
        "Tap *New alarm* below or say:\n"
        "  • _\"Set alarm at 6 morning for irrigation\"_\n"
        "  • _\"Remind me at 5:30 for mandi\"_\n"
        "  • _\"Alarm pettandi 7 ki\"_ (Telugu)\n"
        "  • _\"Alarm lagao subah 5 baje\"_ (Hindi)"
    )


def alarm_next_text(label: str, time_str: str, minutes_away: int) -> str:
    """One-line 'next alarm' chip text shown at the top of the list."""
    if minutes_away < 60:
        eta = f"{minutes_away} min"
    elif minutes_away < 120:
        eta = f"1 h {minutes_away - 60} min"
    else:
        eta = f"{minutes_away // 60} h {minutes_away % 60} min"
    return f"🔔 Next: *{label}* at {time_str} — in {eta}"


def alarm_fire_text(alarm: dict, name: str) -> str:
    """
    The ring message pushed to the farmer when an alarm fires.
    Rich, encouraging, farmer-friendly.
    """
    icon      = _alarm_icon(alarm)
    label     = alarm.get("label", "Alarm")
    time_str  = alarm.get("time", "")
    cat_label = _alarm_category_label(alarm)

    return (
        f"🔔 *Alarm Ringing!*\n\n"
        f"{icon} *{label}*\n"
        f"📂 {cat_label}\n"
        f"🕐 It's {time_str} — time to act!\n\n"
        f"Good morning, *{name}*! 🌾\n"
        f"Wishing you a productive day on the farm. 🙏"
    )


def voice_hint_text(lang: str = "English") -> str:
    """
    Voice command hint shown in the alarm section of the main menu.
    Returns a short multilingual hint string.
    """
    hints = {
        "English":   '🎤 Say: _"Set alarm at 6 morning for irrigation"_',
        "Hindi":     '🎤 बोलें: _"Alarm lagao subah 6 baje"_',
        "Telugu":    '🎤 చెప్పండి: _"Alarm pettandi 6 ki"_',
        "Tamil":     '🎤 சொல்லுங்கள்: _"Alarm set pannu காலை 6 மணிக்கு"_',
        "Kannada":   '🎤 ಹೇಳಿ: _"Alarm set madi beligge 6 gantige"_',
        "Malayalam": '🎤 പറയൂ: _"Alarm set cheyyoo raaviley 6 manikku"_',
        "Marathi":   '🎤 म्हणा: _"Alarm lagav subah 6 vajta"_',
        "Gujarati":  '🎤 કહો: _"Alarm set karo subah 6 vajey"_',
    }
    return hints.get(lang) or hints["English"]