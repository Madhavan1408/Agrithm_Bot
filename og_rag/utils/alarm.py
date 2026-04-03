"""
utils/alarm.py
──────────────
Alarm storage and natural-language time parser for Agrithm.

FIXES vs v1:
  FIX M3: Added "fired" timestamp guard so the alarm cannot fire
          twice in the same minute even if APScheduler runs the job
          multiple times (e.g. after a misfire recovery).
  FIX H5: Absolute path for alarms.json — works regardless of cwd.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import logging
from datetime import datetime
from typing import Optional

import pytz

log = logging.getLogger(__name__)

# FIX H5: Absolute path — project root is one level above utils/
_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALARMS_PATH = os.path.join(_ROOT, "data", "alarms.json")
os.makedirs(os.path.join(_ROOT, "data"), exist_ok=True)

# ── Day aliases ───────────────────────────────────────────────────────
_DAY_ALIASES: dict[str, str] = {
    # English
    "monday": "mon", "tuesday": "tue", "wednesday": "wed",
    "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
    "mon": "mon", "tue": "tue", "wed": "wed", "thu": "thu",
    "fri": "fri", "sat": "sat", "sun": "sun",
    "weekday": "weekday", "weekend": "weekend", "everyday": "daily",
    "daily": "daily", "every day": "daily",
    # Hindi transliterations
    "somvar": "mon", "mangalvar": "tue", "budhvar": "wed",
    "guruvar": "thu", "shukravar": "fri", "shanivar": "sat", "ravivar": "sun",
    "roz": "daily", "har din": "daily",
    # Telugu transliterations
    "somavaram": "mon", "mangalavaram": "tue", "budhavaram": "wed",
    "guruvaram": "thu", "shukravaram": "fri", "shanivaram": "sat", "adivaram": "sun",
    "pratirojoo": "daily",
    # Tamil transliterations
    "thingal": "mon", "sevvai": "tue", "budhan": "wed",
    "vyazhan": "thu", "velli": "fri", "sani": "sat", "nyayiru": "sun",
    "thinanum": "daily",
}

# ── AM/PM & period keywords ───────────────────────────────────────────
_MORNING_WORDS   = {"morning", "am", "subah", "காலை", "ఉదయం", "ಬೆಳಿಗ್ಗೆ", "രാവിലെ"}
_EVENING_WORDS   = {"evening", "pm", "sham", "மாலை", "సాయంత్రం", "ಸಂಜೆ", "വൈകുന്നേരം"}
_NIGHT_WORDS     = {"night", "raat", "இரவு", "రాత్రి", "ರಾತ್ರಿ", "രാത്രി"}
_AFTERNOON_WORDS = {"afternoon", "dopahar", "மதியம்", "మధ్యాహ్నం", "ಮಧ್ಯಾಹ್ನ", "ഉച്ചക്ക്"}

# ── Number words → digits ─────────────────────────────────────────────
_NUM_WORDS: dict[str, int] = {
    "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,
    "six":6,"seven":7,"eight":8,"nine":9,"ten":10,
    "eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,
    "sixteen":16,"seventeen":17,"eighteen":18,"nineteen":19,"twenty":20,
    "thirty":30,"forty":40,"fifty":50,
    # Hindi
    "ek":1,"do":2,"teen":3,"char":4,"paanch":5,
    "chhe":6,"saat":7,"aath":8,"nau":9,"das":10,
}


# ═══════════════════════════════════════════════════════════════════════
# TIME PARSER
# ═══════════════════════════════════════════════════════════════════════

def parse_alarm_time(text: str) -> Optional[tuple[int, int]]:
    """
    Extract (hour, minute) in 24-h from a natural-language string.
    Returns None if no time found.
    """
    t = text.lower().strip()

    if "noon" in t:
        return (12, 0)
    if "midnight" in t:
        return (0, 0)

    is_morning   = any(w in t for w in _MORNING_WORDS)
    is_evening   = any(w in t for w in _EVENING_WORDS)
    is_night     = any(w in t for w in _NIGHT_WORDS)
    is_afternoon = any(w in t for w in _AFTERNOON_WORDS)

    hour:   Optional[int] = None
    minute: Optional[int] = None

    # Pattern 1: HH:MM or HH.MM (with optional am/pm)
    m = re.search(r'\b(\d{1,2})[:\.](\d{2})\s*(am|pm)?\b', t)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        ampm = m.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
    else:
        # Pattern 2: 4-digit compact "0630" or "630"
        m2 = re.search(r'\b(\d{3,4})\b', t)
        if m2:
            raw = m2.group(1).zfill(4)
            h, mn = int(raw[:2]), int(raw[2:])
            if 0 <= h <= 23 and 0 <= mn <= 59:
                hour, minute = h, mn

        # Pattern 3: bare hour "at 6", "baje 7"
        if hour is None:
            m3 = re.search(
                r'(?:at|@|baje|बजे|గంటలకు|மணிக்கு|ಗಂಟೆಗೆ|മണിക്ക്)?\s*(\d{1,2})', t
            )
            if m3:
                hour = int(m3.group(1))

        # Pattern 4: number words
        if hour is None:
            for word, val in sorted(_NUM_WORDS.items(), key=lambda x: -len(x[0])):
                if re.search(rf'\b{re.escape(word)}\b', t):
                    hour = val
                    break

        # Try to find minute word ("thirty", "fifteen" …)
        if hour is not None and minute is None:
            for word, val in _NUM_WORDS.items():
                if val < 60 and re.search(rf'\b{re.escape(word)}\b', t):
                    if val != hour:
                        minute = val
                        break

        minute = minute or 0

    if hour is None:
        return None

    # Apply period hints to resolve ambiguous 12-h hours
    if 1 <= hour <= 6:
        if is_evening or is_night or is_afternoon:
            hour += 12
    elif 7 <= hour <= 11:
        if is_evening or is_night:
            hour += 12
    elif hour == 12:
        if is_morning:
            hour = 0

    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None

    return (hour, minute)


def parse_alarm_days(text: str) -> list[str]:
    """Extract day list from text. Returns ["daily"] if no specific days found."""
    t = text.lower()
    found: list[str] = []

    for alias, canonical in _DAY_ALIASES.items():
        if alias in t:
            if canonical == "weekday":
                return ["mon", "tue", "wed", "thu", "fri"]
            if canonical == "weekend":
                return ["sat", "sun"]
            if canonical == "daily":
                return ["daily"]
            if canonical not in found:
                found.append(canonical)

    return found if found else ["daily"]


def parse_alarm_label(text: str) -> str:
    """Strip time/day/trigger words and return remaining text as label."""
    stop = {
        "set", "alarm", "reminder", "remind", "alert", "wake", "me",
        "at", "on", "for", "every", "please", "baje", "subah", "sham",
        "raat", "kal", "aaj", "tomorrow", "today", "morning", "evening",
        "night", "am", "pm", "noon", "midnight", "daily", "roz",
    }
    words = [
        w for w in text.lower().split()
        if w not in stop and not re.match(r'[\d:.]+', w)
    ]
    label = " ".join(words).strip().title()
    return label or "Alarm"


# ═══════════════════════════════════════════════════════════════════════
# STORAGE HELPERS
# ═══════════════════════════════════════════════════════════════════════

def _load_all() -> dict:
    if not os.path.exists(ALARMS_PATH):
        return {}
    try:
        with open(ALARMS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data: dict) -> None:
    with open(ALARMS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_alarms(user_id: int) -> list[dict]:
    return _load_all().get(str(user_id), [])


def add_alarm(
    user_id:  int,
    hour:     int,
    minute:   int,
    label:    str,
    days:     list[str],
    timezone: str,
) -> dict:
    data     = _load_all()
    key      = str(user_id)
    alarms   = data.get(key, [])
    alarm_id = secrets.token_hex(3)          # e.g. "a1b2c3"
    alarm    = {
        "id":         alarm_id,
        "label":      label,
        "time":       f"{hour:02d}:{minute:02d}",
        "days":       days,
        "timezone":   timezone,
        "active":     True,
        "last_fired": None,   # FIX M3: tracks last fire timestamp
    }
    alarms.append(alarm)
    data[key] = alarms
    _save_all(data)
    return alarm


def delete_alarm(user_id: int, alarm_id: str) -> bool:
    data   = _load_all()
    key    = str(user_id)
    before = data.get(key, [])
    after  = [a for a in before if a["id"] != alarm_id]
    if len(after) == len(before):
        return False
    data[key] = after
    _save_all(data)
    return True


def toggle_alarm(user_id: int, alarm_id: str) -> Optional[bool]:
    """Returns new active state, or None if not found."""
    data = _load_all()
    key  = str(user_id)
    for alarm in data.get(key, []):
        if alarm["id"] == alarm_id:
            alarm["active"] = not alarm["active"]
            _save_all(data)
            return alarm["active"]
    return None


def get_all_active_alarms() -> list[tuple[int, dict]]:
    """Returns [(user_id, alarm_dict), ...] for all active alarms."""
    data   = _load_all()
    result = []
    for uid_str, alarms in data.items():
        for alarm in alarms:
            if alarm.get("active"):
                result.append((int(uid_str), alarm))
    return result


def mark_alarm_fired(user_id: int, alarm_id: str) -> None:
    """FIX M3: Record last-fired timestamp to prevent double-fire."""
    data = _load_all()
    key  = str(user_id)
    for alarm in data.get(key, []):
        if alarm["id"] == alarm_id:
            alarm["last_fired"] = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
            _save_all(data)
            return


# ═══════════════════════════════════════════════════════════════════════
# FIRE CHECK
# ═══════════════════════════════════════════════════════════════════════

_DAY_MAP = {0: "mon", 1: "tue", 2: "wed", 3: "thu", 4: "fri", 5: "sat", 6: "sun"}


def should_fire_now(alarm: dict) -> bool:
    """
    Returns True if this alarm should fire at the current minute
    in the alarm's own timezone.

    FIX M3: Checks last_fired to prevent double-firing within the same
    minute (e.g. if APScheduler runs the job twice after a misfire).
    """
    try:
        tz  = pytz.timezone(alarm.get("timezone", "Asia/Kolkata"))
        now = datetime.now(tz)
        h, m = map(int, alarm["time"].split(":"))

        if now.hour != h or now.minute != m:
            return False

        # FIX M3: already fired this minute?
        last_fired = alarm.get("last_fired")
        if last_fired:
            try:
                fired_dt = datetime.strptime(last_fired, "%Y-%m-%dT%H:%M")
                fired_utc = datetime.utcnow().replace(second=0, microsecond=0)
                if fired_dt == fired_utc.replace(
                    hour=fired_dt.hour, minute=fired_dt.minute
                ):
                    # Same UTC minute — don't fire again
                    current_utc_minute = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
                    if last_fired == current_utc_minute:
                        return False
            except Exception:
                pass

        days = alarm.get("days", ["daily"])
        if "daily" in days:
            return True
        today = _DAY_MAP[now.weekday()]
        return today in days

    except Exception as exc:
        log.warning("[alarm] should_fire_now error: %s", exc)
        return False


def fmt_days(days: list[str]) -> str:
    if "daily" in days:
        return "Every day"
    return ", ".join(d.capitalize() for d in days)