"""
predict.py
──────────
Inference interface for the trained XGBoost price forecasting model.
Used by FastAPI routes and the bot handlers.
"""

import json
import datetime
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from loguru import logger

MODELS_DIR = Path("models")

_model = None
_encoders = None
_feature_cols = None


def _load_artifacts():
    global _model, _encoders, _feature_cols
    if _model is None:
        _model       = joblib.load(MODELS_DIR / "price_model.joblib")
        _encoders    = json.loads((MODELS_DIR / "encoders.json").read_text())
        _feature_cols = json.loads((MODELS_DIR / "feature_cols.json").read_text())
        logger.info("Price model artifacts loaded.")


def _encode(value: str, mapping: dict, default: int = 0) -> int:
    return mapping.get(value.strip().lower(), default)


def _build_input_row(
    crop: str,
    district: str,
    state: str = "Tamil Nadu",
    current_price: Optional[float] = None,
    reference_date: Optional[datetime.date] = None,
) -> pd.DataFrame:
    _load_artifacts()

    date = reference_date or datetime.date.today()
    month = date.month
    week = date.isocalendar().week
    doy = date.timetuple().tm_yday
    quarter = (month - 1) // 3 + 1

    row = {
        "crop_enc":     _encode(crop,     _encoders.get("crop", {})),
        "district_enc": _encode(district, _encoders.get("district", {})),
        "month":        month,
        "week":         week,
        "quarter":      quarter,
        "day_of_year":  doy,
        "month_sin":    np.sin(2 * np.pi * month / 12),
        "month_cos":    np.cos(2 * np.pi * month / 12),
        "is_kharif_season": int(month in [6, 7, 8, 9, 10, 11]),
        "is_rabi_season":   int(month in [11, 12, 1, 2, 3, 4]),
        "modal_price":  current_price or 0.0,
    }

    # Fill lag features with current price as best estimate
    for lag in [7, 14, 30]:
        row[f"price_lag_{lag}"]       = current_price or 0.0
        row[f"price_roll_mean_{lag}"] = current_price or 0.0
        row[f"price_roll_std_{lag}"]  = 0.0

    df = pd.DataFrame([row])
    # Align columns to training order
    for col in _feature_cols:
        if col not in df.columns:
            df[col] = 0.0
    return df[_feature_cols]


def predict_price(
    crop: str,
    district: str,
    state: str = "Tamil Nadu",
    current_price: Optional[float] = None,
    reference_date: Optional[datetime.date] = None,
) -> dict:
    """
    Predict crop prices for 7, 14, and 30 days ahead.

    Returns:
        {
          "crop": "tomato",
          "district": "Chennai",
          "price_7d":  45.20,
          "price_14d": 48.50,
          "price_30d": 52.80,
          "unit": "₹/kg",
          "confidence": "moderate"
        }
    """
    _load_artifacts()
    X = _build_input_row(crop, district, state, current_price, reference_date)
    preds = _model.predict(X)[0]

    result = {
        "crop":       crop.title(),
        "district":   district.title(),
        "state":      state,
        "price_7d":   round(float(preds[0]), 2),
        "price_14d":  round(float(preds[1]), 2),
        "price_30d":  round(float(preds[2]), 2),
        "unit":       "₹/kg",
        "confidence": _confidence_label(preds),
        "forecast_date": str(reference_date or datetime.date.today()),
    }
    logger.debug(f"Prediction for {crop}/{district}: {result}")
    return result


def _confidence_label(preds) -> str:
    spread = max(preds) - min(preds)
    if spread < 5:
        return "high"
    elif spread < 15:
        return "moderate"
    return "low"


def format_prediction_message(pred: dict, language: str = "en") -> str:
    """Format prediction result as a readable advisory message."""
    templates = {
        "en": (
            f"📊 Price Forecast for {pred['crop']} in {pred['district']}:\n"
            f"  • In 7 days:  ₹{pred['price_7d']}/kg\n"
            f"  • In 14 days: ₹{pred['price_14d']}/kg\n"
            f"  • In 30 days: ₹{pred['price_30d']}/kg\n"
            f"Confidence: {pred['confidence'].title()}\n"
            f"💡 Best time to sell: {'now' if pred['price_7d'] >= pred['price_30d'] else 'wait 30 days'}"
        ),
        "ta": (
            f"📊 {pred['crop']} விலை முன்னறிவிப்பு — {pred['district']}:\n"
            f"  • 7 நாட்களில்:  ₹{pred['price_7d']}/கிலோ\n"
            f"  • 14 நாட்களில்: ₹{pred['price_14d']}/கிலோ\n"
            f"  • 30 நாட்களில்: ₹{pred['price_30d']}/கிலோ\n"
            f"💡 விற்க சிறந்த நேரம்: {'இப்போது' if pred['price_7d'] >= pred['price_30d'] else '30 நாட்கள் காத்திருங்கள்'}"
        ),
        "hi": (
            f"📊 {pred['crop']} का मूल्य पूर्वानुमान — {pred['district']}:\n"
            f"  • 7 दिनों में:  ₹{pred['price_7d']}/किलो\n"
            f"  • 14 दिनों में: ₹{pred['price_14d']}/किलो\n"
            f"  • 30 दिनों में: ₹{pred['price_30d']}/किलो\n"
            f"💡 बेचने का सबसे अच्छा समय: {'अभी' if pred['price_7d'] >= pred['price_30d'] else '30 दिन प्रतीक्षा करें'}"
        ),
    }
    return templates.get(language, templates["en"])
