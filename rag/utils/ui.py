from telegram import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardRemove
)
from agrithm_config import LANGUAGES

# ── Language selection ────────────────────────────────────────────
def language_keyboard() -> ReplyKeyboardMarkup:
    """Builds keyboard from LANGUAGES in config — auto-updates when you add languages."""
    names = list(LANGUAGES.keys())
    # Split into rows of 2
    rows = [names[i:i+2] for i in range(0, len(names), 2)]
    return ReplyKeyboardMarkup(rows, one_time_keyboard=True, resize_keyboard=True)

# ── Location request ──────────────────────────────────────────────
def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📍 Share My Location", request_location=True)],
         ["✏️ Enter Manually"]],
        one_time_keyboard=True, resize_keyboard=True
    )

# ── Main menu ─────────────────────────────────────────────────────
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["🎙️ Ask a Question", "💰 Mandi Prices"],
        ["🤝 Connect with Farmers", "📰 Daily News Settings"],
        ["👤 My Profile"],
    ], resize_keyboard=True)

# ── Remove keyboard ───────────────────────────────────────────────
def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


# ═══════════════════════════════════════════════════════════════
# MESSAGE DICTIONARIES — all 11 languages
# ═══════════════════════════════════════════════════════════════

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

VOICE_PROMPT = {
    "Tamil":     "உங்கள் கேள்வியை குரல் செய்தியாக அனுப்பவும்.",
    "Telugu":    "మీ ప్రశ్నను వాయిస్ మెసేజ్‌గా పంపండి.",
    "Kannada":   "ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಆಗಿ ಕಳುಹಿಸಿ.",
    "Malayalam": "നിങ്ങളുടെ ചോദ്യം വോയ്സ് മെസേജായി അയക്കൂ.",
    "Hindi":     "अपना सवाल वॉइस मैसेज के रूप में भेजें।",
    "Punjabi":   "ਆਪਣਾ ਸਵਾਲ ਵੌਇਸ ਮੈਸੇਜ ਵਜੋਂ ਭੇਜੋ।",
    "Gujarati":  "તમારો પ્રશ્ન વૉઇસ મેસેજ તરીકે મોકલો.",
    "Marathi":   "तुमचा प्रश्न व्हॉइस मेसेज म्हणून पाठवा.",
    "Bengali":   "আপনার প্রশ্নটি ভয়েস মেসেজ হিসেবে পাঠান।",
    "Odia":      "ଆପଣଙ୍କ ପ୍ରଶ୍ନ ଭଏସ୍ ମେସେଜ୍ ଭାବେ ପଠାନ୍ତୁ।",
    "English":   "Send your question as a voice message.",
}

THINKING = {
    "Tamil":     "யோசிக்கிறேன்... ஒரு நிமிடம் காத்திருங்கள்.",
    "Telugu":    "ఆలోచిస్తున్నాను... ఒక్క నిమిషం వేచి ఉండండి.",
    "Kannada":   "ಯೋಚಿಸುತ್ತಿದ್ದೇನೆ... ಒಂದು ನಿಮಿಷ ಕಾಯಿರಿ.",
    "Malayalam": "ആലോചിക്കുന്നു... ഒരു നിമിഷം കാത്തിരിക്കൂ.",
    "Hindi":     "सोच रहा हूँ... एक पल रुकें।",
    "Punjabi":   "ਸੋਚ ਰਿਹਾ ਹਾਂ... ਇੱਕ ਪਲ ਉਡੀਕ ਕਰੋ।",
    "Gujarati":  "વિચારી રહ્યો છું... એક ક્ષણ રાહ જુઓ.",
    "Marathi":   "विचार करतोय... एक क्षण थांबा.",
    "Bengali":   "ভাবছি... একটু অপেক্ষা করুন।",
    "Odia":      "ଭାବୁଛି... ଏକ ମିନିଟ ଅପେକ୍ଷା କରନ୍ତୁ।",
    "English":   "Thinking... Please wait a moment.",
}

