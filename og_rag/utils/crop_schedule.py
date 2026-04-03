"""
utils/crop_schedule.py
──────────────────────
Builds the daily crop card sent to the farmer every morning.

The card is generated from:
  1. Static stage data from crop_journey.py (tasks, dos, donts, fertilizer, monitor)
  2. An LLM-generated "tip of the day" that adds context about current weather/season
  3. A visual text progress bar

The card is formatted in Telegram Markdown and also returned as plain
text for TTS (Sarvam) — the TTS version strips emojis and Markdown.
"""

from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Optional

from utils.crop_journey import (
    CROP_LIFECYCLES,
    fertilizer_due_today,
    get_current_day,
    get_stage_for_day,
    journey_summary_text,
)

log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════
# PROGRESS BAR
# ══════════════════════════════════════════════════════════════════

def _progress_bar(current: int, total: int, width: int = 12) -> str:
    filled = int(current * width / total)
    bar    = "█" * filled + "░" * (width - filled)
    pct    = int(current * 100 / total)
    return f"[{bar}] {pct}%"


def _stage_timeline(crop_key: str, current_day: int) -> str:
    """Text timeline showing all stages with current one marked."""
    lifecycle = CROP_LIFECYCLES.get(crop_key, {})
    stages    = lifecycle.get("stages", [])
    total     = lifecycle.get("total_days", 1)
    lines     = []
    for s in stages:
        is_current = s["start"] <= current_day < s["end"]
        marker = "▶" if is_current else ("✓" if current_day >= s["end"] else "○")
        days_range = f"Day {s['start']+1}–{s['end']}"
        lines.append(f"  {marker} {s['emoji']} {s['name']} ({days_range})")
    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════
# MAIN CARD BUILDER
# ══════════════════════════════════════════════════════════════════

def build_daily_card(
    journey: dict,
    farmer_name: str,
    ollama_tip: Optional[str] = None,
) -> tuple[str, str]:
    """
    Build the daily crop card.

    Returns:
      (markdown_text, tts_text)
    """
    crop_key = journey["crop_key"]
    day      = get_current_day(journey)
    stage    = get_stage_for_day(crop_key, day)
    total    = journey["total_days"]
    crop     = journey["crop_name"]

    if not stage:
        # Past harvest date
        md = (
            f"🎉 *Congratulations, {farmer_name}!*\n\n"
            f"Your *{crop}* journey is complete (Day {day} of {total}).\n\n"
            f"We hope you had a great harvest! 🌾\n\n"
            f"Start a new journey anytime by typing:\n"
            f"_\"Start {crop} journey\"_"
        )
        tts = f"Congratulations {farmer_name}! Your {crop} journey is complete. We hope you had a great harvest."
        return md, tts

    stage_name = stage["name"]
    emoji      = stage["emoji"]
    prog_bar   = _progress_bar(day, total)
    is_critical = stage.get("critical", False)
    critical_banner = "\n⚠️ *CRITICAL STAGE — pay extra attention today!*\n" if is_critical else ""

    # Tasks
    tasks_text = ""
    for i, task in enumerate(stage.get("key_tasks", [])[:3], 1):
        tasks_text += f"  {i}. {task}\n"

    # Do's
    dos_text = ""
    for d in stage.get("dos", [])[:3]:
        dos_text += f"  ✅ {d}\n"

    # Don'ts
    donts_text = ""
    for d in stage.get("donts", [])[:3]:
        donts_text += f"  ❌ {d}\n"

    # Fertilizer
    fert = fertilizer_due_today(crop_key, day)
    fert_text = ""
    if fert:
        fert_text = (
            f"\n💊 *FERTILIZER DUE TODAY*\n"
            f"  Product : {fert['product']}\n"
            f"  Dose    : {fert['dose']}\n"
            f"  Method  : {fert['method']}\n"
            f"  Cost    : {fert['cost']}\n"
        )

    # Monitor
    monitor_text = ""
    for m in stage.get("monitor", [])[:3]:
        monitor_text += f"  👁 {m}\n"

    # Harvest countdown
    harvest_date  = date.fromisoformat(journey["harvest_date"])
    days_to_harvest = (harvest_date - date.today()).days
    harvest_line  = ""
    if days_to_harvest > 0:
        harvest_line = f"\n🗓 *Estimated harvest in {days_to_harvest} days* ({harvest_date.strftime('%d %b %Y')})"
    elif days_to_harvest == 0:
        harvest_line = "\n🎉 *Harvest day is today!*"

    # Timeline
    timeline = _stage_timeline(crop_key, day)

    # AI tip
    tip_section = ""
    if ollama_tip and ollama_tip.strip():
        tip_section = f"\n🌱 *Today's tip from Agrithm:*\n_{ollama_tip.strip()}_\n"

    # ── Full Markdown card ────────────────────────────────────────
    md = (
        f"🌾 *Daily Crop Card — {crop}*\n"
        f"👋 Good morning, *{farmer_name}*!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"\n"
        f"📅 *Day {day} of {total}*\n"
        f"{prog_bar}\n"
        f"\n"
        f"{emoji} *Stage: {stage_name}*"
        f"{critical_banner}\n"
        f"  You are on day {stage['day_in_stage']} of {stage['stage_total_days']} in this stage.\n"
        f"\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 *Today's Tasks*\n"
        f"{tasks_text}\n"
        f"✅ *Do This*\n"
        f"{dos_text}\n"
        f"❌ *Don't Do This*\n"
        f"{donts_text}"
        f"{fert_text}\n"
        f"👁 *Monitor Today*\n"
        f"{monitor_text}"
        f"{tip_section}"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🗺 *Crop Timeline*\n"
        f"{timeline}\n"
        f"{harvest_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Reply 'crop status' to see this again anytime._"
    )

    # ── Plain text for TTS (strip markdown and emojis) ────────────
    plain = re.sub(r'[*_`]', '', md)
    plain = re.sub(r'[🌾👋━📅█░🌱✅❌💊👁🗓🎉📋🗺▶✓○⚠️]', '', plain)
    plain = re.sub(r'\n{3,}', '\n\n', plain).strip()

    # For TTS just give the concise summary
    task_list = "; ".join([t.split("—")[0].strip() for t in stage.get("key_tasks", [])[:2]])
    fert_tts  = f"Fertilizer due today: {fert['product']}, {fert['dose']}. " if fert else ""
    tts_text  = (
        f"Good morning {farmer_name}. "
        f"This is your {crop} crop daily card. "
        f"Today is day {day} of {total}. "
        f"You are in the {stage_name} stage. "
        f"Tasks for today: {task_list}. "
        f"{fert_tts}"
        f"Days to harvest: {days_to_harvest}."
    )

    return md, tts_text


