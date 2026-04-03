#!/usr/bin/env python3
"""
apply_lang_patch.py
═══════════════════
Run once from your bot root directory:

    python apply_lang_patch.py

Creates bot.py.bak_lang before modifying.
Applies three changes:
  1. Adds get_lang_system_instruction to ui imports
  2. Replaces build_farmer_context() to inject language directive
  3. Replaces ring texts in alarm/journey fire functions
  4. Patches FARMING_SYSTEM_PROMPT to accept {lang_instruction}
"""

import re
import shutil
import sys
from pathlib import Path

BOT = Path("bot.py")
if not BOT.exists():
    print("ERROR: bot.py not found. Run from bot root directory.")
    sys.exit(1)

shutil.copy(BOT, "bot.py.bak_lang")
print("✅ Backup: bot.py.bak_lang")

src = BOT.read_text(encoding="utf-8")
changes = 0

# ──────────────────────────────────────────────────────────────────
# PATCH 1 — add get_lang_system_instruction to ui import
# ──────────────────────────────────────────────────────────────────
if "get_lang_system_instruction" not in src:
    src = src.replace(
        "    get_msg, fmt,",
        "    get_msg, fmt, get_lang_system_instruction,",
        1,
    )
    changes += 1
    print("✅ PATCH 1: Added get_lang_system_instruction import")
else:
    print("⏭  PATCH 1: Already imported")


# ──────────────────────────────────────────────────────────────────
# PATCH 2 — patch FARMING_SYSTEM_PROMPT to carry {lang_instruction}
# ──────────────────────────────────────────────────────────────────
OLD_IDENTITY = "IDENTITY\nYou are AGRITHM"
NEW_IDENTITY = "{lang_instruction}\nIDENTITY\nYou are AGRITHM"

if "{lang_instruction}" not in src and OLD_IDENTITY in src:
    src = src.replace(OLD_IDENTITY, NEW_IDENTITY, 1)
    changes += 1
    print("✅ PATCH 2: Injected {lang_instruction} into FARMING_SYSTEM_PROMPT")
else:
    print("⏭  PATCH 2: lang_instruction already in prompt or anchor not found")


# ──────────────────────────────────────────────────────────────────
# PATCH 3 — replace build_farmer_context() body to inject lang
# ──────────────────────────────────────────────────────────────────
OLD_CTX = '''\
def build_farmer_context(profile: dict) -> str:
    name     = profile.get("name", "Farmer")
    crop     = profile.get("crop", "mixed crops")
    village  = profile.get("village", "")
    district = profile.get("district", "")
    lang     = profile.get("language", "English")

    location_parts = []
    if village and village.lower() not in ("unknown", ""):
        location_parts.append(village)
    if district and district.lower() not in ("unknown", ""):
        location_parts.append(district)
    location_parts.append("India")
    location = ", ".join(location_parts)

    native_lang = LANGUAGES.get(lang, {}).get("native", lang)

    return (
        "=== FARMER PROFILE ===\\n"
        f"Name: {name}\\n"
        f"Crop: {crop}\\n"
        f"Location: {location}\\n"
        f"Language: {native_lang}\\n"
        "=== END PROFILE ===\\n\\n"
    )'''

NEW_CTX = '''\
def build_farmer_context(profile: dict) -> str:
    """Builds farmer context block; injects language directive for Ollama."""
    name     = profile.get("name", "Farmer")
    crop     = profile.get("crop", "mixed crops")
    village  = profile.get("village", "")
    district = profile.get("district", "")
    lang     = profile.get("language", "English")

    location_parts = []
    if village and village.lower() not in ("unknown", ""):
        location_parts.append(village)
    if district and district.lower() not in ("unknown", ""):
        location_parts.append(district)
    location_parts.append("India")
    location = ", ".join(location_parts)

    native_lang = LANGUAGES.get(lang, {}).get("native", lang)
    lang_instr  = get_lang_system_instruction(lang)

    return (
        f"{lang_instr}"
        "=== FARMER PROFILE ===\\n"
        f"Name: {name}\\n"
        f"Crop: {crop}\\n"
        f"Location: {location}\\n"
        f"Language: {native_lang}\\n"
        "=== END PROFILE ===\\n\\n"
    )'''

if "lang_instr  = get_lang_system_instruction" not in src and OLD_CTX in src:
    src = src.replace(OLD_CTX, NEW_CTX, 1)
    changes += 1
    print("✅ PATCH 3: Updated build_farmer_context() with language injection")
