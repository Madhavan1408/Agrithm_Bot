"""
utils/mandi_db.py
─────────────────────────────────────────────────────────────────────
Unified APMC Mandi Price Database — Andhra Pradesh + Karnataka.

FIXES:
  - "Dry Chilli" added as its own canonical commodity (KA DB has it separately)
  - COMMODITY_ALIASES: "dry chilli" now maps to "Dry Chilli" (not Red Chilli)
  - AP_DISTRICT_ALIASES expanded for all new AP districts
  - get_commodities() and get_districts() return combined AP+KA when no state given
  - _query_one_state: uses LIKE with both exact and partial match
"""

import os
import sqlite3
import logging
from collections import defaultdict
from typing import Optional

log = logging.getLogger(__name__)

_ROOT      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AP_DB_PATH = os.path.join(_ROOT, "ap_mandi_prices.db")
KA_DB_PATH = os.path.join(_ROOT, "ka_mandi_prices.db")

MANDI_DB_AVAILABLE: bool = os.path.exists(AP_DB_PATH) or os.path.exists(KA_DB_PATH)

if not MANDI_DB_AVAILABLE:
    log.warning(
        "[mandi_db] Neither ap_mandi_prices.db nor ka_mandi_prices.db found "
        "in project root (%s). Mandi DB queries disabled.", _ROOT,
    )


# ═══════════════════════════════════════════════════════════════════
# COMMODITY ALIASES
# ═══════════════════════════════════════════════════════════════════

