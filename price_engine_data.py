"""
data_engineering.py
───────────────────
Mandi price data preprocessing, pivot transformation, and feature engineering
for the Agrithm price prediction pipeline.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Tuple


RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)


# ── Feature Engineering ───────────────────────────────────────────────────────

def load_raw_data(filepath: str) -> pd.DataFrame:
    """Load raw mandi CSV from Agmarknet or synthetic source."""
    df = pd.read_csv(filepath, parse_dates=["date"])
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    logger.info(f"Loaded {len(df):,} rows from {filepath}")
    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Drop nulls, fix dtypes, remove outliers."""
    df = df.dropna(subset=["crop", "district", "modal_price", "date"])
    df["modal_price"] = pd.to_numeric(df["modal_price"], errors="coerce")
    df["min_price"]   = pd.to_numeric(df.get("min_price", df["modal_price"]), errors="coerce")
    df["max_price"]   = pd.to_numeric(df.get("max_price", df["modal_price"]), errors="coerce")

    # Remove extreme outliers (>3 IQR)
    Q1, Q3 = df["modal_price"].quantile([0.25, 0.75])
    IQR = Q3 - Q1
    df = df[df["modal_price"].between(Q1 - 3 * IQR, Q3 + 3 * IQR)]

    df["crop"]     = df["crop"].str.strip().str.lower()
    df["district"] = df["district"].str.strip().str.title()
    df["state"]    = df.get("state", "Tamil Nadu")

    logger.info(f"After cleaning: {len(df):,} rows")
    return df.reset_index(drop=True)


def add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add time-based features for seasonality."""
    df["year"]         = df["date"].dt.year
    df["month"]        = df["date"].dt.month
    df["week"]         = df["date"].dt.isocalendar().week.astype(int)
    df["day_of_year"]  = df["date"].dt.dayofyear
    df["quarter"]      = df["date"].dt.quarter

    # Cyclical encoding for month (prevents Jan=1, Dec=12 discontinuity)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # Harvest season flag (Kharif: Jun–Nov, Rabi: Nov–Apr)
    df["is_kharif_season"] = df["month"].isin([6, 7, 8, 9, 10, 11]).astype(int)
    df["is_rabi_season"]   = df["month"].isin([11, 12, 1, 2, 3, 4]).astype(int)

    return df


def add_lag_features(df: pd.DataFrame, lags: list = [7, 14, 30]) -> pd.DataFrame:
    """Add lagged price features per crop-district pair."""
    df = df.sort_values(["crop", "district", "date"])
    grp = df.groupby(["crop", "district"])["modal_price"]

    for lag in lags:
        df[f"price_lag_{lag}"] = grp.shift(lag)
        df[f"price_roll_mean_{lag}"] = grp.shift(1).transform(
            lambda x: x.rolling(lag, min_periods=1).mean()
        )
        df[f"price_roll_std_{lag}"] = grp.shift(1).transform(
            lambda x: x.rolling(lag, min_periods=1).std().fillna(0)
        )

    logger.info(f"Added lag features: {lags}")
    return df


def pivot_transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot from long format to wide format for multi-output regression.
    Creates target columns: price_7d, price_14d, price_30d (future prices).
    """
    df = df.sort_values(["crop", "district", "date"])
    grp = df.groupby(["crop", "district"])["modal_price"]

    df["price_7d"]  = grp.shift(-7)
    df["price_14d"] = grp.shift(-14)
    df["price_30d"] = grp.shift(-30)

    df = df.dropna(subset=["price_7d", "price_14d", "price_30d"])
    logger.info(f"After pivot transform: {len(df):,} rows with future targets")
    return df


def encode_categoricals(df: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """Label-encode crop and district columns. Returns df + encoding maps."""
    from sklearn.preprocessing import LabelEncoder

    encoders = {}
    for col in ["crop", "district", "state"]:
        if col in df.columns:
            le = LabelEncoder()
            df[f"{col}_enc"] = le.fit_transform(df[col].astype(str))
            encoders[col] = {cls: idx for idx, cls in enumerate(le.classes_)}

    return df, encoders


def build_feature_matrix(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Return X (features) and y (targets) ready for model training."""
    feature_cols = [
        "crop_enc", "district_enc",
        "month", "week", "quarter", "day_of_year",
        "month_sin", "month_cos",
        "is_kharif_season", "is_rabi_season",
        "price_lag_7", "price_lag_14", "price_lag_30",
        "price_roll_mean_7", "price_roll_mean_14", "price_roll_mean_30",
        "price_roll_std_7", "price_roll_std_14", "price_roll_std_30",
        "modal_price",
    ]
    target_cols = ["price_7d", "price_14d", "price_30d"]

    available_features = [c for c in feature_cols if c in df.columns]
    X = df[available_features].fillna(df[available_features].median())
    y = df[target_cols]

    logger.info(f"Feature matrix: {X.shape}, Targets: {y.shape}")
    return X, y


# ── Full Pipeline ─────────────────────────────────────────────────────────────

def run_pipeline(input_csv: str, output_prefix: str = "tamilnadu") -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    """End-to-end data engineering pipeline."""
    df = load_raw_data(input_csv)
    df = clean_data(df)
    df = add_temporal_features(df)
    df = add_lag_features(df)
    df = pivot_transform(df)
    df, encoders = encode_categoricals(df)
    X, y = build_feature_matrix(df)

    X.to_csv(PROCESSED_DIR / f"{output_prefix}_X.csv", index=False)
    y.to_csv(PROCESSED_DIR / f"{output_prefix}_y.csv", index=False)
    logger.success(f"Pipeline complete. Saved to {PROCESSED_DIR}/")

    return X, y, encoders


if __name__ == "__main__":
    run_pipeline("data/raw/tamilnadu_mandis.csv")
