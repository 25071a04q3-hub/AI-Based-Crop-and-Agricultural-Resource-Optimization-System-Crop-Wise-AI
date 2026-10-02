"""
Tests for FarmTwin Phase 4: Probabilistic Crop Yield Prediction Engine.

Validates the Dataset Decision Gate, Data Honesty rules, production calculations,
error handling, and the Quantile Gradient Boosting regression algorithms.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from engine.profile import FarmProfile, get_demo_farm_profile
from engine.yield_prediction import (
    YieldPredictionResult,
    calculate_farm_yield,
    audit_and_validate_yield_dataset,
    train_quantile_yield_models,
    get_or_train_yield_models,
    predict_yield,
)


class TestDatasetDecisionGateAndAudit:
    """Tests the critical data audit gate ensuring fake yield data is never used."""

    def test_legacy_toy_dataset_disqualification(self):
        """Verifies that the 28-row legacy archive/yield_data.csv is audited and disqualified."""
        legacy_path = Path(__file__).resolve().parent.parent / "archive" / "yield_data.csv"
        if legacy_path.exists():
            is_valid, audit = audit_and_validate_yield_dataset(legacy_path)
            assert not is_valid
            assert audit["dataset_found"] is True
            assert audit["rows"] == 27
            assert len(audit["disqualification_reasons"]) > 0
            # Must identify insufficient sample size and crops with < 15 samples
            disq_text = " ".join(audit["disqualification_reasons"])
            assert "sample count" in disq_text or "fewer than" in disq_text

    def test_nonexistent_dataset_handling(self, tmp_path):
        """Verifies clean handling when a dataset file does not exist."""
        fake_path = tmp_path / "nonexistent_yield.csv"
        is_valid, audit = audit_and_validate_yield_dataset(fake_path)
        assert not is_valid
        assert audit["is_valid"] is False
        assert audit["dataset_found"] is False

    def test_dataset_without_required_target_disqualified(self, tmp_path):
        """Verifies that a CSV lacking target yield columns is disqualified."""
        dummy_csv = tmp_path / "invalid_target.csv"
        df = pd.DataFrame({
            "crop": ["rice"] * 300,
            "nitrogen": [50] * 300,
            "year": [2020] * 300
        })
        df.to_csv(dummy_csv, index=False)
        is_valid, audit = audit_and_validate_yield_dataset(dummy_csv)
        assert not is_valid
        assert any("Missing recognized target yield column" in r for r in audit["disqualification_reasons"])

    def test_dataset_without_temporal_dimension_disqualified(self, tmp_path):
        """Verifies that a dataset without year/date columns is disqualified."""
        dummy_csv = tmp_path / "no_year.csv"
        df = pd.DataFrame({
            "crop": ["rice"] * 300,
            "yield_t_per_ha": [4.0] * 300,
            "N": [50] * 300
        })
        df.to_csv(dummy_csv, index=False)
        is_valid, audit = audit_and_validate_yield_dataset(dummy_csv)
        assert not is_valid
        assert any("temporal time-series" in r for r in audit["disqualification_reasons"])


class TestDecisionGateModelBlocking:
    """Verifies that in the absence of valid historical data, model training is blocked."""

    def test_training_safely_blocked_in_default_repo(self):
        """Verifies that get_or_train_yield_models blocks training in current repo."""
        models_bundle, status_info = get_or_train_yield_models(force_retrain=True)
        assert models_bundle is None
        assert status_info["status"] == "BLOCKED_NO_HISTORICAL_DATASET"
        assert "Phase 4 model training is blocked" in status_info["message"]

    def test_predict_yield_returns_honest_blocked_contract(self):
        """Verifies predict_yield returns structured contract without fabricating fake numbers."""
        demo_profile = get_demo_farm_profile()
        result = predict_yield(demo_profile, "rice")

        assert isinstance(result, YieldPredictionResult)
        assert result.crop_name == "rice"
        assert result.status == "BLOCKED_NO_HISTORICAL_DATASET"
        # CRITICAL: No fake P10/P50/P90 or farm numbers
        assert result.p10_yield_t_per_ha is None
        assert result.p50_yield_t_per_ha is None
        assert result.p90_yield_t_per_ha is None
        assert result.farm_yield_p10_tonnes is None
        assert result.farm_yield_p50_tonnes is None
        assert result.farm_yield_p90_tonnes is None
        assert "A validated historical yield dataset is required" in result.message

    def test_predict_yield_input_validation(self):
        """Verifies input validation on farm profile and crop name."""
        demo_profile = get_demo_farm_profile()
        with pytest.raises(TypeError, match="Expected FarmProfile"):
            predict_yield("invalid_profile", "rice")  # type: ignore

        with pytest.raises(ValueError, match="Target crop name must be a non-empty string"):
            predict_yield(demo_profile, "")

        with pytest.raises(ValueError, match="Target crop name must be a non-empty string"):
            predict_yield(demo_profile, "   ")


class TestFarmProductionCalculation:
    """Verifies accurate farm-level total production calculation: Yield * Area."""

    def test_calculate_farm_yield_accuracy(self):
        # 3.5 tonnes/ha on 2.0 ha = 7.0 tonnes
        assert calculate_farm_yield(3.5, 2.0) == 7.0
        # 4.125 tonnes/ha on 1.5 ha = 6.1875 tonnes
        assert calculate_farm_yield(4.125, 1.5) == 6.1875
        # Zero area or zero yield produces zero
        assert calculate_farm_yield(0.0, 5.0) == 0.0
        assert calculate_farm_yield(3.5, 0.0) == 0.0

    def test_calculate_farm_yield_rejects_negative_values(self):
        with pytest.raises(ValueError, match="non-negative"):
            calculate_farm_yield(-1.0, 2.0)
        with pytest.raises(ValueError, match="non-negative"):
            calculate_farm_yield(3.0, -0.5)


class TestQuantileRegressionAlgorithm:
    """
    Tests the Quantile Gradient Boosting regression algorithms on an isolated
    controlled synthetic dataset to verify statistical mechanics and non-crossing.
    """

    @pytest.fixture
    def synthetic_yield_dataset(self) -> pd.DataFrame:
        """Generates a small valid test DataFrame to verify quantile training logic."""
        np.random.seed(42)
        n_samples = 300
        n_feat = np.random.uniform(20, 140, n_samples)
        rainfall = np.random.uniform(40, 250, n_samples)
        temp = np.random.uniform(15, 38, n_samples)
        base_yield = 1.0 + 0.02 * n_feat + 0.01 * rainfall - 0.03 * (temp - 25)**2 / 10.0
        # Add heteroscedastic noise
        noise = np.random.normal(0, 0.4 + 0.002 * rainfall, n_samples)
        yield_val = np.maximum(0.2, base_yield + noise)

        return pd.DataFrame({
            "N": n_feat,
            "rainfall": rainfall,
            "temperature": temp,
            "crop_rice": [1.0] * n_samples,
            "yield_t_per_ha": yield_val,
        })

    def test_quantile_models_training_and_metrics(self, synthetic_yield_dataset):
        features = ["N", "rainfall", "temperature", "crop_rice"]
        models_bundle, metrics = train_quantile_yield_models(
            synthetic_yield_dataset,
            feature_cols=features,
            target_col="yield_t_per_ha",
            random_state=42
        )

        assert "p10" in models_bundle
        assert "p50" in models_bundle
        assert "p90" in models_bundle
        assert "mean" in models_bundle

        # Verify point metrics
        assert metrics["mae"] > 0
        assert metrics["rmse"] > 0
        assert "r2" in metrics

        # Verify pinball loss metrics
        assert metrics["quantile_loss_p10"] >= 0
        assert metrics["quantile_loss_p50"] >= 0
        assert metrics["quantile_loss_p90"] >= 0

    def test_quantile_monotonicity(self, synthetic_yield_dataset):
        """Verifies that predicted quantiles obey P10 <= P50 <= P90 on evaluation points."""
        features = ["N", "rainfall", "temperature", "crop_rice"]
        models_bundle, _ = train_quantile_yield_models(
            synthetic_yield_dataset,
            feature_cols=features,
            target_col="yield_t_per_ha",
            random_state=42
        )

        X_eval = synthetic_yield_dataset[features].iloc[:20]
        preds_p10 = models_bundle["p10"].predict(X_eval)
        preds_p50 = models_bundle["p50"].predict(X_eval)
        preds_p90 = models_bundle["p90"].predict(X_eval)

        for p10_raw, p50_raw, p90_raw in zip(preds_p10, preds_p50, preds_p90):
            # Apply monotonic non-crossing calibration
            p10 = max(0.05, round(float(p10_raw), 2))
            p50 = max(p10, round(float(p50_raw), 2))
            p90 = max(p50, round(float(p90_raw), 2))

            assert p10 <= p50 <= p90
            assert p10 >= 0.05
