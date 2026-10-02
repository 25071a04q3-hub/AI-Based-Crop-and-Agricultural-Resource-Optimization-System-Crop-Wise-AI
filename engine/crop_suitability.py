"""
FarmTwin — AI Crop Suitability Prediction Engine.

This module implements the crop suitability decision layer.
It ingests a validated FarmProfile, extracts agronomic soil and climate features,
and queries a trained Random Forest classifier trained on the verified 22-crop benchmark
dataset (data/raw/crop_recommendation.csv). It produces a ranked candidate crop list
with calibrated suitability scores, prototype suitability tiers, and crop metadata.

IMPORTANT ARCHITECTURAL RULE:
This module must remain completely independent of UI/Streamlit frameworks.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from engine.profile import FarmProfile

# ==========================================
# FILE PATHS & CONSTANTS
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "raw" / "crop_recommendation.csv"
CROPS_CONFIG_PATH = BASE_DIR / "config" / "crops_profile.json"

FEATURE_COLUMNS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
TARGET_COLUMN = "label"

# Prototype Interpretation Thresholds
THRESH_HIGH = 0.80
THRESH_MODERATE = 0.60
THRESH_LOW_LIMIT = 0.40


class CropSuitabilityResult(BaseModel):
    """
    Structured outcome for an individual crop suitability evaluation.
    """
    crop_name: str = Field(description="Canonical crop identifier")
    suitability_score: float = Field(description="Normalized suitability score between 0.0 and 1.0")
    suitability_level: str = Field(description="Prototype tier: Highly Suitable, Suitable, Moderately Suitable, Low Suitability")
    rank: int = Field(description="Ordinal ranking starting at 1")
    model_probability: float = Field(description="Raw probability output from Random Forest ensemble")
    supporting_features: Dict[str, Any] = Field(default_factory=dict, description="Input values and crop metadata")
    explanation: str = Field(default="", description="Lightweight plain-language explanation of suitability")


def format_suitability_level(score: float) -> str:
    """
    Categorizes suitability score into prototype interpretation tiers:
    >= 0.80 -> Highly Suitable
    >= 0.60 -> Suitable
    >= 0.40 -> Moderately Suitable
    <  0.40 -> Low Suitability
    """
    if score >= THRESH_HIGH:
        return "Highly Suitable"
    if score >= THRESH_MODERATE:
        return "Suitable"
    if score >= THRESH_LOW_LIMIT:
        return "Moderately Suitable"
    return "Low Suitability"


def load_and_audit_dataset(csv_path: Optional[Path] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Loads and audits the crop recommendation dataset.
    Validates required columns, checks for missing data, duplicates, and class balance.
    """
    target_path = Path(csv_path) if csv_path else DATA_PATH
    if not target_path.exists():
        raise FileNotFoundError(f"Training dataset not found at expected path: {target_path}")

    df = pd.read_csv(target_path)

    # 1. Column Validation
    required_cols = set(FEATURE_COLUMNS + [TARGET_COLUMN])
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise ValueError(f"Dataset is missing required columns: {missing_cols}")

    # 2. Audit Metrics
    missing_count = int(df[FEATURE_COLUMNS + [TARGET_COLUMN]].isnull().sum().sum())
    duplicate_count = int(df.duplicated().sum())
    crop_classes = sorted(df[TARGET_COLUMN].unique().tolist())

    audit_summary = {
        "rows": len(df),
        "columns": list(df.columns),
        "features": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "missing_values": missing_count,
        "duplicates": duplicate_count,
        "num_classes": len(crop_classes),
        "classes": crop_classes,
        "season_column_present": "season" in df.columns,
    }

    return df, audit_summary


def load_crop_metadata() -> Dict[str, Any]:
    """Loads 22-crop agronomic metadata from config/crops_profile.json."""
    if CROPS_CONFIG_PATH.exists():
        with open(CROPS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


# ==========================================
# MODEL TRAINING & CACHING PIPELINE
# ==========================================
_MODEL_CACHE: Optional[Tuple[RandomForestClassifier, Dict[str, Any]]] = None


def train_suitability_model(
    df: Optional[pd.DataFrame] = None,
    random_state: int = 42,
    test_size: float = 0.2
) -> Tuple[RandomForestClassifier, Dict[str, Any]]:
    """
    Trains a Random Forest classifier with stratified train/test split.
    Separates X and y cleanly to prevent any data leakage.
    Returns the fitted model and comprehensive prototype evaluation metrics.
    """
    if df is None:
        df, _ = load_and_audit_dataset()

    X = df[FEATURE_COLUMNS].copy()
    y = df[TARGET_COLUMN].copy()

    # Stratified train/test split to maintain class balance across all 22 crops
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=12,
        random_state=random_state,
        n_jobs=-1
    )
    clf.fit(X_train, y_train)

    # Evaluation
    y_pred = clf.predict(X_test)
    accuracy = float(accuracy_score(y_test, y_pred))
    precision_w = float(precision_score(y_test, y_pred, average="weighted", zero_division=0))
    recall_w = float(recall_score(y_test, y_pred, average="weighted", zero_division=0))
    f1_w = float(f1_score(y_test, y_pred, average="weighted", zero_division=0))
    f1_macro = float(f1_score(y_test, y_pred, average="macro", zero_division=0))

    report_dict = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
    report_text = classification_report(y_test, y_pred, zero_division=0)

    importances = dict(zip(FEATURE_COLUMNS, [round(float(v), 4) for v in clf.feature_importances_]))

    metrics = {
        "accuracy": round(accuracy, 4),
        "precision": round(precision_w, 4),
        "recall": round(recall_w, 4),
        "f1": round(f1_w, 4),
        "f1_macro": round(f1_macro, 4),
        "feature_importances": importances,
        "classification_report_text": report_text,
        "classification_report_dict": report_dict,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "random_state": random_state,
    }

    return clf, metrics