FALLBACK = {
    "Tamil":     "மன்னிக்கவும், இந்த தகவல் என்னிடம் இல்லை. உங்கள் அருகிலுள்ள KVK-ஐ தொடர்பு கொள்ளவும்.",
    "Telugu":    "క్షమించండి, ఈ సమాచారం నా దగ్గర లేదు. దయచేసి మీ దగ్గరలోని KVK ని సంప్రదించండి.",
    "Kannada":   "ಕ್ಷಮಿಸಿ, ಈ ಮಾಹಿತಿ ನನ್ನ ಬಳಿ ಇಲ್ಲ. ದಯವಿಟ್ಟು ಹತ್ತಿರದ KVK ಅನ್ನು ಸಂಪರ್ಕಿಸಿ.",
    "Malayalam": "ക്ഷമിക്കൂ, ഈ വിവരം എന്റെ കൈവശമില്ല. ദയവായി അടുത്തുള്ള KVK-നെ ബന്ധപ്പെടൂ.",
    "Hindi":     "माफ़ करें, यह जानकारी मेरे पास नहीं है। कृपया अपने नज़दीकी KVK से संपर्क करें।",
    "Punjabi":   "ਮਾਫ਼ ਕਰਨਾ, ਇਹ ਜਾਣਕਾਰੀ ਮੇਰੇ ਕੋਲ ਨਹੀਂ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੇ ਨੇੜੇ ਦੇ KVK ਨਾਲ ਸੰਪਰਕ ਕਰੋ।",
    "Gujarati":  "માફ કરશો, આ માહિતી મારી પાસે નથી. કૃપા કરી તમારા નજીકના KVK નો સંપર્ક કરો.",
    "Marathi":   "माफ करा, ही माहिती माझ्याकडे नाही. कृपया जवळच्या KVK शी संपर्क करा.",
    "Bengali":   "দুঃখিত, এই তথ্য আমার কাছে নেই। অনুগ্রহ করে আপনার নিকটস্থ KVK-তে যোগাযোগ করুন।",
    "Odia":      "କ୍ଷମା କରନ୍ତୁ, ଏହି ତଥ୍ୟ ମୋ ପାଖରେ ନାହିଁ। ଦୟାକରି ନିକଟସ୍ଥ KVK ସହ ଯୋଗାଯୋଗ କରନ୍ତୁ।",
    "English":   "Sorry, I don't have this information. Please contact your nearest KVK.",
}

