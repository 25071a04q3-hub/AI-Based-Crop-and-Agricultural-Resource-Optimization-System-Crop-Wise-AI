"""
Tests for FarmTwin Phase 5: Future Scenario Simulator & Farm Stress Testing Engine.

Validates:
1. Baseline scenario creation
2. Drought scenario creation
3. Excess rainfall scenario
4. Water shortage scenario
5. Fertilizer price shock
6. Market price shock
7. Combined stress scenario
8. Rainfall transformation
9. Water transformation
10. Temperature transformation
11. Humidity boundary validation
12. Rainfall cannot become negative
13. Water cannot become negative
14. Original FarmProfile is not mutated
15. Scenario generation is reproducible
16. Scenario count works
17. Invalid scenarios are handled
18. Scenario explanation is generated
19. Blocked yield model produces no fake yield
20. Blocked yield model produces no fake profit
21. Comparison table is generated
22. Phase 3 selected crop can flow into scenario engine
"""
import copy
import pandas as pd
import pytest

from engine.profile import FarmProfile, get_demo_farm_profile
from engine.scenario_simulator import (
    ScenarioCategory,
    ScenarioStatus,
    ScenarioDefinition,
    ScenarioResult,
    get_predefined_scenarios,
    apply_scenario,
    generate_random_scenarios,
    generate_scenarios,
    simulate_scenario,
    simulate_scenarios,
    compare_scenarios,
)


class TestStandardScenariosCreation:
    """Verifies creation and specifications of the 7 predefined standard stress scenarios."""

    @pytest.fixture
    def scenarios(self):
        return {s.scenario_name: s for s in get_predefined_scenarios()}

    def test_predefined_scenarios_count_and_types(self, scenarios):
        assert len(scenarios) == 7
        expected_names = [
            "Baseline",
            "Drought",
            "Excess Rainfall",
            "Water Shortage",
            "Fertilizer Price Shock",
            "Market Price Shock",
            "Combined Stress",
        ]
        for name in expected_names:
            assert name in scenarios

    def test_baseline_scenario_creation(self, scenarios):
        s = scenarios["Baseline"]
        assert s.category == ScenarioCategory.NORMAL
        assert s.rainfall_change_pct == 0.0
        assert s.temperature_change_c == 0.0
        assert s.water_change_pct == 0.0
        assert s.fertilizer_price_change_pct == 0.0
        assert s.market_price_change_pct == 0.0
        assert s.probability is None

    def test_drought_scenario_creation(self, scenarios):
        s = scenarios["Drought"]
        assert s.category in (ScenarioCategory.WEATHER_STRESS, ScenarioCategory.WATER_STRESS)
        assert s.rainfall_change_pct == -30.0
        assert s.water_change_pct == -20.0
        assert s.temperature_change_c > 0
        assert s.probability is None

    def test_excess_rainfall_scenario_creation(self, scenarios):
        s = scenarios["Excess Rainfall"]
        assert s.category == ScenarioCategory.WEATHER_STRESS
        assert s.rainfall_change_pct == 30.0
        assert s.probability is None

    def test_water_shortage_scenario_creation(self, scenarios):
        s = scenarios["Water Shortage"]
        assert s.category == ScenarioCategory.WATER_STRESS
        assert s.water_change_pct == -30.0
        assert s.probability is None

    def test_fertilizer_price_shock_creation(self, scenarios):
        s = scenarios["Fertilizer Price Shock"]
        assert s.category == ScenarioCategory.INPUT_COST_STRESS
        assert s.fertilizer_price_change_pct == 25.0
        assert s.rainfall_change_pct == 0.0
        assert s.probability is None

    def test_market_price_shock_creation(self, scenarios):
        s = scenarios["Market Price Shock"]
        assert s.category == ScenarioCategory.MARKET_STRESS
        assert s.market_price_change_pct == -15.0
        assert s.probability is None

    def test_combined_stress_creation(self, scenarios):
        s = scenarios["Combined Stress"]
        assert s.category == ScenarioCategory.COMBINED_STRESS
        assert s.rainfall_change_pct == -30.0
        assert s.water_change_pct == -20.0
        assert s.fertilizer_price_change_pct == 25.0
        assert s.market_price_change_pct == -15.0
        assert s.probability is None


