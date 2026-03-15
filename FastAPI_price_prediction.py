"""
routes/price.py
───────────────
Price prediction API endpoints.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

from core.price_engine.predict import predict_price, format_prediction_message

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class PricePredictRequest(BaseModel):
    crop: str              = Field(..., example="tomato")
    district: str          = Field(..., example="Chennai")
    state: str             = Field("Tamil Nadu", example="Tamil Nadu")
    current_price: Optional[float] = Field(None, example=42.5, description="Current modal price ₹/kg")
    language: str          = Field("en", example="ta", description="Response language code")


class PricePredictResponse(BaseModel):
    crop: str
    district: str
    state: str
    price_7d: float
    price_14d: float
    price_30d: float
    unit: str
    confidence: str
    forecast_date: str
    advisory_message: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/predict", response_model=PricePredictResponse)
async def predict(req: PricePredictRequest):
    """
    Predict crop prices for 7, 14, and 30 days ahead.
    Returns structured prediction + formatted advisory message.
    """
    try:
        pred = predict_price(
            crop=req.crop,
            district=req.district,
            state=req.state,
            current_price=req.current_price,
        )
        pred["advisory_message"] = format_prediction_message(pred, req.language)
        return PricePredictResponse(**pred)

    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Price model not found. Please run train_model.py first."
        )
    except Exception as e:
        logger.error(f"Price prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/crops")
async def list_crops():
    """List all supported crops."""
    crops = [
        "tomato", "onion", "potato", "rice", "wheat", "sugarcane",
        "cotton", "groundnut", "brinjal", "ladyfinger", "drumstick",
        "banana", "coconut", "turmeric", "chilli", "tamarind",
        "mango", "pomegranate", "grapes", "cauliflower", "cabbage",
        "beans", "peas", "garlic", "ginger", "maize", "jowar", "bajra",
    ]
    return {"crops": sorted(crops), "count": len(crops)}


@router.get("/districts")
async def list_districts(state: str = "Tamil Nadu"):
    """List supported districts for a state."""
    districts_map = {
        "Tamil Nadu": [
            "Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem",
            "Tirunelveli", "Erode", "Vellore", "Thoothukudi", "Dindigul",
            "Thanjavur", "Nagapattinam", "Cuddalore", "Villupuram",
            "Kancheepuram", "Tiruvallur", "Dharmapuri", "Krishnagiri",
            "Namakkal", "Perambalur", "Ariyalur", "Karur", "Tirupur",
            "The Nilgiris", "Sivaganga", "Virudhunagar", "Ramanathapuram",
            "Pudukkottai", "Theni", "Tiruvannamalai", "Kanyakumari",
            "Kallakurichi",
        ],
        "Andhra Pradesh": [
            "Visakhapatnam", "Vijayawada", "Guntur", "Kurnool", "Tirupati",
            "Nellore", "Kakinada", "Rajahmundry", "Kadapa", "Anantapur",
            "Ongole", "Srikakulam", "Vizianagaram",
        ],
    }
    return {
        "state": state,
        "districts": districts_map.get(state, []),
    }