def get_or_train_suitability_model(force_retrain: bool = False) -> Tuple[RandomForestClassifier, Dict[str, Any]]:
    """
    In-memory singleton model loader to prevent retraining during Streamlit reruns.
    """
    global _MODEL_CACHE
    if _MODEL_CACHE is not None and not force_retrain:
        return _MODEL_CACHE

    model, metrics = train_suitability_model()
    _MODEL_CACHE = (model, metrics)
    return _MODEL_CACHE


# ==========================================
# INFERENCE & ADAPTER LAYER
# ==========================================
def extract_features_from_profile(profile: FarmProfile) -> pd.DataFrame:
    """
    Maps validated FarmProfile attributes cleanly to model feature columns:
    - N <- nitrogen_n_kg_ha
    - P <- phosphorus_p_kg_ha
    - K <- potassium_k_kg_ha
    - temperature <- temperature_c
    - humidity <- humidity_percent
    - ph <- ph
    - rainfall <- rainfall_mm
    """
    if not isinstance(profile, FarmProfile):
        raise TypeError(f"Expected FarmProfile instance, got {type(profile).__name__}")

    row = {
        "N": float(profile.nitrogen_n_kg_ha),
        "P": float(profile.phosphorus_p_kg_ha),
        "K": float(profile.potassium_k_kg_ha),
        "temperature": float(profile.temperature_c),
        "humidity": float(profile.humidity_percent),
        "ph": float(profile.ph),
        "rainfall": float(profile.rainfall_mm),
    }
    return pd.DataFrame([row])[FEATURE_COLUMNS]


def _generate_crop_explanation(
    crop_name: str,
    score: float,
    level: str,
    profile_features: Dict[str, float],
    top_driver: str,
    metadata: Dict[str, Any]
) -> str:
    """
    Synthesizes a lightweight, transparent explanation for why this crop received its score.
    """
    driver_name = top_driver.upper() if len(top_driver) <= 2 else top_driver.capitalize()
    duration = metadata.get("duration_days")
    water_req = metadata.get("water_req_mm")

    agri_context = ""
    if duration and water_req:
        agri_context = f" (Maturity: ~{duration} days, Water: {water_req} mm)"

    if score >= THRESH_HIGH:
        return (
            f"High suitability ({score * 100:.1f}%) because farm soil nutrients and climatic parameters "
            f"closely align with the learned conditions for {crop_name.capitalize()}{agri_context}. "
            f"Key global model driver: {driver_name}."
        )
    elif score >= THRESH_MODERATE:
        return (
            f"Suitable ({score * 100:.1f}%) with favorable soil and moisture conditions for "
            f"{crop_name.capitalize()}{agri_context}. Key driver: {driver_name}."
        )
    elif score >= THRESH_LOW_LIMIT:
        return (
            f"Moderate suitability ({score * 100:.1f}%). Certain soil or weather factors partially deviate "
            f"from peak {crop_name.capitalize()} profiles{agri_context}."
        )
    else:
        return (
            f"Low suitability ({score * 100:.1f}%). Soil or climate constraints differ substantially "
            f"from typical {crop_name.capitalize()} requirements{agri_context}."
        )


def predict_crop_suitability(
    profile: FarmProfile,
    model: Optional[RandomForestClassifier] = None,
    top_n: Optional[int] = None
) -> List[CropSuitabilityResult]:
    """
    Executes AI crop suitability prediction on a validated FarmProfile.
    Returns ranked CropSuitabilityResult objects sorted descending by suitability score.
    """
    if model is None:
        model, _ = get_or_train_suitability_model()

    input_df = extract_features_from_profile(profile)
    probabilities = model.predict_proba(input_df)[0]
    classes = model.classes_
    feature_importances = dict(zip(FEATURE_COLUMNS, model.feature_importances_))
    top_driver = max(feature_importances, key=feature_importances.get)

    crops_metadata = load_crop_metadata()
    profile_features_dict = input_df.iloc[0].to_dict()

    ranked_pairs = sorted(zip(classes, probabilities), key=lambda x: x[1], reverse=True)

    results: List[CropSuitabilityResult] = []
    for rank, (crop_name, prob) in enumerate(ranked_pairs, start=1):
        score = round(float(prob), 4)
        level = format_suitability_level(score)
        crop_meta = crops_metadata.get(crop_name, {})

        explanation = _generate_crop_explanation(
            crop_name=crop_name,
            score=score,
            level=level,
            profile_features=profile_features_dict,
            top_driver=top_driver,
            metadata=crop_meta
        )

        supporting_info = {
            "profile_inputs": profile_features_dict,
            "crop_metadata": crop_meta,
            "top_global_driver": top_driver,
        }

        results.append(
            CropSuitabilityResult(
                crop_name=crop_name,
                suitability_score=score,
                suitability_level=level,
                rank=rank,
                model_probability=score,
                supporting_features=supporting_info,
                explanation=explanation
            )
        )

    if top_n is not None and top_n > 0:
        return results[:top_n]
    return results


def recommend_crops(profile: FarmProfile, top_n: int = 5) -> List[CropSuitabilityResult]:
    """
    Primary interface to shortlist the top N most suitable crops for a given FarmProfile.
    """
    return predict_crop_suitability(profile=profile, top_n=top_n)