class TestConditionTransformationsAndBoundaries:
    """Verifies that physical and resource shock transformations are mathematically sound and bounded."""

    def test_rainfall_transformation(self):
        profile = get_demo_farm_profile()  # rainfall_mm = 100.0
        scen = ScenarioDefinition(
            scenario_id="TEST-RAIN",
            scenario_name="Rain Test",
            rainfall_change_pct=-25.0
        )
        adj_profile, err = apply_scenario(profile, scen)
        assert err is None
        assert adj_profile is not None
        assert adj_profile.rainfall_mm == 75.0

    def test_water_transformation(self):
        profile = get_demo_farm_profile()  # available_water = 100,000 L
        scen = ScenarioDefinition(
            scenario_id="TEST-WATER",
            scenario_name="Water Test",
            water_change_pct=-35.0
        )
        adj_profile, err = apply_scenario(profile, scen)
        assert err is None
        assert adj_profile is not None
        assert adj_profile.available_water == 65000.0

    def test_temperature_transformation(self):
        profile = get_demo_farm_profile()  # temperature_c = 28.0
        scen = ScenarioDefinition(
            scenario_id="TEST-TEMP",
            scenario_name="Temp Test",
            temperature_change_c=3.5
        )
        adj_profile, err = apply_scenario(profile, scen)
        assert err is None
        assert adj_profile is not None
        assert adj_profile.temperature_c == 31.5

    def test_rainfall_cannot_become_negative(self):
        profile = get_demo_farm_profile()  # rainfall_mm = 100.0
        scen = ScenarioDefinition(
            scenario_id="TEST-RAIN-NEG",
            scenario_name="Negative Rain",
            rainfall_change_pct=-150.0  # Would result in -50 mm
        )
        adj_profile, err = apply_scenario(profile, scen)
        assert adj_profile is None
        assert err is not None
        assert "Rainfall cannot become negative" in err

    def test_water_cannot_become_negative(self):
        profile = get_demo_farm_profile()
        scen = ScenarioDefinition(
            scenario_id="TEST-WATER-NEG",
            scenario_name="Negative Water",
            water_change_pct=-110.0
        )
        adj_profile, err = apply_scenario(profile, scen)
        assert adj_profile is None
        assert err is not None
        assert "Usable water cannot become negative" in err

    def test_humidity_boundary_validation(self):
        profile = get_demo_farm_profile()  # humidity_percent = 65.0
        # Exceed 100%
        scen_high = ScenarioDefinition(
            scenario_id="TEST-HUM-HIGH",
            scenario_name="High Humidity",
            humidity_change_pct=50.0  # 65 + 50 = 115%
        )
        adj_high, err_high = apply_scenario(profile, scen_high)
        assert adj_high is None
        assert "Humidity" in err_high

        # Drop below 0%
        scen_low = ScenarioDefinition(
            scenario_id="TEST-HUM-LOW",
            scenario_name="Low Humidity",
            humidity_change_pct=-80.0  # 65 - 80 = -15%
        )
        adj_low, err_low = apply_scenario(profile, scen_low)
        assert adj_low is None
        assert "Humidity" in err_low

    def test_original_farm_profile_not_mutated(self):
        """CRITICAL: Verifies immutable / copy semantics — original profile is untouched."""
        profile = get_demo_farm_profile()
        original_dict = copy.deepcopy(profile.model_dump())

        drought = get_predefined_scenarios()[1]  # Drought
        adj_profile, _ = apply_scenario(profile, drought)

        # Original profile values must remain exactly identical
        assert profile.model_dump() == original_dict
        # Adjusted profile must reflect changes
        assert adj_profile.rainfall_mm != profile.rainfall_mm
        assert adj_profile.available_water != profile.available_water


