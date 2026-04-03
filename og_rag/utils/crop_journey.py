"""
utils/crop_journey.py
─────────────────────
Crop Journey feature for Agrithm.

Stores a farmer's active crop journey (sow date → harvest date) and
provides the stage engine that maps Day-N to a named growth stage with
all metadata needed to generate the daily card.

Supports: Rice/Paddy, Wheat, Cotton, Tomato, Onion, Groundnut,
          Maize, Sugarcane, Soybean, Chilli — easily extensible.

All durations are in days from sowing.
"""

from __future__ import annotations

import json
import os
import logging
from datetime import date, datetime, timedelta
from typing import Optional

log = logging.getLogger(__name__)

_ROOT         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JOURNEY_PATH  = os.path.join(_ROOT, "data", "crop_journeys.json")
os.makedirs(os.path.join(_ROOT, "data"), exist_ok=True)


# ══════════════════════════════════════════════════════════════════
# CROP LIFECYCLE DATABASE
# Each crop → list of stages: {name, start_day, end_day, emoji,
#   key_tasks, dos, donts, fertilizer, monitor, critical}
# ══════════════════════════════════════════════════════════════════

CROP_LIFECYCLES: dict[str, dict] = {

    "rice": {
        "total_days": 120,
        "aliases": ["paddy", "paddi", "rice", "chawal", "vari", "arisi", "bhata"],
        "stages": [
            {
                "name": "Nursery / Seed preparation",
                "start": 0, "end": 25, "emoji": "🌱",
                "key_tasks": [
                    "Soak seeds for 24 hours, then wrap in wet cloth for 2 days for germination",
                    "Prepare nursery bed — plough, level, apply 5 kg/m² FYM",
                    "Sow pre-germinated seeds uniformly at 25–30 g/m²",
                ],
                "dos": [
                    "Maintain thin water layer (2–3 cm) in nursery",
                    "Apply 25 kg urea per hectare on day 10 in nursery",
                    "Check for damping-off disease — remove infected seedlings immediately",
                ],
                "donts": [
                    "Do NOT let nursery dry out — seedlings die within hours",
                    "Do NOT apply excess nitrogen — causes weak, spindly seedlings",
                    "Do NOT transplant before seedlings reach 20–25 cm height",
                ],
                "fertilizer": {
                    "day_range": [10, 10],
                    "product": "Urea",
                    "dose": "25 kg/hectare in nursery bed",
                    "method": "Broadcast and mix into top 2 cm",
                    "cost": "₹600–₹800",
                },
                "monitor": [
                    "Seedling height — should reach 20 cm by day 20",
                    "Leaf colour — pale yellow means nitrogen deficiency",
                    "Damping-off (rotting at base) — spray Carbendazim 1g/L if seen",
                ],
                "critical": False,
            },
            {
                "name": "Transplanting",
                "start": 25, "end": 30, "emoji": "🌾",
                "key_tasks": [
                    "Transplant seedlings 2–3 per hill, at 20×20 cm spacing",
                    "Apply basal dose: 50 kg DAP + 50 kg MOP per hectare before transplanting",
                    "Maintain 5 cm standing water after transplanting",
                ],
                "dos": [
                    "Transplant in the evening to reduce heat stress",
                    "Keep seedling roots moist during transport from nursery",
                    "Mark rows with rope for uniform spacing",
                ],
                "donts": [
                    "Do NOT transplant very deep — keep crown just below surface",
                    "Do NOT let field dry for 7 days after transplanting",
                    "Do NOT delay transplanting beyond 30 days — seedling quality drops",
                ],
                "fertilizer": {
                    "day_range": [25, 25],
                    "product": "DAP + MOP (basal)",
                    "dose": "50 kg DAP + 50 kg MOP per hectare",
                    "method": "Broadcast and plough in before transplanting",
                    "cost": "₹3,000–₹4,000",
                },
                "monitor": [
                    "Seedling establishment — 90%+ should stand upright in 5 days",
                    "Check for Golden Gall Midge entry — look for silver shoots",
                    "Water level — maintain 5 cm throughout",
                ],
                "critical": True,
            },
            {
                "name": "Tillering",
                "start": 30, "end": 60, "emoji": "🌿",
                "key_tasks": [
                    "Apply first split dose of urea: 50 kg/hectare at day 30",
                    "Weed the field — pull by hand or use cono-weeder between rows",
                    "Check water level — reduce to 3 cm to encourage tillering",
                ],
                "dos": [
                    "Apply urea exactly at 30 days — timing is critical for tiller count",
                    "Allow field to dry for 1–2 days around day 45 (mid-season drainage)",
                    "Spray BHC or Monocrotophos if stem borer damage seen",
                ],
                "donts": [
                    "Do NOT let weeds grow — they compete heavily at this stage",
                    "Do NOT keep field flooded continuously — causes poor tillering",
                    "Do NOT apply excess nitrogen after day 50",
                ],
                "fertilizer": {
                    "day_range": [30, 30],
                    "product": "Urea (1st split)",
                    "dose": "50 kg/hectare",
                    "method": "Broadcast in standing water",
                    "cost": "₹1,200–₹1,500",
                },
                "monitor": [
                    "Tiller count per hill — target 8–12 tillers by day 50",
                    "Stem borer (dead heart) — pull central shoot, if it comes out = borer",
                    "Brown plant hopper (BPH) — check base of plant near waterline",
                    "Water level — adjust based on weather",
                ],
                "critical": False,
            },
            {
                "name": "Panicle initiation",
                "start": 60, "end": 80, "emoji": "🌾",
                "key_tasks": [
                    "Apply second urea split: 50 kg/hectare at panicle initiation",
                    "Spray Propiconazole 25EC to prevent Sheath Blight",
                    "Ensure field has 5 cm water — critical for panicle development",
                ],
                "dos": [
                    "Apply potassium (MOP) if not given earlier — 25 kg/hectare",
                    "Monitor for neck blast — spray Tricyclazole if weather is humid",
                    "Maintain water — water stress at this stage = sterile grains",
                ],
                "donts": [
                    "Do NOT allow water stress — even 1–2 dry days reduces yield by 20%",
                    "Do NOT apply urea after this stage — causes lodging and late maturity",
                    "Do NOT spray insecticides during flowering — kills pollinators",
                ],
                "fertilizer": {
                    "day_range": [60, 62],
                    "product": "Urea (2nd split) + MOP",
                    "dose": "50 kg Urea + 25 kg MOP per hectare",
                    "method": "Broadcast in standing water",
                    "cost": "₹2,000–₹2,500",
                },
                "monitor": [
                    "Neck blast — brown lesions at junction of panicle and stem",
                    "Sheath blight — white patches on leaf sheath at waterline",
                    "Water availability — check daily, critical stage",
                ],
                "critical": True,
            },
            {
                "name": "Flowering / Pollination",
                "start": 80, "end": 95, "emoji": "🌸",
                "key_tasks": [
                    "Maintain 5 cm water — water stress means empty (chaff) grains",
                    "Avoid any spraying during peak flowering hours (8 AM–12 PM)",
                    "Spray micronutrient mix (ZnSO₄) if leaves show yellowing",
                ],
                "dos": [
                    "Monitor daily for any disease spread",
                    "Apply potassium foliar spray if grain fill is poor",
                ],
                "donts": [
                    "Do NOT apply any insecticide or fungicide during 8 AM–12 PM",
                    "Do NOT let field dry — even 1 day of stress causes sterility",
                    "Do NOT disturb crop — no movement through field during flowering",
                ],
                "fertilizer": None,
                "monitor": [
                    "Grain filling — squeeze a grain, should feel milky",
                    "Neck blast at panicle base — spray Tricyclazole if seen",
                    "Sheath rot (red-brown lesions on upper sheath)",
                ],
                "critical": True,
            },
            {
                "name": "Grain filling / Ripening",
                "start": 95, "end": 115, "emoji": "🌾",
                "key_tasks": [
                    "Drain field 10 days before harvest (day 105)",
                    "Stop all chemical applications",
                    "Watch for rat damage — set traps at field bunds",
                ],
                "dos": [
                    "Drain field gradually from day 105 onwards",
                    "Check grain moisture — harvest at 20–22% moisture for combine",
                ],
                "donts": [
                    "Do NOT apply any fertilizer or pesticide",
                    "Do NOT let field remain flooded — causes root rot and lodging",
                ],
                "fertilizer": None,
                "monitor": [
                    "Grain colour — golden yellow = ready to harvest",
                    "Moisture content — test a handful, grains should not be doughy",
                    "Rat or bird damage at field edges",
                ],
                "critical": False,
            },
            {
                "name": "Harvest",
                "start": 115, "end": 120, "emoji": "🎉",
                "key_tasks": [
                    "Harvest when 80% of grains are golden yellow",
                    "Use combine harvester or cut and thresh manually",
                    "Dry harvested grain to 14% moisture before storage",
                ],
                "dos": [
                    "Harvest in morning hours to reduce shattering loss",
                    "Store in clean, dry gunny bags away from moisture",
                ],
                "donts": [
                    "Do NOT delay harvest — over-ripening causes shattering loss",
                    "Do NOT store moist grain — causes fungal spoilage",
                ],
                "fertilizer": None,
                "monitor": [
                    "Check milling quality of a small sample before full harvest",
                ],
                "critical": False,
            },
        ],
    },

    "wheat": {
        "total_days": 120,
        "aliases": ["wheat", "gehun", "godhuma", "godhi"],
        "stages": [
            {
                "name": "Sowing / Germination",
                "start": 0, "end": 20, "emoji": "🌱",
                "key_tasks": [
                    "Sow treated seeds at 100–125 kg/hectare at 2–3 cm depth",
                    "Apply basal dose: 60 kg DAP + 30 kg MOP per hectare",
                    "Ensure pre-sowing irrigation if soil is dry",
                ],
                "dos": [
                    "Treat seeds with Thiram 3 g/kg before sowing to prevent smut",
                    "Sow in rows 20–22 cm apart for good tillering",
                    "Irrigate within 3 days if no rain after sowing",
                ],
                "donts": [
                    "Do NOT sow untreated seeds — Karnal bunt risk is high",
                    "Do NOT sow too deep (>5 cm) — poor emergence",
                    "Do NOT delay sowing beyond end of November in North India",
                ],
                "fertilizer": {
                    "day_range": [0, 0],
                    "product": "DAP + MOP (basal)",
                    "dose": "60 kg DAP + 30 kg MOP per hectare",
                    "method": "Apply in furrow before sowing",
                    "cost": "₹3,500–₹4,500",
                },
                "monitor": [
                    "Germination — 80%+ seedlings should emerge by day 7",
                    "Soil moisture — water if soil surface dries",
                    "Check for termite attack on seeds",
                ],
                "critical": False,
            },
            {
                "name": "Tillering",
                "start": 20, "end": 45, "emoji": "🌿",
                "key_tasks": [
                    "Apply first irrigation (Crown Root Initiation) at 20–25 days",
                    "Apply urea: 65 kg/hectare with first irrigation",
                    "Manual or chemical weeding if Phalaris arundinacea present",
                ],
                "dos": [
                    "Apply Clodinafop herbicide at 20 g/hectare if narrow-leaf weeds are heavy",
                    "Irrigate uniformly — uneven watering causes patchy tillering",
                ],
                "donts": [
                    "Do NOT skip the first irrigation — it is the most critical",
                    "Do NOT apply urea without irrigation — causes leaf burn",
                ],
                "fertilizer": {
                    "day_range": [20, 22],
                    "product": "Urea (1st split)",
                    "dose": "65 kg/hectare",
                    "method": "Broadcast just before irrigation",
                    "cost": "₹1,600–₹2,000",
                },
                "monitor": [
                    "Tiller count — target 5–6 productive tillers per plant",
                    "Yellow rust (yellow stripes on leaves) — spray Propiconazole if seen",
                    "Aphids on leaves — spray Dimethoate if count >15 per tiller",
                ],
                "critical": True,
            },
            {
                "name": "Jointing / Stem elongation",
                "start": 45, "end": 70, "emoji": "🌱",
                "key_tasks": [
                    "Apply second irrigation at day 45",
                    "Apply second urea split: 65 kg/hectare",
                    "Scout for yellow rust and powdery mildew",
                ],
                "dos": [
                    "Spray Propiconazole 25EC at 0.1% (1 ml/L) if rust appears",
                    "Irrigate carefully — lodging risk increases from now",
                ],
                "donts": [
                    "Do NOT apply excess nitrogen — increases lodging risk",
                    "Do NOT irrigate heavily in wind — causes stem breakage",
                ],
                "fertilizer": {
                    "day_range": [45, 47],
                    "product": "Urea (2nd split)",
                    "dose": "65 kg/hectare",
                    "method": "Broadcast before irrigation",
                    "cost": "₹1,600–₹2,000",
                },
                "monitor": [
                    "Yellow rust stripes on leaves",
                    "Powdery mildew (white powder on leaves)",
                    "Stem lodging — check for weak stem base",
                ],
                "critical": False,
            },
            {
                "name": "Booting / Heading",
                "start": 70, "end": 90, "emoji": "🌾",
                "key_tasks": [
                    "Apply third irrigation at boot stage (day 70)",
                    "Spray foliar potassium (0-0-50) if grain fill is poor",
                    "Watch for flag leaf blast — most important leaf",
                ],
                "dos": [
                    "Keep flag leaf green and healthy — it provides 70% of grain carbohydrate",
                    "Spray fungicide if flag leaf shows any spots",
                ],
                "donts": [
                    "Do NOT apply nitrogen after heading — promotes only stem growth",
                    "Do NOT let field dry during heading — critical for spike fertility",
                ],
                "fertilizer": None,
                "monitor": [
                    "Flag leaf health — any spots or rust = spray immediately",
                    "Head emergence — spike fully out by day 80",
                ],
                "critical": True,
            },
            {
                "name": "Grain filling",
                "start": 90, "end": 110, "emoji": "🌾",
                "key_tasks": [
                    "Apply fourth irrigation at milky stage (day 90)",
                    "No fertilizer applications",
                    "Watch for aphid attack on spikes",
                ],
                "dos": [
                    "Irrigate at milky stage — critical for grain weight",
                    "Apply Dimethoate if aphids found on grain heads",
                ],
                "donts": [
                    "Do NOT irrigate after day 105 — causes poor quality grain",
                    "Do NOT apply any pesticide after day 100",
                ],
                "fertilizer": None,
                "monitor": [
                    "Grain fill — squeeze grain, should turn from watery to milky to doughy",
                    "Aphids on spikes",
                    "Bird damage",
                ],
                "critical": False,
            },
            {
                "name": "Maturity / Harvest",
                "start": 110, "end": 120, "emoji": "🎉",
                "key_tasks": [
                    "Harvest at golden yellow stage — grain moisture 14–18%",
                    "Thrash promptly after cutting",
                    "Dry grain to 12% moisture before storage",
                ],
                "dos": [
                    "Harvest early morning or evening to reduce shatter loss",
                    "Store in cool, dry, ventilated space",
                ],
                "donts": [
                    "Do NOT delay harvest — rain on ripe wheat damages quality",
                    "Do NOT store wet grain",
                ],
                "fertilizer": None,
                "monitor": [
                    "Moisture content — bite a grain, should feel hard, not doughy",
                ],
                "critical": False,
            },
        ],
    },

    "cotton": {
        "total_days": 180,
        "aliases": ["cotton", "kapas", "patthi", "karpas", "narma"],
        "stages": [
            {
                "name": "Sowing / Germination",
                "start": 0, "end": 20, "emoji": "🌱",
                "key_tasks": [
                    "Sow Bt cotton seeds at 75×75 cm spacing, 2–3 cm deep",
                    "Apply FYM 5 tonnes/hectare and DAP 50 kg/hectare before sowing",
                    "Ensure soil moisture — irrigate if dry before sowing",
                ],
                "dos": [
                    "Treat seeds with Imidacloprid 70 WS at 5 g/kg for sucking pest protection",
                    "Sow in rows for easy intercultural operations",
                ],
                "donts": [
                    "Do NOT sow in waterlogged soil — seeds rot",
                    "Do NOT sow below 5 cm — poor emergence of cotton",
                ],
                "fertilizer": {
                    "day_range": [0, 0],
                    "product": "DAP (basal)",
                    "dose": "50 kg DAP per hectare",
                    "method": "Incorporate into soil before sowing",
                    "cost": "₹2,200–₹2,800",
                },
                "monitor": [
                    "Germination — 90%+ emergence by day 10",
                    "Damping-off — remove and drench Copper Oxychloride if seen",
                    "Termites — check seed zone",
                ],
                "critical": False,
            },
            {
                "name": "Seedling establishment",
                "start": 20, "end": 45, "emoji": "🌿",
                "key_tasks": [
                    "Gap fill — replant where germination failed",
                    "Apply urea: 50 kg/hectare as 1st split",
                    "Inter-cultivation to keep soil loose and weed-free",
                ],
                "dos": [
                    "Remove excess plants — keep 1 strong plant per hill",
                    "Apply neem cake (250 kg/hectare) if root knot nematode risk",
                ],
                "donts": [
                    "Do NOT over-irrigate — leads to root rot",
                    "Do NOT let weeds establish — they are extremely competitive at this stage",
                ],
                "fertilizer": {
                    "day_range": [30, 32],
                    "product": "Urea (1st split)",
                    "dose": "50 kg/hectare",
                    "method": "Side dress near plant base, cover with soil",
                    "cost": "₹1,200–₹1,500",
                },
                "monitor": [
                    "Thrips — silvery speckling on leaves (spray Fipronil if heavy)",
                    "Whitefly — honeydew on lower leaves (spray Diafenthiuron)",
                    "Leaf curl virus symptoms — curling, distortion = remove plant",
                ],
                "critical": False,
            },
            {
                "name": "Vegetative growth / Squaring",
                "start": 45, "end": 80, "emoji": "🌿",
                "key_tasks": [
                    "Apply urea 2nd split: 50 kg/hectare at day 60",
                    "Apply MOP: 50 kg/hectare at day 60",
                    "Topping (removal of terminal bud) on tall varieties if needed",
                ],
                "dos": [
                    "Spray Mepiquat Chloride (plant growth regulator) if plants are too vegetative",
                    "Maintain 10–12 day irrigation interval in this stage",
                    "Scout for pink bollworm entry in flower buds",
                ],
                "donts": [
                    "Do NOT apply excess nitrogen — promotes vegetative growth, delays fruiting",
                    "Do NOT skip irrigation — flower bud shedding occurs in water stress",
                ],
                "fertilizer": {
                    "day_range": [60, 62],
                    "product": "Urea (2nd split) + MOP",
                    "dose": "50 kg Urea + 50 kg MOP per hectare",
                    "method": "Side dress, cover with soil, irrigate",
                    "cost": "₹3,000–₹3,800",
                },
                "monitor": [
                    "American bollworm egg count on upper leaves",
                    "Pink bollworm — entry holes in flower buds",
                    "Thrips and whitefly population",
                    "Irrigation requirement — check soil at 15 cm depth",
                ],
                "critical": False,
            },
            {
                "name": "Flowering / Boll setting",
                "start": 80, "end": 120, "emoji": "🌸",
                "key_tasks": [
                    "Maintain irrigation every 10–12 days — critical for boll retention",
                    "Spray Chlorpyriphos + Cypermethrin for bollworm if ETL crossed",
                    "Remove and destroy boll-damaged squares to reduce pest load",
                ],
                "dos": [
                    "Use pheromone traps (4 per acre) for bollworm monitoring",
                    "Spray foliar fertilizer (13:00:45 — 5 g/L) for boll development",
                    "Pick and destroy pink bollworm-infested squares daily",
                ],
                "donts": [
                    "Do NOT use pyrethroid sprays alone — causes whitefly resistance",
                    "Do NOT skip irrigation — boll shedding is directly linked to water stress",
                    "Do NOT spray during hot afternoon hours",
                ],
                "fertilizer": {
                    "day_range": [85, 88],
                    "product": "Foliar nutrition (13:00:45)",
                    "dose": "5 g per litre, spray 500 L/hectare",
                    "method": "Foliar spray on leaves and bolls",
                    "cost": "₹800–₹1,200",
                },
                "monitor": [
                    "Pheromone trap count — if >8 moths/trap/week, spray bollworm",
                    "Boll retention — count bolls per plant weekly",
                    "Sucking pests — thrips, whitefly under leaves",
                ],
                "critical": True,
            },
            {
                "name": "Boll development / Maturation",
                "start": 120, "end": 160, "emoji": "🌾",
                "key_tasks": [
                    "Reduce irrigation frequency — 15–20 day intervals",
                    "Apply ethephon spray (40 ml/100 L) to accelerate boll opening",
                    "Stop all chemical applications 21 days before picking",
                ],
                "dos": [
                    "Hand-pick open bolls separately from closed bolls",
                    "Grade cotton by colour and trash content",
                ],
                "donts": [
                    "Do NOT irrigate after bolls start opening naturally",
                    "Do NOT spray any chemical 21 days before picking",
                ],
                "fertilizer": None,
                "monitor": [
                    "Boll weevil — check for pinhole entry in bolls",
                    "Mealy bugs at stem base and boll junction",
                    "Boll opening percentage — harvest when >60% open",
                ],
                "critical": False,
            },
            {
                "name": "Harvest",
                "start": 160, "end": 180, "emoji": "🎉",
                "key_tasks": [
                    "Pick cotton every 10–15 days — multiple pickings",
                    "Store in clean, dry gunny bags away from rain",
                    "Separate grades — shankar-6 cotton gets premium price",
                ],
                "dos": [
                    "Pick in the morning when cotton is dry",
                    "Remove all plant residue after last picking",
                ],
                "donts": [
                    "Do NOT mix wet and dry cotton — reduces grade",
                    "Do NOT store unpicked cotton — boll weevil will damage",
                ],
                "fertilizer": None,
                "monitor": [
                    "Boll opening rate — pick all open bolls within 2 days",
                    "Market price — check mandi rates before selling",
                ],
                "critical": False,
            },
        ],
    },

    "tomato": {
        "total_days": 90,
        "aliases": ["tomato", "tamatar", "thakkali", "tameta", "tomat"],
        "stages": [
            {
                "name": "Nursery raising",
                "start": 0, "end": 25, "emoji": "🌱",
                "key_tasks": [
                    "Prepare raised nursery beds — mix soil + FYM + sand (1:1:1)",
                    "Sow seeds at 1 cm depth, 5 cm apart",
                    "Water gently with watering can twice daily",
                ],
                "dos": [
                    "Treat seeds with Thiram 2 g/kg before sowing",
                    "Cover nursery with 50% shade net to protect from harsh sun",
                    "Apply Drenching with Copper Oxychloride on day 10 to prevent damping-off",
                ],
                "donts": [
                    "Do NOT over-water — causes damping-off disease",
                    "Do NOT transplant before seedlings have 5–6 true leaves",
                    "Do NOT use heavy soil — roots cannot penetrate",
                ],
                "fertilizer": {
                    "day_range": [10, 12],
                    "product": "19:19:19 soluble fertilizer",
                    "dose": "2 g per litre — spray on seedlings",
                    "method": "Foliar spray on seedlings, avoid midday",
                    "cost": "₹200–₹300",
                },
                "monitor": [
                    "Damping-off — rotting at stem base (drench Copper Oxychloride)",
                    "Leaf curl virus — check for whitefly on underside of leaves",
                    "Seedling height — should reach 15–20 cm by day 20",
                ],
                "critical": False,
            },
            {
                "name": "Transplanting and establishment",
                "start": 25, "end": 40, "emoji": "🌿",
                "key_tasks": [
                    "Transplant in the evening at 60×45 cm spacing",
                    "Apply 10 tonnes FYM/hectare + DAP 100 kg/hectare before transplanting",
                    "Stake plants immediately after transplanting if indeterminate variety",
                ],
                "dos": [
                    "Water immediately after transplanting and daily for first week",
                    "Apply Trichoderma 2 g/kg of soil around each plant root zone",
                ],
                "donts": [
                    "Do NOT transplant in afternoon heat",
                    "Do NOT let newly transplanted seedlings wilt",
                ],
                "fertilizer": {
                    "day_range": [25, 25],
                    "product": "DAP (basal)",
                    "dose": "100 kg/hectare",
                    "method": "Mix into soil 2 weeks before transplanting",
                    "cost": "₹2,400–₹3,000",
                },
                "monitor": [
                    "Transplant survival — 95%+ should establish in 5 days",
                    "Early blight — brown circular spots on lower leaves",
                    "Root health — yellowing plants may have root knot nematode",
                ],
                "critical": True,
            },
            {
                "name": "Vegetative growth",
                "start": 40, "end": 60, "emoji": "🌿",
                "key_tasks": [
                    "Apply urea 50 kg/hectare at day 40",
                    "Prune lower leaves and side shoots for determinate varieties",
                    "Spray Mancozeb (2.5 g/L) preventively for early blight",
                ],
                "dos": [
                    "Apply Calcium Nitrate foliar spray (2 g/L) for blossom end rot prevention",
                    "Train plants on stakes — tie loosely",
                ],
                "donts": [
                    "Do NOT over-irrigate — causes Fusarium wilt",
                    "Do NOT skip pruning — causes disease build-up in dense canopy",
                ],
                "fertilizer": {
                    "day_range": [40, 42],
                    "product": "Urea",
                    "dose": "50 kg/hectare",
                    "method": "Side dress near plant base, irrigate",
                    "cost": "₹1,200–₹1,500",
                },
                "monitor": [
                    "Leaf curl (virus) — distorted, curled leaves with purple tinge",
                    "Early blight — spray Mancozeb on first sign",
                    "Fruit fly trap count — set McPhail traps at 4/acre",
                ],
                "critical": False,
            },
            {
                "name": "Flowering",
                "start": 60, "end": 70, "emoji": "🌸",
                "key_tasks": [
                    "Spray Boron (0.2%) + Calcium (0.5%) foliar for flower set",
                    "Apply MOP 50 kg/hectare for fruit quality",
                    "Maintain consistent soil moisture — fluctuation causes flower drop",
                ],
                "dos": [
                    "Spray 13:00:45 fertilizer at 5 g/L for flower retention",
                    "Monitor for tomato fruit borer eggs on flowers",
                ],
                "donts": [
                    "Do NOT spray during 8 AM–12 PM — peak pollination time",
                    "Do NOT apply high nitrogen now — promotes leaf, not fruit",
                ],
                "fertilizer": {
                    "day_range": [60, 62],
                    "product": "MOP + Boron",
                    "dose": "50 kg MOP/hectare + Boron 2 kg/hectare",
                    "method": "MOP soil application; Boron foliar spray 0.2%",
                    "cost": "₹1,500–₹2,000",
                },
                "monitor": [
                    "Flower drop — 20%+ drop means stress (water/nutrient/heat)",
                    "Fruit borer entry holes in fruits",
                    "Leaf curl virus spread",
                ],
                "critical": True,
            },
            {
                "name": "Fruit development",
                "start": 70, "end": 85, "emoji": "🍅",
                "key_tasks": [
                    "Apply 00:52:34 foliar fertilizer (5 g/L) for fruit size",
                    "Spray Emamectin Benzoate for fruit borer control",
                    "Irrigate every 4–5 days — critical for uniform fruit size",
                ],
                "dos": [
                    "Spray Calcium Nitrate 2 g/L to prevent blossom end rot",
                    "Harvest mature green fruits for distant markets",
                    "Remove and destroy infected/cracked fruits to reduce disease load",
                ],
                "donts": [
                    "Do NOT over-irrigate — causes fruit cracking",
                    "Do NOT spray within 7 days of harvest",
                ],
                "fertilizer": {
                    "day_range": [70, 72],
                    "product": "00:52:34 + Calcium Nitrate",
                    "dose": "5 g/L foliar spray + 2 g/L Ca(NO₃)₂",
                    "method": "Foliar spray in the evening",
                    "cost": "₹400–₹600",
                },
                "monitor": [
                    "Blossom end rot — dark, sunken patch at fruit bottom",
                    "Fruit borer entry holes",
                    "Early blight on fruit surface",
                    "Fruit size uniformity",
                ],
                "critical": True,
            },
            {
                "name": "Harvest",
                "start": 85, "end": 90, "emoji": "🎉",
                "key_tasks": [
                    "Harvest at correct stage — mature green for long transport, half-red for local",
                    "Handle fruits carefully to avoid bruising",
                    "Grade fruits by size and quality",
                ],
                "dos": [
                    "Harvest every 2–3 days during peak season",
                    "Cool harvested fruits in shade before packing",
                ],
                "donts": [
                    "Do NOT mix damaged and healthy fruits",
                    "Do NOT leave over-ripe fruits on plant — attracts pests",
                ],
                "fertilizer": None,
                "monitor": [
                    "Market price — check mandi before deciding to harvest",
                    "Fruit fly damage at harvest",
                ],
                "critical": False,
            },
        ],
    },

    "maize": {
        "total_days": 95,
        "aliases": ["maize", "corn", "makka", "makki", "cholam", "jonna"],
        "stages": [
            {
                "name": "Sowing / Germination",
                "start": 0, "end": 15, "emoji": "🌱",
                "key_tasks": [
                    "Sow seeds at 60×25 cm spacing, 3–4 cm deep",
                    "Apply DAP 50 kg + MOP 25 kg per hectare as basal dose",
                    "Keep soil moist for uniform germination",
                ],
                "dos": [
                    "Treat seeds with Thiram+Carbendazim for Pythium control",
                    "Sow when soil temperature is above 15°C",
                ],
                "donts": [
                    "Do NOT sow too deep — germination fails above 5 cm",
                    "Do NOT sow in cold or waterlogged soil",
                ],
                "fertilizer": {
                    "day_range": [0, 0],
                    "product": "DAP + MOP (basal)",
                    "dose": "50 kg DAP + 25 kg MOP per hectare",
                    "method": "Place in furrow before sowing",
                    "cost": "₹2,500–₹3,200",
                },
                "monitor": [
                    "Germination uniformity — target 90%+ by day 7",
                    "Termite attack on seeds",
                    "Soil crust — break gently if crust forms before emergence",
                ],
                "critical": False,
            },
            {
                "name": "Vegetative growth",
                "start": 15, "end": 45, "emoji": "🌿",
                "key_tasks": [
                    "Apply first urea split: 60 kg/hectare at 4–5 leaf stage (day 20)",
                    "Weed at 15–20 days — manual hoeing or Atrazine spray",
                    "Irrigate at 10–12 day intervals",
                ],
                "dos": [
                    "Earth up (mound soil to base) at day 30 for better root support",
                    "Remove side tillers (suckers) if any in the first 30 days",
                ],
                "donts": [
                    "Do NOT allow waterlogging — maize is highly sensitive",
                    "Do NOT miss first urea application — it drives vegetative yield",
                ],
                "fertilizer": {
                    "day_range": [20, 22],
                    "product": "Urea (1st split)",
                    "dose": "60 kg/hectare",
                    "method": "Side dress near row, cover with soil",
                    "cost": "₹1,400–₹1,800",
                },
                "monitor": [
                    "Fall army worm — look for window-pane damage on young leaves",
                    "Downy mildew — white powder on undersides of lower leaves",
                    "Soil moisture — water if leaves roll inward in morning",
                ],
                "critical": True,
            },
            {
                "name": "Tasseling / Silking",
                "start": 45, "end": 65, "emoji": "🌸",
                "key_tasks": [
                    "Apply second urea split: 60 kg/hectare at tasseling",
                    "Ensure adequate irrigation — most critical stage for yield",
                    "Spray micronutrients (ZnSO₄ 5 g/L) if zinc deficiency seen",
                ],
                "dos": [
                    "Irrigate every 7 days during tasseling and silking",
                    "Remove diseased tassels to prevent spread",
                ],
                "donts": [
                    "Do NOT let water stress occur during tasseling — causes poor pollination",
                    "Do NOT apply any herbicide after tasseling",
                ],
                "fertilizer": {
                    "day_range": [50, 52],
                    "product": "Urea (2nd split)",
                    "dose": "60 kg/hectare",
                    "method": "Side dress near plant, irrigate",
                    "cost": "₹1,400–₹1,800",
                },
                "monitor": [
                    "Silk emergence — silks should appear within 2–3 days of tasseling",
                    "Corn borer — entry into tassel",
                    "Aphids on tassels — spray if count > 100 per tassel",
                ],
                "critical": True,
            },
            {
                "name": "Grain filling",
                "start": 65, "end": 85, "emoji": "🌾",
                "key_tasks": [
                    "Apply one irrigation at milky stage (day 70)",
                    "Stop all fertilizer applications",
                    "Watch for ear rot (Fusarium)",
                ],
                "dos": [
                    "Check ears by peeling back husk — grain should be hard and yellow",
                    "Remove and destroy any rotten ears",
                ],
                "donts": [
                    "Do NOT apply any chemical at this stage",
                    "Do NOT waterlog the field — causes ear rots",
                ],
                "fertilizer": None,
                "monitor": [
                    "Ear rot — pinkish mold inside the husk",
                    "Grain filling uniformity — check 5 ears from different plants",
                    "Bird damage at field edges",
                ],
                "critical": False,
            },
            {
                "name": "Maturity / Harvest",
                "start": 85, "end": 95, "emoji": "🎉",
                "key_tasks": [
                    "Harvest when husks are dry and grain shows black layer",
                    "Dry cobs to 14% moisture before shelling",
                    "Shell and store in ventilated bins",
                ],
                "dos": [
                    "Harvest promptly to avoid aflatoxin risk in field",
                    "Check market price — sell at 14% moisture for best rate",
                ],
                "donts": [
                    "Do NOT store wet grain — aflatoxin develops rapidly",
                    "Do NOT delay harvest in humid conditions",
                ],
                "fertilizer": None,
                "monitor": [
                    "Black layer formation at grain tip — harvest readiness indicator",
                    "Grain moisture — target 14–16% for harvest",
                ],
                "critical": False,
            },
        ],
    },

    "groundnut": {
        "total_days": 110,
        "aliases": ["groundnut", "peanut", "moongphali", "verusenaga", "shenga", "nilakadalai"],
        "stages": [
            {
                "name": "Sowing / Germination",
                "start": 0, "end": 15, "emoji": "🌱",
                "key_tasks": [
                    "Shell pods, select bold seeds, treat with Thiram 3 g/kg",
                    "Sow at 30×10 cm spacing, 4–5 cm deep",
                    "Apply SSP 400 kg/hectare as basal — calcium is critical for pegs",
                ],
                "dos": [
                    "Inoculate seeds with Rhizobium culture for nitrogen fixation",
                    "Maintain soil moisture during germination",
                ],
                "donts": [
                    "Do NOT apply urea — groundnut fixes its own nitrogen",
                    "Do NOT sow in waterlogged or heavy clay soil",
                ],
                "fertilizer": {
                    "day_range": [0, 0],
                    "product": "SSP (Single Super Phosphate)",
                    "dose": "400 kg/hectare",
                    "method": "Incorporate into soil before sowing",
                    "cost": "₹3,200–₹4,000",
                },
                "monitor": [
                    "Germination rate — 90%+ by day 10",
                    "Leaf miner on early leaves",
                    "Termite damage on seeds",
                ],
                "critical": False,
            },
            {
                "name": "Vegetative growth",
                "start": 15, "end": 40, "emoji": "🌿",
                "key_tasks": [
                    "Weed at 15–20 days — very competitive stage",
                    "Apply gypsum 400 kg/hectare at pegging stage (day 35)",
                    "Light earthing up at 30–35 days to facilitate peg entry",
                ],
                "dos": [
                    "Spray Chlorimuron herbicide for broad-leaf weed control",
                    "Check nodules on roots — pink inside = working, white = not working",
                ],
                "donts": [
                    "Do NOT over-irrigate — root rot risk is high",
                    "Do NOT deep plough near plants — breaks pegs",
                ],
                "fertilizer": {
                    "day_range": [35, 37],
                    "product": "Gypsum (for pod calcium)",
                    "dose": "400 kg/hectare",
                    "method": "Broadcast around plants, do not incorporate",
                    "cost": "₹1,600–₹2,000",
                },
                "monitor": [
                    "Early leaf spot (Cercospora) — spray Carbendazim at first sign",
                    "Stem rot at plant base",
                    "Aphid colony under leaves",
                ],
                "critical": False,
            },
            {
                "name": "Pegging / Pod initiation",
                "start": 40, "end": 70, "emoji": "🥜",
                "key_tasks": [
                    "Ensure good soil contact for peg entry — gentle earthing up",
                    "Irrigate every 8–10 days — pegs need moist soil to enter",
                    "Spray Chlorothalonil for Cercospora leaf spot",
                ],
                "dos": [
                    "Avoid disturbing soil near plants — pegs are fragile",
                    "Apply foliar calcium spray if gypsum was not applied",
                ],
                "donts": [
                    "Do NOT let soil surface crust — pegs cannot penetrate",
                    "Do NOT deep irrigate — surface moisture is what matters",
                ],
                "fertilizer": None,
                "monitor": [
                    "Peg count and entry depth",
                    "Leaf spot disease progress",
                    "Soil crusting — break gently with hand hoe",
                ],
                "critical": True,
            },
            {
                "name": "Pod filling",
                "start": 70, "end": 100, "emoji": "🥜",
                "key_tasks": [
                    "Irrigate regularly — water stress reduces seed size significantly",
                    "Spray Mancozeb 2.5 g/L for late leaf spot and rust",
                    "Check for aflatoxin risk — avoid water stress and damage",
                ],
                "dos": [
                    "Maintain soil moisture — critical for kernel development",
                    "Spray foliar potassium for improved kernel quality",
                ],
                "donts": [
                    "Do NOT apply nitrogen fertilizer",
                    "Do NOT cause waterlogging — triggers aflatoxin",
                ],
                "fertilizer": None,
                "monitor": [
                    "Pod maturity — scratch test, inside of pod wall turns brown",
                    "Leaf defoliation from late leaf spot",
                    "Groundnut bud necrosis virus",
                ],
                "critical": False,
            },
            {
                "name": "Maturity / Harvest",
                "start": 100, "end": 110, "emoji": "🎉",
                "key_tasks": [
                    "Harvest when 70–80% pods show inner brown colour",
                    "Dry vines with pods in field for 3–4 days before threshing",
                    "Shell and dry kernels to 8% moisture",
                ],
                "dos": [
                    "Harvest promptly — over-matured pods shatter in field",
                    "Stack vines upside down for fast drying",
                ],
                "donts": [
                    "Do NOT harvest in wet soil — pods remain underground",
                    "Do NOT store undried pods — aflatoxin risk",
                ],
                "fertilizer": None,
                "monitor": [
                    "Maturity test — pull 5 plants, check pod colour inside",
                    "Aflatoxin risk — avoid damaged or mold-affected pods",
                ],
                "critical": False,
            },
        ],
    },

    "onion": {
        "total_days": 100,
        "aliases": ["onion", "pyaz", "ullipayalu", "vengayam", "kanda", "savalu"],
        "stages": [
            {
                "name": "Nursery",
                "start": 0, "end": 30, "emoji": "🌱",
                "key_tasks": [
                    "Prepare raised beds 1 m wide, sow seeds at 5 g/m²",
                    "Apply 2 kg/m² FYM and 25 g/m² DAP",
                    "Water twice daily with gentle watering can",
                ],
                "dos": [
                    "Shade nursery for first 7 days with dry grass cover",
                    "Apply Carbendazim drench if damping-off starts",
                ],
                "donts": [
                    "Do NOT flood-irrigate nursery — seeds wash away",
                    "Do NOT transplant before seedlings reach pencil-size (6–7 mm)",
                ],
                "fertilizer": {
                    "day_range": [10, 12],
                    "product": "19:19:19 foliar",
                    "dose": "3 g per litre, spray on seedlings",
                    "method": "Foliar spray at 10 and 20 days",
                    "cost": "₹150–₹250",
                },
                "monitor": [
                    "Damping-off — collapse at seedling base",
                    "Thrips on young leaves — silvery streaks",
                    "Seedling size — transplant when 20 cm tall, pencil-sized",
                ],
                "critical": False,
            },
            {
                "name": "Transplanting and establishment",
                "start": 30, "end": 50, "emoji": "🌿",
                "key_tasks": [
                    "Transplant at 15×10 cm spacing, 3–4 cm deep",
                    "Apply DAP 100 kg + MOP 50 kg/hectare before transplanting",
                    "Irrigate immediately and daily for first week",
                ],
                "dos": [
                    "Transplant in the evening to reduce heat stress",
                    "Apply Trichoderma around root zone",
                ],
                "donts": [
                    "Do NOT transplant too deep — bulb development is restricted",
                    "Do NOT allow wilting after transplanting",
                ],
                "fertilizer": {
                    "day_range": [30, 30],
                    "product": "DAP + MOP (basal)",
                    "dose": "100 kg DAP + 50 kg MOP per hectare",
                    "method": "Incorporate into soil before transplanting",
                    "cost": "₹5,000–₹6,500",
                },
                "monitor": [
                    "Transplant survival — 95%+ establishment",
                    "Purple blotch disease — water-soaked spots on leaves",
                    "Thrips — silver streaking on leaves",
                ],
                "critical": True,
            },
            {
                "name": "Bulb initiation",
                "start": 50, "end": 75, "emoji": "🧅",
                "key_tasks": [
                    "Apply urea 75 kg/hectare at day 50 for leaf growth",
                    "Spray Mancozeb 2.5 g/L + Fipronil for thrips and blight",
                    "Irrigate every 7–8 days — avoid excess",
                ],
                "dos": [
                    "Apply MOP foliar spray (1%) at bulb initiation for size",
                    "Earth up lightly to support bulb",
                ],
                "donts": [
                    "Do NOT over-irrigate — causes neck rot",
                    "Do NOT apply nitrogen after bulbing starts",
                ],
                "fertilizer": {
                    "day_range": [50, 52],
                    "product": "Urea",
                    "dose": "75 kg/hectare",
                    "method": "Side dress, irrigate",
                    "cost": "₹1,800–₹2,200",
                },
                "monitor": [
                    "Thrips population — most damaging at this stage",
                    "Purple blotch and downy mildew",
                    "Bulb size at base — check weekly",
                ],
                "critical": True,
            },
            {
                "name": "Bulb enlargement",
                "start": 75, "end": 92, "emoji": "🧅",
                "key_tasks": [
                    "Reduce irrigation — irrigate every 10–12 days",
                    "Stop all fertilizer applications at day 75",
                    "Watch for neck-fall (tops falling) — harvest signal approaching",
                ],
                "dos": [
                    "Apply foliar potassium 0.5% if bulbs are small",
                    "Scout for Stemphylium blight — spray Iprodione if seen",
                ],
                "donts": [
                    "Do NOT apply any nitrogen — causes green skin and poor keeping quality",
                    "Do NOT irrigate heavily — causes neck rot before harvest",
                ],
                "fertilizer": None,
                "monitor": [
                    "Neck fall percentage — harvest when 50% tops have fallen",
                    "Neck rot inside bulbs — cut a few to check",
                    "Bulb size and skin colour",
                ],
                "critical": False,
            },
            {
                "name": "Harvest and curing",
                "start": 92, "end": 100, "emoji": "🎉",
                "key_tasks": [
                    "Harvest when 50–75% of tops have fallen",
                    "Pull bulbs out, cut tops leaving 2 cm neck",
                    "Cure in shade for 7–10 days before storage",
                ],
                "dos": [
                    "Harvest in dry weather",
                    "Grade by size — medium (55–75 mm) gets premium price",
                ],
                "donts": [
                    "Do NOT harvest in rain or immediately after irrigation",
                    "Do NOT store uncured onions — causes neck rot in storage",
                ],
                "fertilizer": None,
                "monitor": [
                    "Neck moisture — bulb neck should be completely dry for storage",
                    "Market price before deciding to sell fresh or store",
                ],
                "critical": False,
            },
        ],
    },

    "chilli": {
        "total_days": 105,
        "aliases": ["chilli", "chili", "pepper", "mirchi", "milapakaya", "milagai", "marcha"],
        "stages": [
            {
                "name": "Nursery",
                "start": 0, "end": 30, "emoji": "🌱",
                "key_tasks": [
                    "Prepare raised nursery beds with FYM + sand + soil (1:1:1)",
                    "Sow seeds at 4 cm apart, 0.5 cm deep",
                    "Water twice daily — seeds need constant moisture",
                ],
                "dos": [
                    "Treat seeds with Thiram 3 g/kg for seed-borne diseases",
                    "Cover nursery with 50% shade net to protect young seedlings",
                ],
                "donts": [
                    "Do NOT over-water — damping-off is the main risk",
                    "Do NOT transplant before 5 true leaves appear",
                ],
                "fertilizer": {
                    "day_range": [15, 17],
                    "product": "19:19:19 foliar",
                    "dose": "2 g per litre spray on seedlings",
                    "method": "Foliar spray at 15 and 25 days",
                    "cost": "₹100–₹150",
                },
                "monitor": [
                    "Damping-off — drench Copper Oxychloride if seen",
                    "Thrips and aphids on seedlings",
                ],
                "critical": False,
            },
            {
                "name": "Transplanting and establishment",
                "start": 30, "end": 50, "emoji": "🌿",
                "key_tasks": [
                    "Transplant at 60×45 cm spacing in evening",
                    "Apply DAP 100 kg + MOP 50 kg per hectare as basal",
                    "Water immediately and daily for first week",
                ],
                "dos": [
                    "Mulch with dry leaves or plastic to conserve moisture",
                    "Apply Trichoderma 2 g/plant root zone for Fusarium wilt prevention",
                ],
                "donts": [
                    "Do NOT transplant in afternoon heat",
                    "Do NOT let soil dry completely after transplanting",
                ],
                "fertilizer": {
                    "day_range": [30, 30],
                    "product": "DAP + MOP (basal)",
                    "dose": "100 kg DAP + 50 kg MOP per hectare",
                    "method": "Mix into soil before transplanting",
                    "cost": "₹5,000–₹6,500",
                },
                "monitor": [
                    "Wilt (Phytophthora/Fusarium) — remove wilted plants immediately",
                    "Anthracnose on leaves",
                    "Thrips infestation",
                ],
                "critical": True,
            },
            {
                "name": "Vegetative / Flowering",
                "start": 50, "end": 75, "emoji": "🌸",
                "key_tasks": [
                    "Apply urea 50 kg + MOP 30 kg/hectare at day 55",
                    "Spray Imidacloprid for thrips and virus vector control",
                    "Drench Metalaxyl at plant base for Phytophthora wilt",
                ],
                "dos": [
                    "Spray Boron 0.2% for improved flower setting",
                    "Apply calcium nitrate foliar (2 g/L) for fruit quality",
                ],
                "donts": [
                    "Do NOT spray during flowering (8 AM–12 PM)",
                    "Do NOT apply excess nitrogen — causes flower drop",
                ],
                "fertilizer": {
                    "day_range": [55, 57],
                    "product": "Urea + MOP",
                    "dose": "50 kg Urea + 30 kg MOP per hectare",
                    "method": "Side dress and irrigate",
                    "cost": "₹2,800–₹3,500",
                },
                "monitor": [
                    "Leaf curl (Thrips-transmitted virus) — remove affected plants",
                    "Flower drop — check for stress cause",
                    "Anthracnose on leaves and fruits",
                ],
                "critical": True,
            },
            {
                "name": "Fruit setting and development",
                "start": 75, "end": 95, "emoji": "🌶",
                "key_tasks": [
                    "Apply foliar potassium 0.5% for fruit size and colour",
                    "Spray Chlorfenapyr for fruit borers",
                    "Irrigate every 7–8 days",
                ],
                "dos": [
                    "Pick mature red fruits every 3–4 days during season",
                    "Apply calcium spray (2 g/L) for sunscald prevention",
                ],
                "donts": [
                    "Do NOT over-irrigate — causes Phytophthora spread",
                    "Do NOT spray within 10 days of harvest",
                ],
                "fertilizer": {
                    "day_range": [78, 80],
                    "product": "SOP (0:0:50) foliar",
                    "dose": "5 g per litre, 500 L/hectare",
                    "method": "Foliar spray in the evening",
                    "cost": "₹500–₹700",
                },
                "monitor": [
                    "Fruit borer and anthracnose on fruits",
                    "Thrips — check under leaves",
                    "Colour development — deep red = market ready",
                ],
                "critical": False,
            },
            {
                "name": "Harvest",
                "start": 95, "end": 105, "emoji": "🎉",
                "key_tasks": [
                    "Harvest when fruits are fully red (for dry chilli) or mature green",
                    "Handle carefully — bruised chilli loses value rapidly",
                    "Dry harvested chilli to 10% moisture for dry market",
                ],
                "dos": [
                    "Harvest every 2–3 days during peak season",
                    "Grade by colour and size",
                ],
                "donts": [
                    "Do NOT mix green and red chilli",
                    "Do NOT leave over-ripe chilli on plant — attracts anthracnose",
                ],
                "fertilizer": None,
                "monitor": [
                    "Market price — fresh vs dried — decide based on rates",
                    "Fruit quality — check for blemishes before packing",
                ],
                "critical": False,
            },
        ],
    },
}


