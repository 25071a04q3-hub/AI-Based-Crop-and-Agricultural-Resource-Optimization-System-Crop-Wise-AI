"""
FarmTwin — Probabilistic Crop Yield Prediction Engine.

This module implements the probabilistic yield estimation layer of FarmTwin.
It is designed to estimate agricultural yield distributions (P10 pessimistic,
P50 median/expected, P90 optimistic in tonnes/ha) under specific farm parcel conditions.

DATASET DECISION GATE (CRITICAL RULE):
--------------------------------------------------------------------------------
Agricultural yield models must ONLY be trained on authentic historical production data.
In accordance with Rule 1 (No fake AI) and Phase 4 specifications:
- The 2200-row suitability dataset (crop_recommendation.csv) contains NO yield observations.
- The 28-row legacy file (archive/yield_data.csv) is a synthetic toy sample with only 1
  observation for 19 crops, with no temporal (year) or spatial (location) dimensions.
- If no valid historical yield dataset is present, model training is SAFELY BLOCKED.
- No fake or randomly manufactured P10/P50/P90 numbers will ever be generated.
--------------------------------------------------------------------------------

IMPORTANT ARCHITECTURAL RULE:
This module must remain completely independent of UI/Streamlit frameworks.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from engine.profile import FarmProfile

# ==========================================
# FILE PATHS & CONSTANTS
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
PRIMARY_YIELD_DATA_PATH = BASE_DIR / "data" / "raw" / "historical_yield.csv"
LEGACY_YIELD_DATA_PATH = BASE_DIR / "archive" / "yield_data.csv"

# Minimum criteria for a scientifically defensible historical agricultural yield dataset
MIN_TOTAL_SAMPLES_THRESHOLD = 200
MIN_SAMPLES_PER_CROP_THRESHOLD = 15


class YieldPredictionResult(BaseModel):
    """
    Structured outcome contract for probabilistic crop yield prediction.
    """
    crop_name: str = Field(description="Target crop name")
    status: str = Field(
        description="Status code: 'AVAILABLE' or 'BLOCKED_NO_HISTORICAL_DATASET'"
    )
    p10_yield_t_per_ha: Optional[float] = Field(
        default=None, description="Pessimistic / lower bound yield estimate in tonnes/ha (10th percentile)"
    )
    p50_yield_t_per_ha: Optional[float] = Field(
        default=None, description="Median / expected yield estimate in tonnes/ha (50th percentile)"
    )
    p90_yield_t_per_ha: Optional[float] = Field(
        default=None, description="Optimistic / upper bound yield estimate in tonnes/ha (90th percentile)"
    )
    farm_yield_p10_tonnes: Optional[float] = Field(
        default=None, description="Total farm-level lower production in metric tonnes"
    )
    farm_yield_p50_tonnes: Optional[float] = Field(
        default=None, description="Total farm-level median production in metric tonnes"
    )
    farm_yield_p90_tonnes: Optional[float] = Field(
        default=None, description="Total farm-level upper production in metric tonnes"
    )
    unit: str = Field(default="tonnes_per_hectare", description="Yield measurement unit")
    land_area_ha: float = Field(default=0.0, description="Normalized farm land area in hectares")
    prediction_interval_width: Optional[float] = Field(
        default=None, description="P90 - P10 yield spread (tonnes/ha)"
    )
    message: str = Field(default="", description="Diagnostic status or explanation message")
    methodology: str = Field(default="", description="Description of the statistical/ML method used")
    supporting_metrics: Dict[str, Any] = Field(default_factory=dict, description="Model evaluation metrics if available")


def calculate_farm_yield(yield_t_per_ha: float, land_area_ha: float) -> float:
    """
    Calculates total expected farm production volume in metric tonnes:
    Total Production (t) = Yield (t/ha) * Cultivated Area (ha)
    """
    if yield_t_per_ha < 0 or land_area_ha < 0:
        raise ValueError("Yield and land area must be non-negative values.")
    return round(float(yield_t_per_ha * land_area_ha), 4)


def audit_and_validate_yield_dataset(
    csv_path: Optional[Path] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Performs a strict data quality and sufficiency audit on potential yield datasets.
    Rejects missing files, toy samples (e.g. 28-row legacy files), and files lacking
    valid historical yield columns or adequate observations per crop.
    """
    candidate_path = Path(csv_path) if csv_path else None

    # Check candidate paths in priority order
    if candidate_path is None:
        if PRIMARY_YIELD_DATA_PATH.exists():
            candidate_path = PRIMARY_YIELD_DATA_PATH
        elif LEGACY_YIELD_DATA_PATH.exists():
            candidate_path = LEGACY_YIELD_DATA_PATH

    if candidate_path is None or not candidate_path.exists():
        return False, {
            "dataset_found": False,
            "filename": None,
            "reason": "No historical yield dataset file found in data/raw/ or archive/.",
            "is_valid": False,
        }

    try:
        df = pd.read_csv(candidate_path)
    except Exception as e:
        return False, {
            "dataset_found": True,
            "filename": str(candidate_path.name),
            "reason": f"Failed to parse CSV file: {str(e)}",
            "is_valid": False,
        }

    # Identify potential target column
    possible_target_cols = ["yield_t_per_ha", "yield", "yield_tonnes_per_hectare", "production_t_ha"]
    target_col = next((col for col in possible_target_cols if col in df.columns), None)

    crop_col = next((col for col in ["crop", "label", "crop_name"] if col in df.columns), None)

    audit: Dict[str, Any] = {
        "dataset_found": True,
        "filename": str(candidate_path.name),
        "filepath": str(candidate_path),
        "rows": len(df),
        "columns": list(df.columns),
        "target_col": target_col,
        "crop_col": crop_col,
        "missing_values": int(df.isnull().sum().sum()),
        "duplicates": int(df.duplicated().sum()),
        "unique_crops": df[crop_col].nunique() if crop_col else 0,
        "crops": sorted(df[crop_col].unique().tolist()) if crop_col else [],
        "years": sorted(df["year"].unique().tolist()) if "year" in df.columns else "None (not recorded)",
        "locations": sorted(df["location"].unique().tolist()) if "location" in df.columns else "None (not recorded)",
        "units": "tonnes_per_hectare" if target_col == "yield_t_per_ha" else "unknown",
        "is_valid": False,
        "disqualification_reasons": [],
    }

    # Validation Gate 1: Target column presence
    if not target_col:
        audit["disqualification_reasons"].append(
            "Missing recognized target yield column (e.g. 'yield_t_per_ha')."
        )

    # Validation Gate 2: Crop column presence
    if not crop_col:
        audit["disqualification_reasons"].append(
            "Missing recognized crop identifier column (e.g. 'crop')."
        )

    # Validation Gate 3: Sample size sufficiency check
    if len(df) < MIN_TOTAL_SAMPLES_THRESHOLD:
        audit["disqualification_reasons"].append(
            f"Critically inadequate sample count ({len(df)} rows). "
            f"Minimum required for statistical quantile estimation is {MIN_TOTAL_SAMPLES_THRESHOLD} rows."
        )

    # Validation Gate 4: Sufficient samples per crop
    if crop_col and target_col:
        counts = df[crop_col].value_counts()
        under_represented = counts[counts < MIN_SAMPLES_PER_CROP_THRESHOLD]
        if not under_represented.empty:
            audit["disqualification_reasons"].append(
                f"{len(under_represented)} crops contain fewer than {MIN_SAMPLES_PER_CROP_THRESHOLD} observations. "
                f"(Example: 19 crops in legacy file contain only 1 sample each)."
            )

    # Validation Gate 5: Temporal and spatial dimension presence
    if "year" not in df.columns and "date" not in df.columns:
        audit["disqualification_reasons"].append(
            "Dataset lacks temporal time-series records (no 'year' or 'date' column) for multi-year yield variance."
        )

    audit["is_valid"] = len(audit["disqualification_reasons"]) == 0
    return audit["is_valid"], audit