class TestRandomScenarioGeneration:
    """Verifies controlled randomized scenario generation and reproducibility."""

    def test_scenario_generation_reproducibility(self):
        scens_a = generate_random_scenarios(n_scenarios=25, random_state=42)
        scens_b = generate_random_scenarios(n_scenarios=25, random_state=42)
        scens_diff = generate_random_scenarios(n_scenarios=25, random_state=999)

        assert len(scens_a) == 25
        assert len(scens_b) == 25
        # Same seed must yield identical values
        for a, b in zip(scens_a, scens_b):
            assert a.rainfall_change_pct == b.rainfall_change_pct
            assert a.water_change_pct == b.water_change_pct
            assert a.temperature_change_c == b.temperature_change_c
            assert a.fertilizer_price_change_pct == b.fertilizer_price_change_pct

        # Different seed should differ
        assert scens_a[0].rainfall_change_pct != scens_diff[0].rainfall_change_pct

    def test_scenario_count_works(self):
        assert len(generate_random_scenarios(n_scenarios=10)) == 10
        assert len(generate_random_scenarios(n_scenarios=100)) == 100
        assert len(generate_random_scenarios(n_scenarios=0)) == 0

        # Unified generator count
        all_scens = generate_scenarios(include_predefined=True, n_random=50)
        assert len(all_scens) == 7 + 50


class TestScenarioSimulationAndDataHonesty:
    """Verifies scenario simulation contracts, blocked yield behavior, and tabular comparison."""

    def test_invalid_scenario_handled_gracefully(self):
        profile = get_demo_farm_profile()
        invalid_scen = ScenarioDefinition(
            scenario_id="INVALID-01",
            scenario_name="Impossible Rain",
            rainfall_change_pct=-200.0
        )
        res = simulate_scenario(profile, invalid_scen)
        assert res.status == ScenarioStatus.INVALID_SCENARIO
        assert res.adjusted_rainfall_mm is None
        assert "Physical Boundary Violation" in res.explanation

    def test_scenario_explanation_generated(self):
        profile = get_demo_farm_profile()
        scen = ScenarioDefinition(
            scenario_id="TEST-EXP",
            scenario_name="Explanation Test",
            rainfall_change_pct=-30.0,
            water_change_pct=-20.0,
            fertilizer_price_change_pct=25.0
        )
        res = simulate_scenario(profile, scen)
        assert "Rainfall -30.0%" in res.explanation
        assert "Water -20.0%" in res.explanation
        assert "Fertilizer cost +25.0%" in res.explanation

    def test_blocked_yield_model_produces_no_fake_yield_or_profit(self):
        """CRITICAL RULE: While yield model is blocked, scenario outcome must be BLOCKED_NO_YIELD_MODEL."""
        profile = get_demo_farm_profile()
        drought = get_predefined_scenarios()[1]

        res = simulate_scenario(profile, drought, crop_name="rice")

        assert res.status == ScenarioStatus.BLOCKED_NO_YIELD_MODEL
        # Zero fabricated numbers allowed
        assert res.yield_p10 is None
        assert res.yield_p50 is None
        assert res.yield_p90 is None
        assert res.production_p10 is None
        assert res.production_p50 is None
        assert res.production_p90 is None
        assert res.revenue is None
        assert res.profit is None

        # Physical transformations are nonetheless valid and verified
        assert res.adjusted_rainfall_mm == 70.0
        assert res.adjusted_water_liters == 80000.0

    def test_comparison_table_generation(self):
        profile = get_demo_farm_profile()
        scenarios = get_predefined_scenarios()
        results = simulate_scenarios(profile, scenarios, crop_name="rice")
        df_comp = compare_scenarios(results)

        assert isinstance(df_comp, pd.DataFrame)
        assert len(df_comp) == 7
        assert "Scenario Name" in df_comp.columns
        assert "Yield Outcome Status" in df_comp.columns
        assert "Rainfall (mm)" in df_comp.columns
        # All currently expected to report BLOCKED_NO_YIELD_MODEL
        assert all(status == "BLOCKED_NO_YIELD_MODEL" for status in df_comp["Yield Outcome Status"])

    def test_phase3_selected_crop_flows_into_scenario_engine(self):
        profile = get_demo_farm_profile()
        drought = get_predefined_scenarios()[1]

        res = simulate_scenario(profile, drought, crop_name="cotton")
        assert res.crop_name == "cotton"
        assert res.status == ScenarioStatus.BLOCKED_NO_YIELD_MODEL