COMMODITY_ALIASES: dict[str, str] = {
    # ── Red / Dry Chilli — FIX: Dry Chilli is now its own entry ──
    "red chilli":       "Red Chilli",
    "red chili":        "Red Chilli",
    "lal mirch":        "Red Chilli",
    "endu mirapa":      "Red Chilli",
    "vara milagai":     "Red Chilli",
    "mirchi":           "Red Chilli",
    "mirch":            "Red Chilli",

    # FIX: dry chilli → Dry Chilli (separate from Red Chilli in KA DB)
    "dry chilli":       "Dry Chilli",
    "dry chili":        "Dry Chilli",
    "ona menasu":       "Dry Chilli",

    # Generic "chilli" → try Red Chilli first
    "chilli":           "Red Chilli",
    "chili":            "Red Chilli",

    # ── Green Chilli ──────────────────────────────────────────────
    "green chilli":     "Green Chilli",
    "green chili":      "Green Chilli",
    "hari mirch":       "Green Chilli",
    "pachchi mirapa":   "Green Chilli",
    "hasiru menasu":    "Green Chilli",
    "pachai milagai":   "Green Chilli",

    # ── Paddy ─────────────────────────────────────────────────────
    "paddy":            "Paddy (Common)",
    "rice":             "Paddy (Common)",
    "paddy common":     "Paddy (Common)",
    "common paddy":     "Paddy (Common)",
    "dhan":             "Paddy (Common)",
    "vandlu":           "Paddy (Common)",
    "bhatta":           "Paddy (Common)",
    "nel":              "Paddy (Common)",
    "paddy fine":       "Paddy (Fine)",
    "fine paddy":       "Paddy (Fine)",
    "basmati":          "Paddy (Fine)",

    # ── Maize ─────────────────────────────────────────────────────
    "maize":            "Maize",
    "corn":             "Maize",
    "makka":            "Maize",
    "mekke jola":       "Maize",
    "cholam":           "Maize",

    # ── Groundnut ─────────────────────────────────────────────────
    "groundnut":        "Groundnut",
    "peanut":           "Groundnut",
    "moongphali":       "Groundnut",
    "pallilu":          "Groundnut",
    "palli":            "Groundnut",
    "kadalekai":        "Groundnut",
    "verkadalai":       "Groundnut",

    # ── Sunflower ─────────────────────────────────────────────────
    "sunflower":        "Sunflower",
    "surajmukhi":       "Sunflower",
    "puvvulu":          "Sunflower",
    "suryakanti":       "Sunflower",

    # ── Cotton ────────────────────────────────────────────────────
    "cotton":           "Cotton",
    "kapas":            "Cotton",
    "patti":            "Cotton",
    "hatti":            "Cotton",
    "paruthi":          "Cotton",

    # ── Turmeric ──────────────────────────────────────────────────
    "turmeric":         "Turmeric",
    "haldi":            "Turmeric",
    "pasupu":           "Turmeric",
    "arishina":         "Turmeric",
    "manjal":           "Turmeric",

    # ── Onion ─────────────────────────────────────────────────────
    "onion":            "Onion",
    "pyaz":             "Onion",
    "ullipaya":         "Onion",
    "eerulli":          "Onion",
    "vengayam":         "Onion",

    # ── Tomato ────────────────────────────────────────────────────
    "tomato":           "Tomato",
    "tamatar":          "Tomato",
    "thakkali":         "Tomato",

    # ── Potato ────────────────────────────────────────────────────
    "potato":           "Potato",
    "aloo":             "Potato",
    "urlagadda":        "Potato",
    "aalugadde":        "Potato",
    "urulaikizhangu":   "Potato",

    # ── Bengalgram ────────────────────────────────────────────────
    "bengalgram":       "Bengalgram",
    "chana":            "Bengalgram",
    "gram":             "Bengalgram",
    "chickpea":         "Bengalgram",
    "sanagalu":         "Bengalgram",
    "kadale":           "Bengalgram",
    "kadalai":          "Bengalgram",

    # ── Blackgram ─────────────────────────────────────────────────
    "blackgram":        "Blackgram",
    "black gram":       "Blackgram",
    "urad":             "Blackgram",
    "urad dal":         "Blackgram",
    "minumulu":         "Blackgram",
    "uddina bele":      "Blackgram",
    "ulundu":           "Blackgram",

    # ── Greengram ─────────────────────────────────────────────────
    "greengram":        "Greengram",
    "green gram":       "Greengram",
    "moong":            "Greengram",
    "moong dal":        "Greengram",
    "pesalu":           "Greengram",
    "hesaru bele":      "Greengram",
    "paasipayaru":      "Greengram",

    # ── Jowar ─────────────────────────────────────────────────────
    "jowar":            "Jowar",
    "sorghum":          "Jowar",
    "jonna":            "Jowar",
    "jwari":            "Jowar",

    # ── Bajra ─────────────────────────────────────────────────────
    "bajra":            "Bajra",
    "pearl millet":     "Bajra",
    "sajja":            "Bajra",
    "sajje":            "Bajra",
    "kambu":            "Bajra",

    # ── Ragi ──────────────────────────────────────────────────────
    "ragi":             "Ragi",
    "finger millet":    "Ragi",
    "ragulu":           "Ragi",
    "kelvaragu":        "Ragi",

    # ── Sugarcane ─────────────────────────────────────────────────
    "sugarcane":        "Sugarcane",
    "ganna":            "Sugarcane",
    "cheruku":          "Sugarcane",
    "kabbu":            "Sugarcane",
    "karumbu":          "Sugarcane",

    # ── Coconut ───────────────────────────────────────────────────
    "coconut":          "Coconut",
    "kobbari":          "Coconut",
    "nariyal":          "Coconut",
    "tengu":            "Coconut",
    "thengai":          "Coconut",

    # ── Banana ────────────────────────────────────────────────────
    "banana":           "Banana",
    "kela":             "Banana",
    "arati":            "Banana",
    "bale":             "Banana",
    "plantain":         "Banana",
    "vazhai":           "Banana",

    # ── Mango ─────────────────────────────────────────────────────
    "mango":            "Mango",
    "aam":              "Mango",
    "mamidi":           "Mango",
    "mavina":           "Mango",
    "manga":            "Mango",

    # ── Tamarind ──────────────────────────────────────────────────
    "tamarind":         "Tamarind",
    "imli":             "Tamarind",
    "chintapandu":      "Tamarind",
    "hunase":           "Tamarind",
    "puli":             "Tamarind",

    # ── Sesame ────────────────────────────────────────────────────
    "sesame":           "Sesame",
    "til":              "Sesame",
    "nuvvulu":          "Sesame",
    "ellu":             "Sesame",
    "gingelly":         "Sesame",

    # ── Castor ────────────────────────────────────────────────────
    "castor":           "Castor",
    "arand":            "Castor",
    "amudam":           "Castor",
    "haralu":           "Castor",
    "amanakku":         "Castor",

    # ── Soybean ───────────────────────────────────────────────────
    "soybean":          "Soybean",
    "soya":             "Soybean",
    "soya bean":        "Soybean",

    # ── Coriander ─────────────────────────────────────────────────
    "coriander":        "Coriander",
    "dhania":           "Coriander",
    "kothimeera":       "Coriander",
    "kottambari":       "Coriander",
    "kothamalli":       "Coriander",

    # ── Garlic ────────────────────────────────────────────────────
    "garlic":           "Garlic",
    "lahsun":           "Garlic",
    "vellulli":         "Garlic",
    "bellulli":         "Garlic",
    "poondu":           "Garlic",

    # ── Ginger ────────────────────────────────────────────────────
    "ginger":           "Ginger",
    "adrak":            "Ginger",
    "allam":            "Ginger",
    "shunti":           "Ginger",
    "inji":             "Ginger",

    # ── Arecanut ──────────────────────────────────────────────────
    "arecanut":         "Arecanut",
    "betelnut":         "Arecanut",
    "supari":           "Arecanut",
    "adike":            "Arecanut",
    "pakku":            "Arecanut",

    # ── Coffee ────────────────────────────────────────────────────
    "coffee":           "Coffee (Arabica)",
    "arabica":          "Coffee (Arabica)",

    # ── Tur Dal ───────────────────────────────────────────────────
    "tur dal":          "Tur Dal",
    "toor dal":         "Tur Dal",
    "arhar":            "Tur Dal",
    "kandi":            "Tur Dal",
    "togari":           "Tur Dal",
    "tuvaram":          "Tur Dal",
}