# ==========================================
# QUANTILE REGRESSION MODEL ARCHITECTURE
# ==========================================
_YIELD_MODEL_CACHE: Optional[Tuple[Dict[str, Any], Dict[str, Any]]] = None


def train_quantile_yield_models(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str = "yield_t_per_ha",
    random_state: int = 42
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Trains technically defensible quantile regression models (P10, P50, P90)
    using GradientBoostingRegressor with pinball loss (alpha = 0.10, 0.50, 0.90),
    along with an MSE mean regressor for standard regression metrics (MAE, RMSE, R²).

    Enforces non-crossing quantile calibration: P10 <= P50 <= P90.
    """
    X = df[feature_cols].copy()
    y = df[target_col].copy()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=random_state
    )

    # 1. P10 Quantile Model (Lower bound - 10th percentile)
    model_p10 = GradientBoostingRegressor(
        loss="quantile", alpha=0.10, n_estimators=100, max_depth=3, random_state=random_state
    )
    model_p10.fit(X_train, y_train)

    # 2. P50 Quantile Model (Median - 50th percentile)
    model_p50 = GradientBoostingRegressor(
        loss="quantile", alpha=0.50, n_estimators=100, max_depth=3, random_state=random_state
    )
    model_p50.fit(X_train, y_train)

    # 3. P90 Quantile Model (Upper bound - 90th percentile)
    model_p90 = GradientBoostingRegressor(
        loss="quantile", alpha=0.90, n_estimators=100, max_depth=3, random_state=random_state
    )
    model_p90.fit(X_train, y_train)

    # 4. Standard Regressor for point metrics
    model_mean = GradientBoostingRegressor(
        loss="squared_error", n_estimators=100, max_depth=3, random_state=random_state
    )
    model_mean.fit(X_train, y_train)

    # Evaluation
    preds_mean = model_mean.predict(X_test)
    preds_p10 = model_p10.predict(X_test)
    preds_p50 = model_p50.predict(X_test)
    preds_p90 = model_p90.predict(X_test)

    # Pinball / Quantile loss calculations
    def pinball_loss(y_true, y_pred, alpha):
        diff = y_true - y_pred
        return float(np.mean(np.maximum(alpha * diff, (alpha - 1.0) * diff)))

    mae = float(mean_absolute_error(y_test, preds_mean))
    rmse = float(np.sqrt(mean_squared_error(y_test, preds_mean)))
    r2 = float(r2_score(y_test, preds_mean))

    metrics = {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "r2": round(r2, 4),
        "quantile_loss_p10": round(pinball_loss(y_test, preds_p10, 0.10), 4),
        "quantile_loss_p50": round(pinball_loss(y_test, preds_p50, 0.50), 4),
        "quantile_loss_p90": round(pinball_loss(y_test, preds_p90, 0.90), 4),
        "test_samples": len(y_test),
        "random_state": random_state,
    }

    models_bundle = {
        "p10": model_p10,
        "p50": model_p50,
        "p90": model_p90,
        "mean": model_mean,
        "feature_cols": feature_cols,
    }

    return models_bundle, metrics


def get_or_train_yield_models(
    force_retrain: bool = False
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    """
    Decision Gate Handler:
    - Audits available yield datasets.
    - If valid historical data is found (CASE A), trains/loads quantile models.
    - If no valid historical data is found (CASE B), SAFELY BLOCKS training and returns None.
    """
    global _YIELD_MODEL_CACHE
    if _YIELD_MODEL_CACHE is not None and not force_retrain:
        return _YIELD_MODEL_CACHE

    is_valid, audit = audit_and_validate_yield_dataset()

    if not is_valid:
        # CASE B: No valid historical yield dataset exists -> Safely block
        status_info = {
            "status": "BLOCKED_NO_HISTORICAL_DATASET",
            "message": (
                "Phase 4 model training is blocked because no valid historical yield dataset was found. "
                "Available files do not meet the minimum sample size, historical time-series, or multi-location "
                "standards required for technically defensible quantile regression."
            ),
            "audit": audit,
        }
        _YIELD_MODEL_CACHE = (None, status_info)
        return _YIELD_MODEL_CACHE

    # CASE A: A valid dataset is supplied
    df = pd.read_csv(audit["filepath"])
    # One-hot encode crop if present
    df_encoded = pd.get_dummies(df, columns=[audit["crop_col"]], drop_first=False)
    target = audit["target_col"]
    features = [c for c in df_encoded.columns if c != target and c not in ["year", "location", "date"]]

    models_bundle, metrics = train_quantile_yield_models(
        df_encoded, feature_cols=features, target_col=target
    )
    _YIELD_MODEL_CACHE = (models_bundle, {"status": "AVAILABLE", "metrics": metrics, "audit": audit})
    return _YIELD_MODEL_CACHE


# ==========================================
# PREDICTION & ADAPTER API
# ==========================================
def predict_yield(
    profile: FarmProfile,
    crop_name: str
) -> YieldPredictionResult:
    """
    Primary interface for probabilistic crop yield prediction.
    Accepts a validated FarmProfile and a target crop identifier.

    If training is blocked due to dataset absence (CASE B):
    Returns a structured YieldPredictionResult with status 'BLOCKED_NO_HISTORICAL_DATASET'
    and None for yield values, strictly refusing to fabricate fake numbers.
    """
    if not isinstance(profile, FarmProfile):
        raise TypeError(f"Expected FarmProfile instance, got {type(profile).__name__}")

    clean_crop = crop_name.strip().lower() if isinstance(crop_name, str) else ""
    if not clean_crop:
        raise ValueError("Target crop name must be a non-empty string.")

    land_ha = float(profile.land_area_ha)

    models_bundle, status_info = get_or_train_yield_models()

    # DECISION GATE: Check if model is blocked
    if models_bundle is None:
        return YieldPredictionResult(
            crop_name=clean_crop,
            status="BLOCKED_NO_HISTORICAL_DATASET",
            p10_yield_t_per_ha=None,
            p50_yield_t_per_ha=None,
            p90_yield_t_per_ha=None,
            farm_yield_p10_tonnes=None,
            farm_yield_p50_tonnes=None,
            farm_yield_p90_tonnes=None,
            unit="tonnes_per_hectare",
            land_area_ha=land_ha,
            message=(
                "Probabilistic yield prediction is not yet available. "
                "A validated historical yield dataset is required before the model can be trained."
            ),
            methodology=(
                "Architecture ready for Quantile Gradient Boosting (loss='quantile', alpha=0.10, 0.50, 0.90). "
                "Currently blocked to prevent scientific fabrication."
            ),
            supporting_metrics=status_info
        )

    # When valid model is present (CASE A)
    feature_cols = models_bundle["feature_cols"]
    row_data = {col: 0.0 for col in feature_cols}

    # Map profile features
    row_data["N"] = float(profile.nitrogen_n_kg_ha)
    row_data["P"] = float(profile.phosphorus_p_kg_ha)
    row_data["K"] = float(profile.potassium_k_kg_ha)
    row_data["temperature"] = float(profile.temperature_c)
    row_data["humidity"] = float(profile.humidity_percent)
    row_data["ph"] = float(profile.ph)
    row_data["rainfall"] = float(profile.rainfall_mm)

    crop_col_name = f"crop_{clean_crop}"
    if crop_col_name in row_data:
        row_data[crop_col_name] = 1.0

    X_in = pd.DataFrame([row_data])[feature_cols]

    raw_p10 = float(models_bundle["p10"].predict(X_in)[0])
    raw_p50 = float(models_bundle["p50"].predict(X_in)[0])
    raw_p90 = float(models_bundle["p90"].predict(X_in)[0])

    # Enforce non-crossing and physical non-negativity: 0 <= P10 <= P50 <= P90
    p10 = max(0.05, round(raw_p10, 2))
    p50 = max(p10, round(raw_p50, 2))
    p90 = max(p50, round(raw_p90, 2))

    farm_p10 = calculate_farm_yield(p10, land_ha)
    farm_p50 = calculate_farm_yield(p50, land_ha)
    farm_p90 = calculate_farm_yield(p90, land_ha)

    return YieldPredictionResult(
        crop_name=clean_crop,
        status="AVAILABLE",
        p10_yield_t_per_ha=p10,
        p50_yield_t_per_ha=p50,
        p90_yield_t_per_ha=p90,
        farm_yield_p10_tonnes=farm_p10,
        farm_yield_p50_tonnes=farm_p50,
        farm_yield_p90_tonnes=farm_p90,
        unit="tonnes_per_hectare",
        land_area_ha=land_ha,
        prediction_interval_width=round(p90 - p10, 2),
        message=f"Estimated yield for {clean_crop.capitalize()} under observed soil and weather conditions.",
        methodology="Quantile Gradient Boosting (alpha=0.10, 0.50, 0.90) with monotonic non-crossing calibration.",
        supporting_metrics=status_info.get("metrics", {})
    )