ASK_NAME = {
    "Tamil":     "உங்கள் பெயரை குரல் செய்தியாக அல்லது தட்டச்சு செய்யவும்.",
    "Telugu":    "మీ పేరు వాయిస్ మెసేజ్ లేదా టైప్ చేయండి.",
    "Kannada":   "ನಿಮ್ಮ ಹೆಸರನ್ನು ವಾಯ್ಸ್ ಮೆಸೇಜ್ ಅಥವಾ ಟೈಪ್ ಮಾಡಿ ಕಳುಹಿಸಿ.",
    "Malayalam": "നിങ്ങളുടെ പേര് വോയ്സ് മെസേജായോ ടൈപ്പ് ചെയ്തോ അയക്കൂ.",
    "Hindi":     "अपना नाम वॉइस मैसेज या टाइप करके भेजें।",
    "Punjabi":   "ਆਪਣਾ ਨਾਮ ਵੌਇਸ ਮੈਸੇਜ ਜਾਂ ਟਾਈਪ ਕਰਕੇ ਭੇਜੋ।",
    "Gujarati":  "તમારું નામ વૉઇસ મેસેજ અથવા ટાઇપ કરીને મોકલો.",
    "Marathi":   "तुमचे नाव व्हॉइस मेसेज किंवा टाइप करून पाठवा.",
    "Bengali":   "আপনার নাম ভয়েস মেসেজ বা টাইপ করে পাঠান।",
    "Odia":      "ଆପଣଙ୍କ ନାମ ଭଏସ୍ ମେସେଜ୍ ବା ଟାଇପ୍ କରି ପଠାନ୍ତୁ।",
    "English":   "Please send your name as a voice message or type it.",
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

ASK_LOCATION = {
    "Tamil":     "உங்கள் இருப்பிடத்தை பகிரவும் அல்லது மாவட்டத்தை தட்டச்சு செய்யவும்.",
    "Telugu":    "మీ స్థానం షేర్ చేయండి లేదా జిల్లా పేరు టైప్ చేయండి.",
    "Kannada":   "ನಿಮ್ಮ ಸ್ಥಳ ಹಂಚಿಕೊಳ್ಳಿ ಅಥವಾ ಜಿಲ್ಲೆಯ ಹೆಸರು ಟೈಪ್ ಮಾಡಿ.",
    "Malayalam": "നിങ്ങളുടെ സ്ഥലം പങ്കിടൂ അല്ലെങ്കിൽ ജില്ല ടൈപ്പ് ചെയ്യൂ.",
    "Hindi":     "अपना स्थान शेयर करें या अपना जिला टाइप करें।",
    "Punjabi":   "ਆਪਣੀ ਸਥਿਤੀ ਸਾਂਝੀ ਕਰੋ ਜਾਂ ਆਪਣਾ ਜ਼ਿਲ੍ਹਾ ਟਾਈਪ ਕਰੋ।",
    "Gujarati":  "તમારું સ્થાન શેર કરો અથવા તમારો જિલ્લો ટાઇપ કરો.",
    "Marathi":   "तुमचे स्थान शेअर करा किंवा तुमचा जिल्हा टाइप करा.",
    "Bengali":   "আপনার অবস্থান শেয়ার করুন বা আপনার জেলা টাইপ করুন।",
    "Odia":      "ଆପଣଙ୍କ ସ୍ଥାନ ଶେୟାର କରନ୍ତୁ ବା ଜିଲ୍ଲା ଟାଇପ୍ କରନ୍ତୁ।",
    "English":   "Share your location or type your district name.",
}

ASK_TIME = {
    "Tamil":     "நீங்கள் எத்தனை மணிக்கு தினசரி செய்திகளை பெற விரும்புகிறீர்கள்? (எ.கா: 07:00)",
    "Telugu":    "మీకు ప్రతిరోజూ వ్యవసాయ వార్తలు ఎప్పుడు కావాలి? (ఉదా: 07:00)",
    "Kannada":   "ನೀವು ಪ್ರತಿದಿನ ಸುದ್ದಿ ಯಾವ ಸಮಯದಲ್ಲಿ ಬೇಕು? (ಉದಾ: 07:00)",
    "Malayalam": "ദിവസേന വാർത്ത എപ്പോൾ വേണം? (ഉദാ: 07:00)",
    "Hindi":     "आप रोज़ कितने बजे खेत समाचार पाना चाहते हैं? (जैसे: 07:00)",
    "Punjabi":   "ਤੁਸੀਂ ਰੋਜ਼ਾਨਾ ਖੇਤੀ ਖ਼ਬਰਾਂ ਕਿੰਨੇ ਵਜੇ ਚਾਹੁੰਦੇ ਹੋ? (ਜਿਵੇਂ: 07:00)",
    "Gujarati":  "તમે દરરોજ ખેતી સમાચાર કેટલા વાગ્યે ઇચ્છો છો? (જેમ કે: 07:00)",
    "Marathi":   "तुम्हाला रोज शेती बातम्या किती वाजता हव्यात? (उदा: 07:00)",
    "Bengali":   "আপনি প্রতিদিন কৃষি খবর কখন চান? (যেমন: 07:00)",
    "Odia":      "ଆପଣ ପ୍ରତିଦିନ କୃଷି ସମ୍ବାଦ କେତେ ବେଳେ ଚାହାନ୍ତି? (ଯଥା: 07:00)",
    "English":   "What time should I send you daily farm news? (e.g. 07:00 for 7 AM)",
}

CONFIRM_ONBOARD = {
    "Tamil":     "நன்று {name}! நீங்கள் தயார். ஒவ்வொரு நாளும் {time} மணிக்கு செய்திகள் வரும்.",
    "Telugu":    "బాగుంది {name}! మీరు సిద్ధంగా ఉన్నారు. రోజూ {time} కి వార్తలు వస్తాయి.",
    "Kannada":   "ಒಳ್ಳೆಯದು {name}! ನೀವು ಸಿದ್ಧರಾಗಿದ್ದೀರಿ. ಪ್ರತಿದಿನ {time} ಕ್ಕೆ ಸುದ್ದಿ ಬರುತ್ತದೆ.",
    "Malayalam": "നന്നായി {name}! നിങ്ങൾ തയ്യാർ. എല്ലാ ദിവസവും {time} ന് വാർത്ത വരും.",
    "Hindi":     "बढ़िया {name}! आप तैयार हैं। हर दिन {time} बजे समाचार आएगा।",
    "Punjabi":   "ਵਧੀਆ {name}! ਤੁਸੀਂ ਤਿਆਰ ਹੋ। ਹਰ ਰੋਜ਼ {time} ਵਜੇ ਖ਼ਬਰਾਂ ਆਉਣਗੀਆਂ।",
    "Gujarati":  "સરસ {name}! તમે તૈયાર છો. દરરોજ {time} વાગ્યે સમાચાર આવશે.",
    "Marathi":   "छान {name}! तुम्ही तयार आहात. दररोज {time} वाजता बातम्या येतील.",
    "Bengali":   "দারুণ {name}! আপনি প্রস্তুত। প্রতিদিন {time} টায় খবর আসবে।",
    "Odia":      "ବଢ଼ିଆ {name}! ଆପଣ ପ୍ରସ୍ତୁତ। ପ୍ରତିଦିନ {time} ରେ ଖବର ଆସିବ।",
    "English":   "All set, {name}! You will receive farm news daily at {time}.",
}

NO_FARMERS_NEARBY = {
    "Tamil":     "{crop} பயிரிடும் விவசாயிகள் இன்னும் Agrithm-ல் இல்லை.",
    "Telugu":    "{crop} వేసే రైతులు ఇంకా Agrithm లో లేరు.",
    "Kannada":   "{crop} ಬೆಳೆಯುವ ರೈತರು ಇನ್ನೂ Agrithm ನಲ್ಲಿ ಇಲ್ಲ.",
    "Malayalam": "{crop} കൃഷി ചെയ്യുന്ന കർഷകർ ഇതുവരെ Agrithm-ൽ ഇല്ല.",
    "Hindi":     "{crop} उगाने वाले किसान अभी Agrithm पर नहीं हैं।",
    "Punjabi":   "{crop} ਉਗਾਉਣ ਵਾਲੇ ਕਿਸਾਨ ਅਜੇ Agrithm 'ਤੇ ਨਹੀਂ ਹਨ।",
    "Gujarati":  "{crop} ઉગાડનારા ખેડૂતો હજુ Agrithm પર નથી.",
    "Marathi":   "{crop} पिकवणारे शेतकरी अजून Agrithm वर नाहीत.",
    "Bengali":   "{crop} চাষীরা এখনও Agrithm-এ নেই।",
    "Odia":      "{crop} ଚାଷ କରୁଥିବା କୃଷକ ଏପର୍ଯ୍ୟନ୍ତ Agrithm ରେ ନାହାନ୍ତି।",
    "English":   "No {crop} farmers have joined Agrithm yet in your area.",
}


# ── Helper functions ──────────────────────────────────────────────

def get_msg(msg_dict: dict, language: str) -> str:
    """Get message in user's language, fallback to English."""
    return msg_dict.get(language, msg_dict["English"])

def get_confirm_onboard(language: str, name: str, time: str) -> str:
    """Get formatted onboarding confirmation message."""
    template = get_msg(CONFIRM_ONBOARD, language)
    return template.format(name=name, time=time)

def get_no_farmers_msg(language: str, crop: str) -> str:
    """Get 'no farmers nearby' message with crop filled in."""
    template = get_msg(NO_FARMERS_NEARBY, language)
    return template.format(crop=crop)