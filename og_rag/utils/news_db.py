"""
utils/news_db.py  —  Fake farming news DB for Agrithm demo
──────────────────────────────────────────────────────────
A hardcoded list of realistic Indian farming news items.
Used by the Daily News button to show today's top stories.
"""

from datetime import date, timedelta
import random

# ── Hardcoded news items (realistic Indian farming news) ─────────────
_NEWS_ITEMS = [
    {
        "id": 1,
        "title": "MSP for Paddy Increased by ₹143 per Quintal",
        "body": (
            "The Cabinet Committee on Economic Affairs has approved a hike in the "
            "Minimum Support Price (MSP) for Kharif paddy to ₹2,183 per quintal. "
            "Farmers are advised to register at their nearest APMC to benefit from "
            "government procurement this season."
        ),
        "category": "🏛️ Government Policy",
        "tags": ["paddy", "rice", "MSP", "kharif"],
    },
    {
        "id": 2,
        "title": "Blast Blight Alert for Paddy in Tamil Nadu & AP",
        "body": (
            "The Department of Agriculture has issued an advisory warning farmers in "
            "Tamil Nadu and Andhra Pradesh about increased risk of blast blight in paddy "
            "due to high humidity. Spray Tricyclazole 75 WP @ 0.6 g/litre of water "
            "preventively. Avoid excess nitrogen application."
        ),
        "category": "⚠️ Disease Alert",
        "tags": ["paddy", "disease", "blast", "Tamil Nadu", "Andhra Pradesh"],
    },
    {
        "id": 3,
        "title": "Groundnut Prices Rise 12% Ahead of Festival Season",
        "body": (
            "Groundnut prices at Kurnool mandi have risen to ₹6,200–₹6,450 per quintal, "
            "driven by festive demand and lower arrivals. Traders expect prices to remain "
            "firm for the next 2–3 weeks. Farmers with stock can consider selling now."
        ),
        "category": "📈 Market Update",
        "tags": ["groundnut", "mandi", "price", "Kurnool"],
    },
    {
        "id": 4,
        "title": "PM-KISAN 17th Instalment Released — Check Your Account",
        "body": (
            "The Government of India has released the 17th instalment of PM-KISAN, "
            "transferring ₹2,000 directly to eligible farmers' bank accounts. "
            "Farmers who have not received the amount should verify their Aadhaar-bank "
            "linkage at pmkisan.gov.in or visit the nearest CSC centre."
        ),
        "category": "💰 Government Scheme",
        "tags": ["PM-KISAN", "subsidy", "scheme"],
    },
    {
        "id": 5,
        "title": "Chilli Crop Thrips Infestation Reported in Guntur",
        "body": (
            "Guntur district farmers report heavy thrips attack on chilli crops causing "
            "leaf curling and fruit drop. Agriculture officers recommend Spinosad 45 SC "
            "@ 0.3 ml/litre or Imidacloprid 17.8 SL @ 0.5 ml/litre. "
            "Spray in evening hours to protect pollinators."
        ),
        "category": "🌶️ Pest Alert",
        "tags": ["chilli", "pest", "thrips", "Guntur"],
    },
    {
        "id": 6,
        "title": "Northeast Monsoon to Arrive Early in South India — IMD",
        "body": (
            "The India Meteorological Department (IMD) forecasts an early onset of the "
            "Northeast monsoon over Tamil Nadu and South Andhra Pradesh this year. "
            "Farmers are advised to prepare fields for Rabi sowing and ensure drainage "
            "channels are cleared to prevent waterlogging."
        ),
        "category": "🌧️ Weather Update",
        "tags": ["monsoon", "weather", "Rabi", "Tamil Nadu"],
    },
    {
        "id": 7,
        "title": "Nano Urea: Government Expands Free Distribution to Small Farmers",
        "body": (
            "IFFCO's Nano Urea liquid (500 ml bottle) is now being distributed free to "
            "small and marginal farmers (below 2 acres) through PACS and cooperative "
            "societies. One bottle replaces a 45 kg urea bag for one acre. "
            "Contact your local agriculture office to claim yours."
        ),
        "category": "🌱 Farm Input News",
        "tags": ["fertilizer", "nano urea", "IFFCO", "subsidy"],
    },
    {
        "id": 8,
        "title": "Tomato Prices Crash at Kolar — ₹2 per Kg at Farm Gate",
        "body": (
            "Tomato prices have crashed to ₹2–₹5 per kg at Kolar mandi due to bumper "
            "harvest and excess arrivals. Farmers' associations are urging the government "
            "to intervene with procurement. Cold storage facilities at Krishnagiri are "
            "accepting produce at ₹3 per kg handling charge."
        ),
        "category": "📉 Market Alert",
        "tags": ["tomato", "price", "Kolar", "mandi"],
    },
    {
        "id": 9,
        "title": "Cotton Pink Bollworm Resistance: New BG-III Variety Approved",
        "body": (
            "The Genetic Engineering Appraisal Committee (GEAC) has recommended approval "
            "of Bt Cotton BG-III, which offers resistance to Pink Bollworm (PBW). "
            "PBW has caused up to 30% yield loss in Vidarbha and Telangana this season. "
            "Seeds expected in market from next Kharif season."
        ),
        "category": "🔬 Research & Tech",
        "tags": ["cotton", "bollworm", "BG-III", "Bt cotton"],
    },
    {
        "id": 10,
        "title": "Free Soil Health Card Camp in Nellore District Next Week",
        "body": (
            "The Andhra Pradesh Agriculture Department will conduct a free Soil Health "
            "Card (SHC) camp in Nellore district from Monday to Friday. Farmers can bring "
            "200g soil samples from their field corners for free NPK and micronutrient "
            "testing. Cards will be distributed within 7 days."
        ),
        "category": "🌍 Local Event",
        "tags": ["soil", "health card", "Nellore", "free"],
    },
    {
        "id": 11,
        "title": "Mango Hopper Control: Pre-Flowering Spray Advisory Issued",
        "body": (
            "Agriculture officials advise mango farmers to spray Imidacloprid 200 SL "
            "@ 0.5 ml/litre before flowering to prevent hopper infestation. "
            "Hoppers can destroy up to 80% of the mango crop if not controlled early. "
            "Do not spray during flowering to protect honey bees."
        ),
        "category": "🥭 Crop Advisory",
        "tags": ["mango", "hopper", "pest", "flowering"],
    },
    {
        "id": 12,
        "title": "Drip Irrigation Subsidy: 90% for SC/ST Farmers in AP",
        "body": (
            "Andhra Pradesh government offers up to 90% subsidy on drip irrigation "
            "systems for SC/ST farmers and 75% for other small farmers. "
            "Applications open at horticulture.ap.gov.in. Last date for this season "
            "is end of this month. Water use can be reduced by 40–60% with drip."
        ),
        "category": "💧 Irrigation Scheme",
        "tags": ["drip", "irrigation", "subsidy", "Andhra Pradesh"],
    },
    {
        "id": 13,
        "title": "Wheat Procurement Season Opens — Register at Your APMC Now",
        "body": (
            "The wheat procurement season for Rabi 2024–25 is now open across Punjab, "
            "Haryana, and Madhya Pradesh. Farmers must pre-register their produce at "
            "the APMC portal or the Kisan Suvidhaa app. Procurement will be done at "
            "MSP of ₹2,275 per quintal."
        ),
        "category": "🌾 Procurement",
        "tags": ["wheat", "Rabi", "MSP", "procurement"],
    },
    {
        "id": 14,
        "title": "Zero Budget Natural Farming: 5-Day Training Camp in Tirupati",
        "body": (
            "The AP Natural Farming Mission is conducting a free 5-day residential "
            "training on Zero Budget Natural Farming (ZBNF) at Tirupati from next "
            "Monday. Topics include Jeevamrutha preparation, seed treatment, and "
            "mulching techniques. Register at apzbnf.ap.gov.in."
        ),
        "category": "🎓 Training",
        "tags": ["ZBNF", "natural farming", "Tirupati", "training"],
    },
    {
        "id": 15,
        "title": "Black Pepper Prices Hit 5-Year High at Wayanad Mandi",
        "body": (
            "Black pepper prices have reached ₹620 per kg at Wayanad mandi, the highest "
            "in five years, driven by reduced production in Vietnam and strong domestic "
            "demand. Kerala farmers are advised to hold stock for 2–4 more weeks for "
            "maximum benefit."
        ),
        "category": "📈 Market Update",
        "tags": ["pepper", "spice", "Wayanad", "price"],
    },
]

