"""
FarmTwin — AI Crop Suitability Engine.

Facade re-exporting the primary implementation from engine.crop_suitability.
"""
from engine.crop_suitability import (
    CropSuitabilityResult,
    recommend_crops,
    predict_crop_suitability,
    get_or_train_suitability_model,
    train_suitability_model,
    load_and_audit_dataset,
    format_suitability_level,
    extract_features_from_profile,
)

__all__ = [
    "CropSuitabilityResult",
    "recommend_crops",
    "predict_crop_suitability",
    "get_or_train_suitability_model",
    "train_suitability_model",
    "load_and_audit_dataset",
    "format_suitability_level",
    "extract_features_from_profile",
]