else:
    print("⏭  PATCH 3: Already patched or anchor not found — patching by line search")
    # Fallback: find the return block and inject lang_instr
    if 'lang_instr  = get_lang_system_instruction' not in src:
        src = src.replace(
            '    native_lang = LANGUAGES.get(lang, {}).get("native", lang)\n\n    return (',
            '    native_lang = LANGUAGES.get(lang, {}).get("native", lang)\n'
            '    lang_instr  = get_lang_system_instruction(lang)\n\n    return (\n'
            '        f"{lang_instr}"',
            1,
        )
        # Remove the duplicate opening paren from original return
        src = src.replace(
            '    lang_instr  = get_lang_system_instruction(lang)\n\n    return (\n'
            '        f"{lang_instr}"\n'
            '        "=== FARMER PROFILE ===\\n"\n'
            '        f"Name: {name}\\n"\n'
            '        f"Crop: {crop}\\n"\n'
            '        f"Location: {location}\\n"\n'
            '        f"Language: {native_lang}\\n"\n'
            '        "=== END PROFILE ===\\n\\n"\n'
            '    )\n'
            '    return (',
            '    lang_instr  = get_lang_system_instruction(lang)\n\n    return (\n'
            '        f"{lang_instr}"\n'
            '        "=== FARMER PROFILE ===\\n"\n'
            '        f"Name: {name}\\n"\n'
            '        f"Crop: {crop}\\n"\n'
            '        f"Location: {location}\\n"\n'
            '        f"Language: {native_lang}\\n"\n'
            '        "=== END PROFILE ===\\n\\n"\n'
            '    )\n',
            1,
        )
        changes += 1
        print("✅ PATCH 3 (fallback): Injected lang_instr via line search")


# ──────────────────────────────────────────────────────────────────
# PATCH 4 — patch query_ollama_async to format {lang_instruction}
# The system prompt template now has {lang_instruction} but the
# context is already passed via build_farmer_context(), so we just
# ensure the system prompt doesn't fail with a KeyError.
# ──────────────────────────────────────────────────────────────────
OLD_OLLAMA_CALL = '''\
            body: JSON.stringify({
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},'''

# This is Python, not JS — find the actual call
OLD_MESSAGES = (
    '                    {"role": "system", "content": system},\n'
    '                    {"role": "user",   "content": prompt},\n'
)
NEW_MESSAGES = (
    '                    {"role": "system", "content": system.format(lang_instruction="")},\n'
    '                    {"role": "user",   "content": prompt},\n'
)

if OLD_MESSAGES in src and 'format(lang_instruction' not in src:
    src = src.replace(OLD_MESSAGES, NEW_MESSAGES, 1)
    # Also patch vision call
    OLD_VIS = (
        '                    {"role": "system", "content": system},\n'
        '                    {"role": "user",   "content": prompt, "images": [image_b64]},\n'
    )
    NEW_VIS = (
        '                    {"role": "system", "content": system.format(lang_instruction="")},\n'
        '                    {"role": "user",   "content": prompt, "images": [image_b64]},\n'
    )
    src = src.replace(OLD_VIS, NEW_VIS, 1)
    changes += 1
    print("✅ PATCH 4: Added .format(lang_instruction='') to Ollama system calls")
else:
    print("⏭  PATCH 4: Already patched or anchor not found")


# ──────────────────────────────────────────────────────────────────
# PATCH 5 — localise alarm ring text
# ──────────────────────────────────────────────────────────────────
OLD_RING = '''\
    ring_text = (
        f"🔔🔔🔔 *ALARM — {label}* 🔔🔔🔔\\n\\n"
        f"⏰ It is *{time_str}*\\n"
        f"👋 Good morning, *{name}*!\\n\\n"
        f"🌾 Your daily farming tip is coming..."
    )'''

NEW_RING = '''\
    _alarm_ring_templates = {
        "English":   f"🔔🔔🔔 *ALARM — {label}* 🔔🔔🔔\\n\\n⏰ It is *{time_str}*\\n👋 Good morning, *{name}*!\\n\\n🌾 Your daily farming tip is coming...",
        "Hindi":     f"🔔🔔🔔 *अलार्म — {label}* 🔔🔔🔔\\n\\n⏰ अभी *{time_str}* बजे हैं\\n👋 सुप्रभात, *{name}*!\\n\\n🌾 आपकी दैनिक खेती टिप आ रही है...",
        "Telugu":    f"🔔🔔🔔 *అలారం — {label}* 🔔🔔🔔\\n\\n⏰ ఇప్పుడు *{time_str}* అయింది\\n👋 శుభోదయం, *{name}*!\\n\\n🌾 మీ రోజువారీ చిట్కా వస్తోంది...",
        "Tamil":     f"🔔🔔🔔 *அலாரம் — {label}* 🔔🔔🔔\\n\\n⏰ இப்போது *{time_str}* மணி\\n👋 காலை வணக்கம், *{name}*!\\n\\n🌾 உங்கள் தினசரி குறிப்பு வருகிறது...",
        "Kannada":   f"🔔🔔🔔 *ಅಲಾರಂ — {label}* 🔔🔔🔔\\n\\n⏰ ಈಗ *{time_str}* ಆಗಿದೆ\\n👋 ಶುಭೋದಯ, *{name}*!\\n\\n🌾 ನಿಮ್ಮ ಕೃಷಿ ಸಲಹೆ ಬರುತ್ತಿದೆ...",
        "Malayalam": f"🔔🔔🔔 *അലാറം — {label}* 🔔🔔🔔\\n\\n⏰ ഇപ്പോൾ *{time_str}* ആയി\\n👋 സുപ്രഭാതം, *{name}*!\\n\\n🌾 നിങ്ങളുടെ കൃഷി ടിപ്പ് വരുന്നു...",
        "Marathi":   f"🔔🔔🔔 *अलार्म — {label}* 🔔🔔🔔\\n\\n⏰ आता *{time_str}* वाजले\\n👋 सुप्रभात, *{name}*!\\n\\n🌾 तुमची शेती टिप येत आहे...",
        "Gujarati":  f"🔔🔔🔔 *એલાર્મ — {label}* 🔔🔔🔔\\n\\n⏰ હવે *{time_str}* વાગ્યા\\n👋 સુપ્રભાત, *{name}*!\\n\\n🌾 તમારી ખેતી ટીપ આવી રહી છે...",
    }
    ring_text = _alarm_ring_templates.get(lang) or _alarm_ring_templates["English"]'''