# ═══════════════════════════════════════════════════════════════════
# DISTRICT ALIASES — FIX: Added all new AP districts
# ═══════════════════════════════════════════════════════════════════

AP_DISTRICT_ALIASES: dict[str, str] = {
    "visakhapatnam": "Visakhapatnam",   "vizag": "Visakhapatnam",
    "waltair": "Visakhapatnam",
    "vizianagaram": "Vizianagaram",     "vizi": "Vizianagaram",
    "srikakulam": "Srikakulam",
    "east godavari": "East Godavari",   "east god": "East Godavari",
    "kakinada": "Kakinada",
    "west godavari": "West Godavari",   "west god": "West Godavari",
    "eluru": "Eluru",
    "krishna": "Krishna",               "vijayawada": "Krishna",
    "ntr district": "NTR District",     "ntr": "NTR District",
    "guntur": "Guntur",
    "bapatla": "Bapatla",               "chirala": "Bapatla",
    "prakasam": "Prakasam",             "ongole": "Prakasam",
    "nellore": "Nellore",               "sps nellore": "SPS Nellore",
    "kurnool": "Kurnool",               "nandyal": "Kurnool",
    "anantapur": "Anantapur",           "anantapuramu": "Anantapur",
    "kadapa": "Kadapa",                 "cuddapah": "Kadapa",
    "chittoor": "Chittoor",
    "tirupati": "Tirupati",             "tirupati": "Tirupati",
    "palnadu": "Palnadu",               "narasaraopet": "Palnadu",
    "alluri": "Alluri Sitharama Raju",  "paderu": "Alluri Sitharama Raju",
    "alluri sitharama raju": "Alluri Sitharama Raju",
    "anakapalli": "Anakapalli",
    "konaseema": "Konaseema",           "amalapuram": "Konaseema",
    # FIX: added missing
    "bhimavaram": "West Godavari",
    "rajahmundry": "East Godavari",
    "machilipatnam": "Krishna",
    "proddatur": "Kadapa",
    "madanapalle": "Chittoor",
}