# ══════════════════════════════════════════════════════════════════
# LLM PROMPT BUILDER FOR DAILY TIP
# ══════════════════════════════════════════════════════════════════

def build_daily_tip_prompt(journey: dict, profile: dict) -> str:
    """
    Builds the LLM prompt for generating the personalized AI tip
    that goes in the daily card.
    """
    crop_key  = journey["crop_key"]
    day       = get_current_day(journey)
    stage     = get_stage_for_day(crop_key, day)
    name      = profile.get("name", "Farmer")
    district  = profile.get("district", "India")
    village   = profile.get("village", "")

    if not stage:
        return (
            f"The farmer {name} in {village}, {district} has just completed harvesting their "
            f"{journey['crop_name']} crop. Give ONE encouraging sentence and ONE tip for next season."
        )

    stage_name = stage["name"]
    fert       = fertilizer_due_today(crop_key, day)
    fert_note  = f"Fertilizer is due today: {fert['product']} ({fert['dose']})." if fert else ""

    return (
        f"Farmer {name} in {village}, {district} is growing {journey['crop_name']}. "
        f"Today is day {day} — {stage_name} stage. "
        f"{fert_note} "
        f"Give ONE practical tip (2–3 sentences) specific to this stage and location. "
        f"Be direct and actionable. Plain sentences only. No bullet points."
    )


# ══════════════════════════════════════════════════════════════════
# JOURNEY START MESSAGE
# ══════════════════════════════════════════════════════════════════

def build_journey_start_message(
    journey: dict,
    farmer_name: str,
) -> str:
    """
    Message sent when farmer confirms a new crop journey.
    """
    crop      = journey["crop_name"]
    sow_date  = date.fromisoformat(journey["sow_date"])
    har_date  = date.fromisoformat(journey["harvest_date"])
    total     = journey["total_days"]
    crop_key  = journey["crop_key"]

    lifecycle = CROP_LIFECYCLES.get(crop_key, {})
    stages    = lifecycle.get("stages", [])

    stage_lines = ""
    for s in stages:
        days_range   = f"Day {s['start']+1}–{s['end']}"
        stage_lines += f"  {s['emoji']} {s['name']} ({days_range})\n"

    alarm_time = journey.get("alarm_time", "06:00")

    return (
        f"🌱 *{crop} Journey Started!*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Hello {farmer_name}!\n\n"
        f"Your crop monitoring journey has begun. Every morning at *{alarm_time}*, "
        f"you will receive a *Daily Crop Card* with:\n"
        f"  📋 Today's tasks\n"
        f"  ✅ Do's and don'ts\n"
        f"  💊 Fertilizer reminders\n"
        f"  👁 What to monitor\n"
        f"  🌱 AI-powered field tip\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 *Sow date:*     {sow_date.strftime('%d %b %Y')}\n"
        f"🎉 *Est. harvest:* {har_date.strftime('%d %b %Y')}\n"
        f"⏱ *Duration:*     {total} days\n\n"
        f"🗺 *Growth stages:*\n"
        f"{stage_lines}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Type 'crop status' anytime to see today's card._\n"
        f"_Type 'end journey' to stop monitoring._"
    )