# ── Disease-specific knowledge chunks for RAG demo ──────────────────
DISEASE_KNOWLEDGE_BASE = [
    {
        "id": "d1",
        "topic": "paddy blast disease",
        "content": (
            "Rice/Paddy Blast (Magnaporthe oryzae): Appears as diamond-shaped lesions "
            "with grey centres and brown borders on leaves. Neck blast causes white/grey "
            "discolouration at panicle neck. Favoured by cool nights (below 20°C), "
            "high humidity (>90%), and excess nitrogen. "
            "Control: Tricyclazole 75 WP @ 0.6 g/litre, or Isoprothiolane 40 EC @ 1.5 ml/litre. "
            "Spray twice at 10-day intervals. Avoid urea top-dressing during disease period."
        ),
        "keywords": ["blast", "paddy", "rice", "lesion", "diamond", "neck", "panicle", "grey spots"],
    },
    {
        "id": "d2",
        "topic": "chilli leaf curl virus",
        "content": (
            "Chilli Leaf Curl (Begomovirus): Leaves curl upward/inward, turn pale yellow-green. "
            "Transmitted by whitefly. Infected plants are stunted with distorted fruits. "
            "Remove and destroy infected plants immediately. "
            "Control whitefly: Imidacloprid 17.8 SL @ 0.5 ml/litre or Thiamethoxam 25 WG @ 0.3 g/litre. "
            "Use yellow sticky traps. Spray neem oil 2% as preventive measure."
        ),
        "keywords": ["chilli", "leaf curl", "yellow", "virus", "whitefly", "stunted", "distorted"],
    },
    {
        "id": "d3",
        "topic": "tomato early blight",
        "content": (
            "Tomato Early Blight (Alternaria solani): Brown-black spots with concentric "
            "rings (target-board pattern) on older leaves. Causes premature defoliation. "
            "Favoured by high temperature (24–29°C) and alternating wet-dry conditions. "
            "Control: Mancozeb 75 WP @ 2.5 g/litre or Chlorothalonil 75 WP @ 2 g/litre. "
            "Remove infected lower leaves. Spray at 7-day intervals. Avoid overhead irrigation."
        ),
        "keywords": ["tomato", "blight", "brown spots", "rings", "target", "leaf drop", "alternaria"],
    },
    {
        "id": "d4",
        "topic": "cotton pink bollworm",
        "content": (
            "Pink Bollworm (Pectinophora gossypiella): Larva enters cotton boll, feeds on seeds. "
            "Signs: small entry holes on bolls, rosy-pink larvae inside, stained lint. "
            "Heavy infestation causes 30–50% yield loss. "
            "Control: Emamectin benzoate 5 SG @ 0.4 g/litre or Spinosad 45 SC @ 0.3 ml/litre. "
            "Install pheromone traps (5 per acre). Collect and destroy fallen bolls daily."
        ),
        "keywords": ["cotton", "pink bollworm", "boll", "holes", "larvae", "pink", "bollworm"],
    },
    {
        "id": "d5",
        "topic": "groundnut leaf spot",
        "content": (
            "Groundnut Leaf Spot (Cercospora arachidicola / Phaeoisariopsis personata): "
            "Early leaf spot: circular brown spots with yellow halo on upper leaf surface. "
            "Late leaf spot: darker spots on lower surface. Causes 30–70% yield reduction if unchecked. "
            "Control: Tebuconazole 25 EC @ 1 ml/litre or Mancozeb 75 WP @ 2.5 g/litre. "
            "Spray at 15-day intervals from 30 days after sowing. Collect and burn infected leaves."
        ),
        "keywords": ["groundnut", "leaf spot", "brown", "cercospora", "yellow halo", "spots"],
    },
    {
        "id": "d6",
        "topic": "mango anthracnose",
        "content": (
            "Mango Anthracnose (Colletotrichum gloeosporioides): Black-brown irregular spots "
            "on leaves, flowers, and fruits. Causes blossom blight and fruit rot. "
            "Post-harvest fruit develops black sunken spots. Favoured by rains during flowering. "
            "Control: Carbendazim 50 WP @ 1 g/litre or Copper oxychloride 50 WP @ 3 g/litre. "
            "Spray at bud initiation, full bloom, and fruit set stages."
        ),
        "keywords": ["mango", "anthracnose", "black spots", "flower blight", "fruit rot", "colletotrichum"],
    },
    {
        "id": "d7",
        "topic": "banana panama wilt",
        "content": (
            "Banana Panama Wilt (Fusarium oxysporum f.sp. cubense): Yellowing of older outer "
            "leaves progressing inward. Pseudostem shows reddish-brown discolouration when cut. "
            "No chemical cure — cultural management only. "
            "Prevention: Use Fusarium-resistant varieties (Grand Naine, FHIA hybrids). "
            "Remove and destroy infected mats. Drench soil with Trichoderma viride @ 10 g/litre. "
            "Do not plant banana in same field for at least 3 years."
        ),
        "keywords": ["banana", "wilt", "panama", "yellow", "fusarium", "pseudostem", "browning"],
    },
    {
        "id": "d8",
        "topic": "general yellowing nitrogen deficiency",
        "content": (
            "Nitrogen Deficiency in crops: Uniform yellowing of older lower leaves, starting "
            "from leaf tips. Plant growth is stunted and pale. Common in sandy/light soils. "
            "Correction: Apply urea top-dressing @ 25–30 kg/acre or liquid urea (Nano Urea) "
            "foliar spray @ 2.5 ml/litre water. Split nitrogen application reduces losses. "
            "Combine with organic matter (FYM/compost) to improve soil nitrogen retention."
        ),
        "keywords": ["yellow leaves", "nitrogen", "deficiency", "pale", "stunted", "yellowing"],
    },
]