KA_DISTRICT_ALIASES: dict[str, str] = {
    "bengaluru": "Bengaluru Urban",     "bangalore": "Bengaluru Urban",
    "bengaluru urban": "Bengaluru Urban",
    "bangalore urban": "Bengaluru Urban",
    "bengaluru rural": "Bengaluru Rural",
    "bangalore rural": "Bengaluru Rural",
    "mysuru": "Mysuru",                 "mysore": "Mysuru",
    "mandya": "Mandya",
    "hassan": "Hassan",
    "tumakuru": "Tumakuru",             "tumkur": "Tumakuru",
    "kolar": "Kolar",
    "chikkaballapura": "Chikkaballapura",
    "chikballapur": "Chikkaballapura",
    "raichur": "Raichur",
    "ballari": "Ballari",               "bellary": "Ballari",
    "koppal": "Koppal",
    "gadag": "Gadag",
    "dharwad": "Dharwad",               "hubli": "Dharwad",
    "belagavi": "Belagavi",             "belgaum": "Belagavi",
    "vijayapura": "Vijayapura",         "bijapur": "Vijayapura",
    "bagalkot": "Bagalkot",
    "haveri": "Haveri",
    "uttara kannada": "Uttara Kannada", "karwar": "Uttara Kannada",
    "dakshina kannada": "Dakshina Kannada",
    "mangaluru": "Dakshina Kannada",    "mangalore": "Dakshina Kannada",
    "udupi": "Udupi",
    "shivamogga": "Shivamogga",         "shimoga": "Shivamogga",
    "chikkamagaluru": "Chikkamagaluru", "chikmagalur": "Chikkamagaluru",
    "kodagu": "Kodagu",                 "coorg": "Kodagu",
    "yadgir": "Yadgir",
    "kalaburagi": "Kalaburagi",         "gulbarga": "Kalaburagi",
    "bidar": "Bidar",
    "chitradurga": "Chitradurga",
    "davanagere": "Davanagere",         "davangere": "Davanagere",
    "chamarajanagara": "Chamarajanagara",
    "chamarajanagar": "Chamarajanagara",
    "ramanagara": "Ramanagara",
    "vijayanagara": "Vijayanagara",
}

_STATE_NAME_ALIASES: dict[str, str] = {
    "andhra pradesh": "AP",   "andhra": "AP",
    "ap": "AP",               "telugu state": "AP",
    "karnataka": "KA",        "karnataka state": "KA",
    "ka": "KA",               "kannada state": "KA",
}

_DISTRICT_MAP: dict[str, tuple[str, str]] = {}
for _a, _n in AP_DISTRICT_ALIASES.items():
    _DISTRICT_MAP[_a] = (_n, "AP")
for _a, _n in KA_DISTRICT_ALIASES.items():
    _DISTRICT_MAP[_a] = (_n, "KA")


# ═══════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════

def _get_conn(state: str) -> Optional[sqlite3.Connection]:
    path = AP_DB_PATH if state == "AP" else KA_DB_PATH
    if not os.path.exists(path):
        log.debug("[mandi_db] %s not found — skipping %s queries", path, state)
        return None
    try:
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as exc:
        log.warning("[mandi_db] Cannot open %s: %s", path, exc)
        return None


def _resolve_commodity(raw: str) -> Optional[str]:
    n = raw.lower().strip()
    if n in COMMODITY_ALIASES:
        return COMMODITY_ALIASES[n]
    # Partial match — longer aliases checked first
    for alias in sorted(COMMODITY_ALIASES, key=len, reverse=True):
        if alias in n or n in alias:
            return COMMODITY_ALIASES[alias]
    return None


def _resolve_district(raw: str) -> tuple[Optional[str], Optional[str]]:
    n = raw.lower().strip()
    if n in _DISTRICT_MAP:
        return _DISTRICT_MAP[n]
    for alias, (name, state) in _DISTRICT_MAP.items():
        if alias in n or n in alias:
            return name, state
    return None, None


def _resolve_state(raw: str) -> Optional[str]:
    n = raw.lower().strip()
    return _STATE_NAME_ALIASES.get(n)


