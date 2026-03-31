"""
utils/mandi.py
──────────────
Fetches crop mandi (market) prices from data.gov.in API.
"""

import os
import sys
import logging
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agrithm_config import MANDI_API_URL, MANDI_API_KEY

log = logging.getLogger(__name__)


def fetch_mandi_prices(commodity: str, district: str = "", state: str = "Tamil Nadu", limit: int = 5) -> list:
    """Fetch current mandi prices for a crop from data.gov.in."""
    params = {
        "api-key":            MANDI_API_KEY,
        "format":             "json",
        "limit":              limit,
        "filters[commodity]": commodity.strip().title(),
    }
    if state:
        params["filters[state]"] = state
    if district and not district.startswith("Lat:"):
        params["filters[district]"] = district

    try:
        resp = requests.get(MANDI_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        records = resp.json().get("records", [])
        log.info("Mandi API: %d records for '%s'", len(records), commodity)
        return [
            {
                "market":   r.get("market",       "Unknown Market"),
                "district": r.get("district",     ""),
                "variety":  r.get("variety",      "General"),
                "min":      r.get("min_price",    "N/A"),
                "max":      r.get("max_price",    "N/A"),
                "modal":    r.get("modal_price",  "N/A"),
                "date":     r.get("arrival_date", "N/A"),
            }
            for r in records
        ]
    except requests.exceptions.Timeout:
        log.error("Mandi API timed out for '%s'", commodity)
        return []
    except requests.exceptions.RequestException as e:
        log.error("Mandi API request failed: %s", e)
        return []
    except Exception as e:
        log.error("Unexpected mandi error: %s", e)
        return []


def format_mandi_text(prices: list, commodity: str, district: str = "") -> str:
    """Format mandi price list into a readable Telegram message."""
    if not prices:
        location = f" in {district}" if district and not district.startswith("Lat:") else ""
        return (
            f"❌ No mandi prices found for *{commodity.title()}*{location}.\n"
            "Try a different crop name or check back later."
        )

    location = f" in {district}" if district and not district.startswith("Lat:") else ""
    lines = [f"💰 *Mandi Prices — {commodity.title()}*{location}\n"]

    for p in prices:
        lines.append(
            f"📍 *{p['market']}* ({p['district']})\n"
            f"   Variety : {p['variety']}\n"
            f"   Min     : ₹{p['min']} / quintal\n"
            f"   Max     : ₹{p['max']} / quintal\n"
            f"   Modal   : ₹{p['modal']} / quintal\n"
            f"   Date    : {p['date']}\n"
        )

    lines.append("_Source: data.gov.in (Agmarknet)_")
    return "\n".join(lines)