def get_todays_news(max_items: int = 5, seed: int = None) -> list[dict]:
    """
    Return today's top farming news items.
    Uses today's date as random seed so the same items show all day.
    """
    today = date.today()
    if seed is None:
        seed = today.toordinal()
    rng = random.Random(seed)
    shuffled = _NEWS_ITEMS.copy()
    rng.shuffle(shuffled)
    return shuffled[:max_items]


def search_disease_knowledge(query_text: str, top_k: int = 3) -> list[dict]:
    """
    Simple keyword-based RAG simulation for disease knowledge.
    Returns the most relevant disease knowledge chunks for the query.
    In production this would be replaced by Supabase pgvector similarity search.
    """
    query_lower = query_text.lower()
    scored = []
    for chunk in DISEASE_KNOWLEDGE_BASE:
        score = 0
        # Score by keyword matches
        for kw in chunk["keywords"]:
            if kw.lower() in query_lower:
                score += 2
        # Score by topic words
        for word in chunk["topic"].split():
            if word in query_lower:
                score += 1
        if score > 0:
            scored.append((score, chunk))

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scored[:top_k]]


def format_news_text(news_items: list[dict]) -> str:
    """Format news items into a readable Telegram message."""
    today_str = date.today().strftime("%B %d, %Y")
    lines = [
        f"📰 *Agrithm Daily Farming News*",
        f"📅 {today_str}",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for i, item in enumerate(news_items, 1):
        lines.append(f"{item['category']}")
        lines.append(f"*{i}. {item['title']}*")
        lines.append(item["body"])
        lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append("_Tap '⏰ Set Alarm' to schedule your daily news digest._")
    return "\n".join(lines)