# ══════════════════════════════════════════════════════════════════
# MATCH CROP TO DATABASE
# ══════════════════════════════════════════════════════════════════

def match_crop(crop_name: str) -> Optional[str]:
    """
    Given a crop name (in any language/spelling), return the canonical
    key in CROP_LIFECYCLES, or None if not found.
    """
    name = crop_name.lower().strip()
    for key, data in CROP_LIFECYCLES.items():
        if key == name:
            return key
        if name in data.get("aliases", []):
            return key
    # partial match
    for key, data in CROP_LIFECYCLES.items():
        for alias in data.get("aliases", []):
            if alias in name or name in alias:
                return key
    return None


def get_supported_crops() -> list[str]:
    return [k.title() for k in CROP_LIFECYCLES.keys()]


# ══════════════════════════════════════════════════════════════════
# STAGE ENGINE
# ══════════════════════════════════════════════════════════════════

def get_stage_for_day(crop_key: str, day: int) -> Optional[dict]:
    """
    Return the stage dict for a given day number (1-indexed).
    Adds computed fields: day_in_stage, stage_progress_pct.
    """
    lifecycle = CROP_LIFECYCLES.get(crop_key)
    if not lifecycle:
        return None
    for stage in lifecycle["stages"]:
        if stage["start"] <= day < stage["end"]:
            span = stage["end"] - stage["start"]
            day_in = day - stage["start"]
            return {
                **stage,
                "day_in_stage":       day_in + 1,
                "stage_total_days":   span,
                "stage_progress_pct": round((day_in / span) * 100),
                "crop_day":           day,
                "crop_total_days":    lifecycle["total_days"],
                "crop_progress_pct":  round((day / lifecycle["total_days"]) * 100),
            }
    return None


