"""
utils/mandi.py
──────────────
Fetches crop mandi (market) prices from data.gov.in API.

FIXES:
  - format_mandi_text() uses ₹ symbol instead of "Rs."
  - fetch_mandi_prices() state param passed from caller (not always Tamil Nadu)
  - Better visual formatting for Telegram (cleaner spacing)
"""

from __future__ import annotations

import logging
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# PRICE FETCHING
# ═══════════════════════════════════════════════════════════════════

def fetch_mandi_prices(
    commodity: str,
    district:  str = "",
    state:     str = "Tamil Nadu",
    limit:     int = 5,
) -> list[dict]:
    """
    Fetch mandi prices from data.gov.in.

    Strategy:
      1. Try district-level filter (most relevant for the farmer).
      2. If zero results, retry without district (state-wide).
    Returns a list of price dicts (may be empty on API failure).
    """
    commodity = commodity.strip().title()

    def _call(params: dict) -> list[dict]:
        try:
            resp = requests.get(MANDI_API_URL, params=params, timeout=10)
            resp.raise_for_status()
            records = resp.json().get("records", [])
            log.info("[mandi] %d records | commodity=%s params=%s",
                     len(records), commodity, params)
            return [
                {
                    "market":   r.get("market",       "Unknown Market"),
                    "district": r.get("district",     ""),
                    "state":    r.get("state",         ""),
                    "variety":  r.get("variety",      "General"),
                    "min":      r.get("min_price",    "N/A"),
                    "max":      r.get("max_price",    "N/A"),
                    "modal":    r.get("modal_price",  "N/A"),
                    "date":     r.get("arrival_date", "N/A"),
                }
                for r in records
            ]
        except requests.exceptions.Timeout:
            log.error("[mandi] timeout | commodity=%s", commodity)
            return []
        except requests.exceptions.RequestException as exc:
            log.error("[mandi] request failed: %s", exc)
            return []
        except Exception as exc:
            log.error("[mandi] unexpected error: %s", exc)
            return []

    base_params = {
        "api-key":            MANDI_API_KEY,
        "format":             "json",
        "limit":              limit,
        "filters[commodity]": commodity,
        "filters[state]":     state,
    }

    # Pass 1 — with district filter
    clean_district = (district or "").strip()
    if clean_district and not clean_district.startswith("Lat:"):
        params_with_district = {**base_params, "filters[district]": clean_district}
        results = _call(params_with_district)
        if results:
            return results
        log.info("[mandi] no district results, retrying state-wide")

    # Pass 2 — state-wide fallback
    return _call(base_params)


# ═══════════════════════════════════════════════════════════════════
# TEXT FORMATTING — FIXED: ₹ symbol, cleaner layout
# ═══════════════════════════════════════════════════════════════════

def format_mandi_text(prices: list[dict], commodity: str, district: str = "") -> str:
    """Format price list into a Telegram-ready Markdown message."""
    commodity = commodity.strip().title()

    if not prices:
        location = (
            f" in {district}"
            if district and not district.startswith("Lat:") else ""
        )
        return (
            f"❌ No mandi prices found for *{commodity}*{location}.\n"
            "Try a different crop name or check back later."
        )

    location = (
        f" in {district}"
        if district and not district.startswith("Lat:") else ""
    )
    lines = [f"💰 *Mandi Prices — {commodity}*{location}\n"]

    for i, p in enumerate(prices):
        market_line = f"🏪 *{p['market']}*"
        if p["district"]:
            market_line += f" _{p['district']}_"
        lines.append(
            f"{market_line}\n"
            f"  Variety  : {p['variety']}\n"
            f"  Min ↓    : ₹{p['min']}/quintal\n"
            f"  Max ↑    : ₹{p['max']}/quintal\n"
            f"  Modal ◉  : ₹{p['modal']}/quintal\n"
            f"  Date     : {p['date']}\n"
        )
        if i < len(prices) - 1:
            lines.append("─" * 20)

    lines.append("\n_Source: data.gov.in (Agmarknet)_")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
# ASYNC HANDLER  (called directly from bot.py)
# ═══════════════════════════════════════════════════════════════════

async def handle_mandi_query(
    update,
    context,
    profile:   dict,
    lang:      str,
    lang_cfg:  dict,
    *,
    download_voice_fn,
    safe_transcribe_fn,
    translate_to_english_fn,
    extract_crop_fn,
    translate_from_english_fn,
    speak_fn,
    main_menu_keyboard_fn,
    STATE_MANDI_CROP: int,
    STATE_MAIN_MENU:  int,
) -> int:
    """
    Full mandi flow:
      voice/text → crop name (STT + extraction) → fetch prices
      → translate result → text reply + TTS voice reply.
    """
    from telegram.constants import ParseMode

    user_id  = update.effective_user.id
    district = (profile.get("district") or "").strip()
    state    = (profile.get("state") or "Tamil Nadu").strip()

    raw = ""
    if update.message.voice:
        path = await download_voice_fn(update, context)
        if path:
            import os as _os
            raw, _ = safe_transcribe_fn(path, lang_cfg["code"])
            try:
                _os.remove(path)
            except OSError:
                pass
    else:
        raw = (update.message.text or "").strip()

    crop = (
        extract_crop_fn(raw)
        or translate_to_english_fn(raw, lang_cfg["code"]).lower().strip()
    )

    if not crop:
        await update.message.reply_text(
            "Please type the crop name.",
            reply_markup=main_menu_keyboard_fn(user_id),
        )
        return STATE_MANDI_CROP

    await update.message.reply_text(
        f"🔍 Fetching mandi prices for *{crop.title()}*...",
    )
    # FIX: pass state from profile instead of hardcoded Tamil Nadu
    prices = fetch_mandi_prices(crop, district, state=state)
    msg_en = format_mandi_text(prices, crop, district)

    await update.message.reply_text(
        msg_en,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_keyboard_fn(user_id),
    )

    try:
        plain = msg_en.replace("*", "").replace("_", "").replace("₹", "Rs.")
        local_text = (
            translate_from_english_fn(plain, lang_cfg["code"])
            if lang != "English"
            else plain
        )
        await speak_fn(update, local_text, lang, "Mandi prices")
    except Exception as exc:
        log.warning("[mandi TTS] %s", exc)

    return STATE_MAIN_MENU