def _query_one_state(
    state: str,
    canonical_commodity: str,
    canonical_district: Optional[str],
    latest_only: bool,
) -> list[dict]:
    conn = _get_conn(state)
    if conn is None:
        return []
    try:
        cur = conn.cursor()
        latest_date: Optional[str] = None
        if latest_only:
            if canonical_district:
                cur.execute(
                    """SELECT MAX(Date) FROM mandi_prices
                       WHERE Commodity LIKE ? AND District LIKE ?""",
                    (f"%{canonical_commodity}%", f"%{canonical_district}%"),
                )
            else:
                cur.execute(
                    "SELECT MAX(Date) FROM mandi_prices WHERE Commodity LIKE ?",
                    (f"%{canonical_commodity}%",),
                )
            row = cur.fetchone()
            latest_date = row[0] if row and row[0] else None

        params: list = [f"%{canonical_commodity}%"]
        sql = (
            'SELECT Date, District, "Market HQ", "APMC / Mandi", Commodity, '
            '"Min Price (₹/Qtl)", "Max Price (₹/Qtl)", "Average Price (₹/Qtl)" '
            "FROM mandi_prices WHERE Commodity LIKE ?"
        )
        if canonical_district:
            sql += " AND District LIKE ?"
            params.append(f"%{canonical_district}%")
        if latest_date:
            sql += " AND Date = ?"
            params.append(latest_date)
        sql += ' ORDER BY "Average Price (₹/Qtl)" DESC'

        cur.execute(sql, params)
        return [
            {
                "date":      r[0],
                "district":  r[1],
                "market_hq": r[2],
                "mandi":     r[3],
                "commodity": r[4],
                "min_price": round(float(r[5] or 0), 2),
                "max_price": round(float(r[6] or 0), 2),
                "avg_price": round(float(r[7] or 0), 2),
                "state":     state,
            }
            for r in cur.fetchall()
        ]
    except sqlite3.Error as exc:
        log.warning("[mandi_db] SQLite error (%s): %s", state, exc)
        return []
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════

def extract_location_from_query(text: str) -> tuple[Optional[str], Optional[str]]:
    lower = text.lower()
    for alias, (name, state) in _DISTRICT_MAP.items():
        if alias in lower:
            return name, state
    for alias, state_code in _STATE_NAME_ALIASES.items():
        if alias in lower:
            return None, state_code
    return None, None


def detect_state(district: str) -> Optional[str]:
    if not district:
        return None
    _, state = _resolve_district(district)
    return state


def query_mandi_db(
    commodity:    str,
    district:     Optional[str] = None,
    state:        Optional[str] = None,
    latest_only:  bool = True,
) -> list[dict]:
    if not MANDI_DB_AVAILABLE:
        return []

    canonical_commodity = _resolve_commodity(commodity) or commodity.strip().title()

    canonical_district: Optional[str] = None
    resolved_state = state

    if district:
        c_dist, d_state = _resolve_district(district)
        canonical_district = c_dist or district
        if not resolved_state:
            resolved_state = d_state

    if not resolved_state:
        results: list[dict] = []
        for s in ("AP", "KA"):
            results.extend(_query_one_state(s, canonical_commodity, canonical_district, latest_only))
        return sorted(results, key=lambda r: -r["avg_price"])

    rows = _query_one_state(resolved_state, canonical_commodity, canonical_district, latest_only)
    log.info("[mandi_db] %s | crop=%s district=%s → %d rows",
             resolved_state, canonical_commodity, canonical_district, len(rows))
    return rows


def get_commodities(state: str = None) -> list[str]:
    if not MANDI_DB_AVAILABLE:
        return []
    states = [state] if state else ["AP", "KA"]
    result = set()
    for s in states:
        conn = _get_conn(s)
        if conn is None:
            continue
        try:
            rows = conn.execute("SELECT DISTINCT Commodity FROM mandi_prices ORDER BY Commodity").fetchall()
            result.update(r[0] for r in rows)
        except Exception as exc:
            log.error("[mandi_db] get_commodities(%s): %s", s, exc)
        finally:
            conn.close()
    return sorted(result)