def fertilizer_due_today(crop_key: str, day: int) -> Optional[dict]:
    """Return fertilizer info if today falls in application window."""
    stage = get_stage_for_day(crop_key, day)
    if not stage:
        return None
    fert = stage.get("fertilizer")
    if fert and fert.get("day_range"):
        lo, hi = fert["day_range"]
        if lo <= day <= hi:
            return fert
    return None


# ══════════════════════════════════════════════════════════════════
# JOURNEY STORE
# ══════════════════════════════════════════════════════════════════

def _load_journeys() -> dict:
    if not os.path.exists(JOURNEY_PATH):
        return {}
    try:
        with open(JOURNEY_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_journeys(data: dict) -> None:
    with open(JOURNEY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def start_journey(
    user_id:     int,
    crop_key:    str,
    sow_date:    date,
    alarm_time:  str = "06:00",
    timezone:    str = "Asia/Kolkata",
) -> dict:
    """Start a new crop journey. Returns the journey dict."""
    data = _load_journeys()
    key  = str(user_id)

    lifecycle    = CROP_LIFECYCLES[crop_key]
    total_days   = lifecycle["total_days"]
    harvest_date = sow_date + timedelta(days=total_days)

    journey = {
        "crop_key":     crop_key,
        "crop_name":    crop_key.title(),
        "sow_date":     sow_date.isoformat(),
        "harvest_date": harvest_date.isoformat(),
        "total_days":   total_days,
        "alarm_time":   alarm_time,
        "timezone":     timezone,
        "active":       True,
        "started_at":   datetime.utcnow().isoformat(),
    }
    data[key] = journey
    _save_journeys(data)
    log.info("[journey] Started %s journey for user %s, sow=%s", crop_key, user_id, sow_date)
    return journey


def get_journey(user_id: int) -> Optional[dict]:
    return _load_journeys().get(str(user_id))


def end_journey(user_id: int) -> None:
    data = _load_journeys()
    key  = str(user_id)
    if key in data:
        data[key]["active"] = False
        _save_journeys(data)
        log.info("[journey] Ended journey for user %s", user_id)


def get_current_day(journey: dict) -> int:
    """Return day number (1 = sow day) for today."""
    sow = date.fromisoformat(journey["sow_date"])
    today = date.today()
    return max(1, (today - sow).days + 1)


def get_all_active_journeys() -> list[tuple[int, dict]]:
    """Return [(user_id, journey_dict), ...] for all active journeys."""
    data = _load_journeys()
    return [
        (int(uid), j)
        for uid, j in data.items()
        if j.get("active")
    ]


def journey_summary_text(journey: dict) -> str:
    """One-line summary: Crop | Day N of M | Stage Name"""
    day    = get_current_day(journey)
    key    = journey["crop_key"]
    stage  = get_stage_for_day(key, day)
    total  = journey["total_days"]
    sname  = stage["name"] if stage else "Complete"
    emoji  = stage["emoji"] if stage else "🎉"
    return (
        f"{emoji} *{journey['crop_name']} Journey*\n"
        f"Day {day} of {total} | {sname}\n"
        f"Progress: {'█' * (day * 10 // total)}{'░' * (10 - day * 10 // total)} {day * 100 // total}%"
    )
