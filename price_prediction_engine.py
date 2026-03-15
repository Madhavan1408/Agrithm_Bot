"""
train_model.py
──────────────
Train XGBoost multi-output crop price forecasting model.
Outputs: trained model artifact + encoder maps saved to models/
"""

import json
import joblib
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sklearn.model_selection import train_test_split
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor

from data_engineering import run_pipeline

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


# ── Model Definition ──────────────────────────────────────────────────────────

def build_model() -> MultiOutputRegressor:
    base = XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1,
        tree_method="hist",
    )
    return MultiOutputRegressor(base, n_jobs=-1)


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(model, X_test: pd.DataFrame, y_test: pd.DataFrame) -> dict:
    y_pred = model.predict(X_test)
    targets = y_test.columns.tolist()
    metrics = {}

    for i, target in enumerate(targets):
        mae  = mean_absolute_error(y_test.iloc[:, i], y_pred[:, i])
        rmse = np.sqrt(mean_squared_error(y_test.iloc[:, i], y_pred[:, i]))
        r2   = r2_score(y_test.iloc[:, i], y_pred[:, i])
        metrics[target] = {"MAE": round(mae, 2), "RMSE": round(rmse, 2), "R2": round(r2, 4)}
        logger.info(f"{target:12s} → MAE: ₹{mae:.2f}/kg  RMSE: ₹{rmse:.2f}/kg  R²: {r2:.4f}")

    return metrics


# ── Training Pipeline ─────────────────────────────────────────────────────────

def train(input_csv: str = "data/raw/tamilnadu_mandis.csv"):
    logger.info("Starting Agrithm price model training...")

    X, y, encoders = run_pipeline(input_csv)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, shuffle=True
    )
    logger.info(f"Train: {len(X_train):,} | Test: {len(X_test):,}")

    model = build_model()
    logger.info("Fitting XGBoost multi-output model...")
    model.fit(X_train, y_train)

    logger.info("Evaluating...")
    metrics = evaluate(model, X_test, y_test)

    # Save artifacts
    joblib.dump(model, MODELS_DIR / "price_model.joblib")
    with open(MODELS_DIR / "encoders.json", "w") as f:
        json.dump(encoders, f, ensure_ascii=False, indent=2)
    with open(MODELS_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Save feature column order (required for inference)
    feature_cols = X_train.columns.tolist()
    with open(MODELS_DIR / "feature_cols.json", "w") as f:
        json.dump(feature_cols, f)

    logger.success(f"Model saved to {MODELS_DIR}/price_model.joblib")
    return model, metrics


if __name__ == "__main__":
    train()