def get_districts(state: str = None) -> list[str]:
    if not MANDI_DB_AVAILABLE:
        return []
    states = [state] if state else ["AP", "KA"]
    result = set()
    for s in states:
        conn = _get_conn(s)
        if conn is None:
            continue
        try:
            rows = conn.execute("SELECT DISTINCT District FROM mandi_prices ORDER BY District").fetchall()
            result.update(r[0] for r in rows)
        except Exception as exc:
            log.error("[mandi_db] get_districts(%s): %s", s, exc)
        finally:
            conn.close()
    return sorted(result)


def format_mandi_db_text(
    rows:      list[dict],
    commodity: str,
    district:  Optional[str] = None,
    state:     Optional[str] = None,
) -> str:
    if not rows:
        scope = (
            f"in {district}" if district else
            "in Andhra Pradesh" if state == "AP" else
            "in Karnataka"      if state == "KA" else
            "in AP / Karnataka"
        )
        return (
            f"❌ No mandi data found for *{commodity.title()}* {scope}.\n\n"
            "Try: Paddy, Groundnut, Red Chilli, Dry Chilli, Turmeric, Cotton, "
            "Onion, Tomato, Maize, Sunflower, Ragi, Soybean, Coriander, Garlic, "
            "Arecanut, Tur Dal, Bengalgram, Jowar, Sugarcane, Potato, Ginger, "
            "Banana, Mango, Sesame, Castor, Blackgram, Greengram, Bajra, Tamarind"
        )

    date        = rows[0]["date"]
    canonical_c = rows[0]["commodity"]
    row_state   = state or rows[0].get("state")
    state_label = (
        "Andhra Pradesh" if row_state == "AP" else
        "Karnataka"      if row_state == "KA" else
        "AP + Karnataka"
    )

    if not district:
        grouped: dict[str, list[float]] = defaultdict(list)
        for r in rows:
            grouped[r["district"]].append(r["avg_price"])

        lines = [
            f"🌾 *{canonical_c}* — Mandi Prices",
            f"📍 *{state_label}*  ·  {date}",
            f"📊 {len(grouped)} districts  |  {len(rows)} mandis\n",
        ]
        for dist, prices in sorted(grouped.items(), key=lambda x: -(sum(x[1]) / len(x[1])))[:15]:
            avg = sum(prices) / len(prices)
            lines.append(f"• *{dist}* — ₹{avg:,.0f}/Qtl")

        all_avg = [r["avg_price"] for r in rows]
        lines += [
            "",
            f"📊 *State Avg:* ₹{sum(all_avg)/len(all_avg):,.0f}/Qtl",
            f"📉 *Min:* ₹{min(r['min_price'] for r in rows):,.0f}  "
            f"📈 *Max:* ₹{max(r['max_price'] for r in rows):,.0f}",
            "_Unit: ₹/Quintal · Source: APMC_",
        ]
    else:
        lines = [
            f"🌾 *{canonical_c}* — Mandi Prices",
            f"📍 *{district}*, {state_label}  ·  {date}\n",
        ]
        for r in rows[:20]:
            mandi = r["mandi"].replace(" APMC", "").replace(" New", "").replace(" Central", "").strip()
            lines.append(
                f"🏪 *{mandi}*\n"
                f"   ₹{r['min_price']:,.0f} – ₹{r['max_price']:,.0f}  "
                f"(Avg ₹{r['avg_price']:,.0f})/Qtl"
            )
        avgs = [r["avg_price"] for r in rows]
        lines += [
            "",
            f"📊 *Dist Avg:* ₹{sum(avgs)/len(avgs):,.0f}/Qtl",
            f"📉 *Min:* ₹{min(r['min_price'] for r in rows):,.0f}  "
            f"📈 *Max:* ₹{max(r['max_price'] for r in rows):,.0f}",
            "_Unit: ₹/Quintal · Source: APMC_",
        ]

    return "\n".join(lines)
