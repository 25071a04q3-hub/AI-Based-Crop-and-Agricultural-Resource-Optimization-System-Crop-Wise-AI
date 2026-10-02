"""
Test Suite: AI Crop Suitability Prediction Engine.
Validates all Section 15 requirements for Phase 3.
"""
import pytest
import pandas as pd
from engine.profile import FarmProfile, get_demo_farm_profile
from engine.crop_suitability import (
    load_and_audit_dataset,
    train_suitability_model,
    get_or_train_suitability_model,
    extract_features_from_profile,
    predict_crop_suitability,
    recommend_crops,
    format_suitability_level,
    CropSuitabilityResult,
    FEATURE_COLUMNS,
    TARGET_COLUMN,
)


# -------------------------------------------------------------
# Test 1 — Training data loads successfully
# -------------------------------------------------------------
def test_training_data_loads():
    df, audit = load_and_audit_dataset()
    assert df is not None
    assert len(df) == 2200
    assert audit["rows"] == 2200
    assert audit["missing_values"] == 0
    assert audit["duplicates"] == 0


# -------------------------------------------------------------
# Test 2 — Required dataset columns are validated
# -------------------------------------------------------------
def test_required_dataset_columns_validated():
    df, audit = load_and_audit_dataset()
    for col in FEATURE_COLUMNS:
        assert col in df.columns, f"Feature column '{col}' missing from dataset"
    assert TARGET_COLUMN in df.columns, "Target column 'label' missing from dataset"

    # Verify invalid dataset missing a required column raises ValueError
    bad_df = df.drop(columns=["rainfall"])
    tmp_csv = "tests/_tmp_bad.csv"
    bad_df.to_csv(tmp_csv, index=False)
    try:
        with pytest.raises(ValueError) as exc:
            load_and_audit_dataset(tmp_csv)
        assert "missing required columns" in str(exc.value)
    finally:
        import os
        if os.path.exists(tmp_csv):
            os.remove(tmp_csv)


# -------------------------------------------------------------
# Test 3 — Model trains successfully
# -------------------------------------------------------------
def test_model_trains_successfully():
    model, metrics = train_suitability_model(random_state=42)
    assert model is not None
    assert hasattr(model, "predict_proba")
    assert len(model.classes_) == 22


# -------------------------------------------------------------
# Test 4 — Model evaluation returns metrics
# -------------------------------------------------------------
def test_model_evaluation_metrics():
    _, metrics = train_suitability_model(random_state=42)
    assert "accuracy" in metrics
    assert "precision" in metrics
    assert "recall" in metrics
    assert "f1" in metrics
    assert "f1_macro" in metrics
    assert "feature_importances" in metrics

    # Prototype performance checks
    assert metrics["accuracy"] >= 0.95
    assert metrics["f1"] >= 0.95
    assert len(metrics["feature_importances"]) == 7


# -------------------------------------------------------------
# Test 5 — FarmProfile converts to model features
# -------------------------------------------------------------
def test_farm_profile_to_features():
    demo = get_demo_farm_profile()
    features_df = extract_features_from_profile(demo)
    assert isinstance(features_df, pd.DataFrame)
    assert list(features_df.columns) == FEATURE_COLUMNS
    assert features_df.iloc[0]["N"] == demo.nitrogen_n_kg_ha
    assert features_df.iloc[0]["P"] == demo.phosphorus_p_kg_ha
    assert features_df.iloc[0]["K"] == demo.potassium_k_kg_ha
    assert features_df.iloc[0]["temperature"] == demo.temperature_c
    assert features_df.iloc[0]["humidity"] == demo.humidity_percent
    assert features_df.iloc[0]["ph"] == demo.ph
    assert features_df.iloc[0]["rainfall"] == demo.rainfall_mm


# -------------------------------------------------------------
# Test 6 — Prediction returns results
# -------------------------------------------------------------
def test_prediction_returns_results():
    demo = get_demo_farm_profile()
    results = predict_crop_suitability(demo)
    assert isinstance(results, list)
    assert len(results) == 22
    assert all(isinstance(r, CropSuitabilityResult) for r in results)


# -------------------------------------------------------------
# Test 7 — Suitability scores are within 0–1
# -------------------------------------------------------------
def test_suitability_scores_within_zero_to_one():
    demo = get_demo_farm_profile()
    results = predict_crop_suitability(demo)
    for r in results:
        assert 0.0 <= r.suitability_score <= 1.0, f"Score out of range: {r.suitability_score}"
        assert 0.0 <= r.model_probability <= 1.0


# -------------------------------------------------------------
# Test 8 — Rankings are correctly ordered (descending)
# -------------------------------------------------------------
def test_rankings_descending_order():
    demo = get_demo_farm_profile()
    results = predict_crop_suitability(demo)
    scores = [r.suitability_score for r in results]
    assert scores == sorted(scores, reverse=True), "Results are not sorted descending by score"

    # Verify rank numbering
    ranks = [r.rank for r in results]
    assert ranks == list(range(1, 23))


# -------------------------------------------------------------
# Test 9 — Top-N recommendation works
# -------------------------------------------------------------
def test_top_n_recommendations():
    demo = get_demo_farm_profile()
    top_3 = recommend_crops(demo, top_n=3)
    assert len(top_3) == 3
    assert top_3[0].rank == 1
    assert top_3[1].rank == 2
    assert top_3[2].rank == 3

    top_5 = recommend_crops(demo, top_n=5)
    assert len(top_5) == 5


# -------------------------------------------------------------
# Test 10 — Invalid / missing input is handled cleanly
# -------------------------------------------------------------
def test_invalid_input_handling():
    with pytest.raises(TypeError):
        # Passing raw dict instead of FarmProfile should be rejected cleanly
        extract_features_from_profile({"N": 50})

    with pytest.raises(TypeError):
        predict_crop_suitability("invalid_input_type")


# -------------------------------------------------------------
# Test 11 — Crop names are returned correctly
# -------------------------------------------------------------
def test_crop_names_returned_correctly():
    _, audit = load_and_audit_dataset()
    demo = get_demo_farm_profile()
    results = predict_crop_suitability(demo)
    returned_names = {r.crop_name for r in results}
    assert returned_names == set(audit["classes"])


# -------------------------------------------------------------
# Test 12 — Demo FarmProfile produces a valid suitability result
# -------------------------------------------------------------
def test_demo_farm_profile_suitability():
    demo = get_demo_farm_profile()
    results = recommend_crops(demo, top_n=5)
    assert len(results) == 5
    top_crop = results[0]
    assert top_crop.crop_name in ["banana", "coffee", "papaya", "maize"]
    assert top_crop.suitability_level in ["Highly Suitable", "Suitable", "Moderately Suitable", "Low Suitability"]
    assert len(top_crop.explanation) > 10
    assert "supporting_features" in top_crop.model_dump()


# -------------------------------------------------------------
# Test 13 — Cached model singleton avoids re-training
# -------------------------------------------------------------
def test_cached_model_singleton():
    m1, _ = get_or_train_suitability_model()
    m2, _ = get_or_train_suitability_model()
    assert m1 is m2, "Model should be cached in-memory and not retrained"
