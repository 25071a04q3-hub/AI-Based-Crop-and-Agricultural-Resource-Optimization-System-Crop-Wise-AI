"""
Tests for FarmTwin Jury Demo Presets and Unified Pipeline Execution.
"""
import pytest
from ui.presets import DEMO_PRESETS, get_preset_profile, execute_full_decision_pipeline
from engine.profile import FarmProfile


class TestDemoPresets:
    """Verifies all jury demonstration presets load and adhere to data honesty."""

    def test_all_presets_valid_farm_profiles(self):
        """Verifies each preset initializes a valid FarmProfile without ValidationError."""
        assert len(DEMO_PRESETS) == 4
        for name in DEMO_PRESETS:
            profile = get_preset_profile(name)
            assert isinstance(profile, FarmProfile)
            assert profile.land_area_ha > 0.0
            assert profile.available_water > 0.0

    def test_pipeline_execution_balanced_farm(self):
        """Verifies end-to-end execution of Balanced Farm preset."""
        p = get_preset_profile("Balanced Farm (Telangana)")
        out = execute_full_decision_pipeline(p)

        assert out["opt_result"].feasibility is True
        assert out["opt_result"].optimization_mode == "RESOURCE_ONLY"
        assert out["opt_result"].expected_profit_inr is None

        # Data Honesty checks
        assert out["yield_result"].status == "BLOCKED_NO_HISTORICAL_DATASET"
        assert out["yield_result"].p50_yield_t_per_ha is None
        assert out["portfolio_report"].rotation_status == "DATA_UNAVAILABLE"

        # Check bottleneck & reserve existence
        assert out["bottleneck_report"].primary_bottleneck is not None
        assert out["adaptive_report"].trigger_status in ("PLAN_STABLE", "REOPTIMIZATION_REQUIRED")

    def test_water_stressed_preset_identifies_water_bottleneck(self):
        """Verifies that the water-stressed preset identifies water as the primary binding constraint."""
        p = get_preset_profile("Water-Stressed Farm (Rajasthan)")
        out = execute_full_decision_pipeline(p)

        assert out["bottleneck_report"].primary_bottleneck == "water_liters"
        assert out["bottleneck_report"].primary_bottleneck_utilization >= 99.0

    def test_fertilizer_constrained_preset_identifies_nutrient_bottleneck(self):
        """Verifies that the fertilizer-constrained preset identifies nutrient limits."""
        p = get_preset_profile("Fertilizer-Constrained Farm (Bihar)")
        out = execute_full_decision_pipeline(p)

        prim = out["bottleneck_report"].primary_bottleneck
        assert prim in ("phosphorus_kg", "nitrogen_kg", "potassium_kg")
        assert out["bottleneck_report"].primary_bottleneck_utilization >= 99.0

    def test_capital_constrained_preset_identifies_budget_bottleneck(self):
        """Verifies that the capital-constrained preset identifies budget as the primary bottleneck."""
        p = get_preset_profile("Capital-Constrained Farm (Maharashtra)")
        out = execute_full_decision_pipeline(p)

        assert out["bottleneck_report"].primary_bottleneck == "budget_inr"
        assert out["bottleneck_report"].primary_bottleneck_utilization >= 99.0