if OLD_RING in src:
    src = src.replace(OLD_RING, NEW_RING, 1)
    changes += 1
    print("✅ PATCH 5: Localised alarm ring text")
else:
    print("⏭  PATCH 5: Alarm ring anchor not found (may differ slightly)")


# ──────────────────────────────────────────────────────────────────
# PATCH 6 — localise journey card ring message
# ──────────────────────────────────────────────────────────────────
OLD_JOURNEY_RING = '''\
        ring_msg   = (
            f"🌾 *Good morning, {name}!*\\n"
            f"🔔 Your *{crop}* Daily Crop Card is ready.\\n"
            f"📅 Day {day} of {total} — {stage_name}"
        )'''

NEW_JOURNEY_RING = '''\
        _jring = {
            "English":   f"🌾 *Good morning, {name}!*\\n🔔 Your *{crop}* Daily Crop Card is ready.\\n📅 Day {day} of {total} — {stage_name}",
            "Hindi":     f"🌾 *सुप्रभात, {name}!*\\n🔔 आपका *{crop}* डेली क्रॉप कार्ड तैयार है।\\n📅 दिन {day} / {total} — {stage_name}",
            "Telugu":    f"🌾 *శుభోదయం, {name}!*\\n🔔 మీ *{crop}* డైలీ క్రాప్ కార్డ్ సిద్ధం.\\n📅 రోజు {day} / {total} — {stage_name}",
            "Tamil":     f"🌾 *காலை வணக்கம், {name}!*\\n🔔 உங்கள் *{crop}* தினசரி பயிர் அட்டை தயார்.\\n📅 நாள் {day} / {total} — {stage_name}",
            "Kannada":   f"🌾 *ಶುಭೋದಯ, {name}!*\\n🔔 ನಿಮ್ಮ *{crop}* ದೈನಂದಿನ ಬೆಳೆ ಕಾರ್ಡ್ ಸಿದ್ಧ.\\n📅 ದಿನ {day} / {total} — {stage_name}",
            "Malayalam": f"🌾 *സുപ്രഭാതം, {name}!*\\n🔔 നിങ്ങളുടെ *{crop}* ഡെയ്‌ലി ക്രോപ്പ് കാർഡ് തയ്യാർ.\\n📅 ദിനം {day} / {total} — {stage_name}",
            "Marathi":   f"🌾 *सुप्रभात, {name}!*\\n🔔 तुमचे *{crop}* डेली क्रॉप कार्ड तयार आहे.\\n📅 दिवस {day} / {total} — {stage_name}",
            "Gujarati":  f"🌾 *સુપ્રભાત, {name}!*\\n🔔 તમારું *{crop}* ડેઈલી ક્રોપ કાર્ડ તૈયાર છે.\\n📅 દિવસ {day} / {total} — {stage_name}",
        }
        ring_msg = _jring.get(lang) or _jring["English"]'''

if OLD_JOURNEY_RING in src:
    src = src.replace(OLD_JOURNEY_RING, NEW_JOURNEY_RING, 1)
    changes += 1
    print("✅ PATCH 6: Localised journey card ring message")
else:
    print("⏭  PATCH 6: Journey ring anchor not found (may differ slightly)")


# ──────────────────────────────────────────────────────────────────
# WRITE
# ──────────────────────────────────────────────────────────────────
if changes:
    BOT.write_text(src, encoding="utf-8")
    print(f"\n🎉 Done! Applied {changes} patch(es) to bot.py")
else:
    print("\n⚠️  No changes written.")

print("\nDeploy steps:")
print("  1. cp ui.py   D:\\agribot\\rag\\utils\\ui.py")
print("  2. python apply_lang_patch.py   (from D:\\agribot\\rag\\)")
print("  3. python bot.py")