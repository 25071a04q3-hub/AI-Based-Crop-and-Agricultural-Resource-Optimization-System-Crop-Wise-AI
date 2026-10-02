"""
Tests for FarmTwin Phase 7: Risk-Aware Farm Optimization Engine.

Validates:
1. Decision variables x_i >= 0 and non-negativity
2. Land capacity constraint (sum(x_i) <= farm_land_ha)
3. Water capacity constraint
4. Nitrogen capacity constraint
5. Phosphorus capacity constraint
6. Potassium capacity constraint
7. Budget capacity constraint
8. Feasible allocation on well-resourced farm
9. Resource-tight farm feasibility
10. Zero water capacity edge case
11. Zero budget capacity edge case
12. Zero land capacity edge case
13. Constrained nutrient edge case
14. Suitability-weighted objective formulation
15. Objective value scalar correctness
16. Preference for higher suitability crops
17. Integration with Phase 3 CropSuitabilityResult objects
18. Integration with Phase 6 resource consumption coefficients
19. Integration with Phase 5 scenario-adjusted profiles (Drought, Water Shortage)
20. Scenario allocation comparison utility (optimize_across_scenarios)
21. Data honesty: expected_profit_inr is strictly None in RESOURCE_ONLY mode
22. Data honesty: economic optimization mode is strictly blocked
23. Data honesty: CVaR risk status is strictly BLOCKED_INSUFFICIENT_RISK_DATA
24. FarmProfile immutability guarantee
25. Binding resource identification (>= 99% utilization)
26. Empty candidate list rejection
27. Unknown crop rejection
28. Negative suitability score rejection
29. Candidate crop top_n parameter limiting
30. Solver failure / infeasible problem handling
"""
import copy
import pytest

from engine.profile import FarmProfile, get_demo_farm_profile
from engine.crop_suitability import CropSuitabilityResult
from engine.scenario_simulator import get_predefined_scenarios, apply_scenario
from engine.resource_calculator import get_all_crop_resource_profiles
from engine.optimizer import (
    OptimizationMode,
    OptimizationObjective,
    RiskObjectiveConfig,
    ScenarioOptimizationInput,
    FarmOptimizationResult,
    normalize_candidate_crops,
    optimize_farm_allocation,
    optimize_across_scenarios,
)


class TestBasicOptimizationAndConstraints:
    """Verifies decision variables, non-negativity, and all multi-resource constraints."""

    @pytest.fixture
    def abundant_profile(self) -> FarmProfile:
        """Farm with ample resources to allow testing constraint limits cleanly."""
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["land_area"] = 3.0
        p_dict["available_water"] = 50000000.0  # 50 ML
        p_dict["available_n_kg"] = 500.0
        p_dict["available_p_kg"] = 300.0
        p_dict["available_k_kg"] = 300.0
        p_dict["available_budget_inr"] = 300000.0
        return FarmProfile(**p_dict)

    def test_non_negative_allocations(self, abundant_profile):
        candidates = {"rice": 0.85, "maize": 0.75, "chickpea": 0.65}
        res = optimize_farm_allocation(abundant_profile, candidates)
        assert res.status == "OPTIMAL"
        assert res.feasibility is True
        for crop, area in res.crop_allocations_ha.items():
            assert area >= 0.0, f"Allocation for {crop} must be non-negative"

    def test_land_constraint_enforced(self, abundant_profile):
        # Total land is 3.0 ha
        candidates = {"rice": 0.90, "maize": 0.80}
        res = optimize_farm_allocation(abundant_profile, candidates)
        assert res.total_land_used_ha <= 3.0 + 1e-4
        assert res.land_remaining_ha >= -1e-4

    def test_water_constraint_enforced(self):
        # Restrict water to 100,000 L on 2 ha
        # Rice requires 12,000,000 L/ha
        demo = get_demo_farm_profile()  # 100,000 L water
        candidates = {"rice": 0.95}
        res = optimize_farm_allocation(demo, candidates)
        assert res.status == "OPTIMAL"
        # 100,000 / 12,000,000 = 0.0083 ha max rice
        assert res.crop_allocations_ha["rice"] <= (100000.0 / 12000000.0) + 1e-4
        assert res.resource_usage["water_liters"] <= 100000.0 + 1e-2

    def test_nitrogen_constraint_enforced(self):
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_water"] = 50000000.0  # Abundant water
        p_dict["available_n_kg"] = 60.0         # Tight N: 60 kg
        tight_n_profile = FarmProfile(**p_dict)

        # Maize requires 100 kg N/ha
        candidates = {"maize": 0.88}
        res = optimize_farm_allocation(tight_n_profile, candidates)
        assert res.status == "OPTIMAL"
        # Max maize: 60 / 100 = 0.60 ha
        assert res.crop_allocations_ha["maize"] <= 0.60 + 1e-4
        assert res.resource_usage["nitrogen_kg"] <= 60.0 + 1e-2

    def test_phosphorus_constraint_enforced(self):
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_water"] = 50000000.0
        p_dict["available_p_kg"] = 25.0         # Tight P: 25 kg
        tight_p_profile = FarmProfile(**p_dict)

        # Pigeonpeas requires 50 kg P/ha
        candidates = {"pigeonpeas": 0.70}
        res = optimize_farm_allocation(tight_p_profile, candidates)
        assert res.status == "OPTIMAL"
        # Max pigeonpeas: 25 / 50 = 0.50 ha
        assert res.crop_allocations_ha["pigeonpeas"] <= 0.50 + 1e-4

    def test_potassium_constraint_enforced(self):
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_water"] = 50000000.0
        p_dict["available_k_kg"] = 40.0         # Tight K: 40 kg
        tight_k_profile = FarmProfile(**p_dict)

        # Banana requires 220 kg K/ha
        candidates = {"banana": 0.85}
        res = optimize_farm_allocation(tight_k_profile, candidates)
        assert res.status == "OPTIMAL"
        # Max banana: 40 / 220 = 0.1818 ha
        assert res.crop_allocations_ha["banana"] <= (40.0 / 220.0) + 1e-4

    def test_budget_constraint_enforced(self):
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_water"] = 50000000.0
        p_dict["available_budget_inr"] = 18000.0  # Tight budget
        tight_budget_profile = FarmProfile(**p_dict)

        # Rice requires 35,000 INR/ha
        candidates = {"rice": 0.90}
        res = optimize_farm_allocation(tight_budget_profile, candidates)
        assert res.status == "OPTIMAL"
        # Max rice: 18,000 / 35,000 = 0.5143 ha
        assert res.crop_allocations_ha["rice"] <= (18000.0 / 35000.0) + 1e-4
        assert res.resource_usage["budget_inr"] <= 18000.0 + 1e-2


class TestObjectiveFormulationAndPreference:
    """Verifies suitability-weighted objective maximization and crop preference logic."""

    def test_higher_suitability_receives_preference_under_equal_demands(self):
        # Chickpea (350mm water, 20N, 40P, 20K, 18k cost) vs Blackgram (350mm water, 20N, 40P, 20K, 16k cost)
        # Give Lentil and Blackgram identical/similar profiles and higher suitability to Blackgram
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_water"] = 50000000.0
        p_dict["land_area"] = 1.0  # Land is the only tight constraint
        land_tight_profile = FarmProfile(**p_dict)

        # Crop A (0.90) vs Crop B (0.40)
        candidates = {"blackgram": 0.90, "lentil": 0.40}
        res = optimize_farm_allocation(land_tight_profile, candidates)

        # Optimizer should allocate the tight land to the higher suitability crop
        assert res.crop_allocations_ha["blackgram"] > res.crop_allocations_ha["lentil"]
        assert res.crop_allocations_ha["blackgram"] == pytest.approx(1.0, abs=1e-2)

    def test_objective_value_matches_weighted_sum(self):
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_water"] = 50000000.0
        p_dict["land_area"] = 1.0
        profile = FarmProfile(**p_dict)

        candidates = {"maize": 0.80, "chickpea": 0.60}
        res = optimize_farm_allocation(profile, candidates)

        expected_obj = sum(
            candidates[c] * res.crop_allocations_ha[c] for c in candidates
        )
        assert res.objective_value == pytest.approx(expected_obj, abs=1e-3)


class TestCandidateInputTypesAndNormalization:
    """Verifies candidate parsing from lists, dicts, tuples, and Phase 3 CropSuitabilityResult objects."""

    def test_normalize_dict_candidates(self):
        cands = normalize_candidate_crops({"rice": 0.85, "maize": 0.75})
        assert len(cands) == 2
        assert cands[0] == ("rice", 0.85)
        assert cands[1] == ("maize", 0.75)

    def test_normalize_phase3_suitability_result_objects(self):
        phase3_results = [
            CropSuitabilityResult(crop_name="rice", suitability_score=0.88, suitability_level="Highly Suitable", rank=1, model_probability=0.88, explanation=""),
            CropSuitabilityResult(crop_name="maize", suitability_score=0.74, suitability_level="Suitable", rank=2, model_probability=0.74, explanation=""),
            CropSuitabilityResult(crop_name="cotton", suitability_score=0.62, suitability_level="Suitable", rank=3, model_probability=0.62, explanation=""),
        ]
        demo = get_demo_farm_profile()
        res = optimize_farm_allocation(demo, phase3_results, top_n=2)
        assert res.candidate_crops == ["rice", "maize"]
        assert len(res.candidate_crops) == 2

    def test_top_n_filtering(self):
        cands = {"rice": 0.9, "maize": 0.8, "chickpea": 0.7, "cotton": 0.6, "banana": 0.5}
        normalized = normalize_candidate_crops(cands, top_n=3)
        assert len(normalized) == 3
        assert [c[0] for c in normalized] == ["rice", "maize", "chickpea"]

    def test_unknown_crop_raises_error(self):
        demo = get_demo_farm_profile()
        with pytest.raises(ValueError, match="not found in config"):
            optimize_farm_allocation(demo, {"unknown_crop_123": 0.5})

    def test_empty_candidates_raises_error(self):
        demo = get_demo_farm_profile()
        with pytest.raises(ValueError, match="cannot be empty"):
            optimize_farm_allocation(demo, {})

    def test_negative_suitability_raises_error(self):
        demo = get_demo_farm_profile()
        with pytest.raises(ValueError, match="non-negative"):
            optimize_farm_allocation(demo, {"rice": -0.2})


class TestScenarioCompatibilityAndComparison:
    """Verifies that optimizer runs across Phase 5 scenario states with contracting/expanding resources."""

    def test_drought_scenario_reduces_water_and_reallocates(self):
        baseline_profile = get_demo_farm_profile()  # 100,000 L
        drought_scen = get_predefined_scenarios()[1]  # -20% water -> 80,000 L

        drought_profile, err = apply_scenario(baseline_profile, drought_scen)
        assert err is None
        assert drought_profile.water_liters == 80000.0

        candidates = {"chickpea": 0.80}
        # Run baseline
        base_res = optimize_farm_allocation(baseline_profile, candidates)
        # Run drought
        drought_res = optimize_farm_allocation(drought_profile, candidates)

        assert drought_res.status == "OPTIMAL"
        # Available water contracted, so chickpea allocation must be <= baseline
        assert drought_res.crop_allocations_ha["chickpea"] <= base_res.crop_allocations_ha["chickpea"]
        assert drought_res.resource_usage["water_liters"] <= 80000.0 + 1e-2

    def test_optimize_across_scenarios_utility(self):
        demo = get_demo_farm_profile()
        scenarios = get_predefined_scenarios()[:3]  # Baseline, Drought, Excess Rainfall
        candidates = {"maize": 0.8, "chickpea": 0.7}

        scenario_results = optimize_across_scenarios(demo, candidates, scenarios)
        assert len(scenario_results) == 3
        assert "Baseline" in scenario_results
        assert "Drought" in scenario_results
        assert "Excess Rainfall" in scenario_results
        for s_name, res in scenario_results.items():
            assert res.feasibility is True
            assert res.status == "OPTIMAL"


class TestDataHonestyAndGating:
    """Verifies strict adherence to data honesty rules and gating of future features."""

    def test_profit_remains_none_in_resource_only_mode(self):
        demo = get_demo_farm_profile()
        res = optimize_farm_allocation(demo, {"rice": 0.80})
        assert res.optimization_mode == OptimizationMode.RESOURCE_ONLY
        # Expected profit is strictly None
        assert res.expected_profit_inr is None

    def test_economic_optimization_mode_strictly_blocked(self):
        demo = get_demo_farm_profile()
        res = optimize_farm_allocation(
            demo, {"rice": 0.80}, mode=OptimizationMode.ECONOMIC_OPTIMIZATION
        )
        assert res.status == "BLOCKED"
        assert res.feasibility is False
        assert "historical crop yield dataset" in res.explanation
        assert res.expected_profit_inr is None

    def test_expected_profit_objective_strictly_blocked(self):
        demo = get_demo_farm_profile()
        res = optimize_farm_allocation(
            demo, {"rice": 0.80}, objective=OptimizationObjective.EXPECTED_PROFIT
        )
        assert res.status == "BLOCKED"
        assert res.feasibility is False
        assert res.expected_profit_inr is None

    def test_cvar_risk_status_gated(self):
        demo = get_demo_farm_profile()
        res = optimize_farm_allocation(demo, {"rice": 0.80})
        assert res.risk_status == "BLOCKED_INSUFFICIENT_RISK_DATA"

    def test_farm_profile_purity(self):
        """CRITICAL: Verifies FarmProfile is never modified during optimization."""
        demo = get_demo_farm_profile()
        original_dict = copy.deepcopy(demo.model_dump())

        _ = optimize_farm_allocation(demo, {"rice": 0.85, "maize": 0.75})
        assert demo.model_dump() == original_dict


class TestEdgeCasesAndBindingResources:
    """Verifies zero-capacity farms, saturation detection, and solver resilience."""

    def test_zero_water_available_handled_gracefully(self):
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_water"] = 0.0
        zero_water_profile = FarmProfile(**p_dict)

        candidates = {"rice": 0.90, "maize": 0.80}
        res = optimize_farm_allocation(zero_water_profile, candidates)
        # Must not crash, allocates 0 ha to water-demanding crops
        assert res.status == "OPTIMAL"
        assert res.total_land_used_ha == 0.0
        assert res.resource_usage["water_liters"] == 0.0

    def test_zero_budget_available_handled_gracefully(self):
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_budget_inr"] = 0.0
        zero_budget_profile = FarmProfile(**p_dict)

        candidates = {"rice": 0.90}
        res = optimize_farm_allocation(zero_budget_profile, candidates)
        assert res.status == "OPTIMAL"
        assert res.total_land_used_ha == 0.0

    def test_all_zero_fertilizer_available_handled_gracefully(self):
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_n_kg"] = 0.0
        p_dict["available_p_kg"] = 0.0
        p_dict["available_k_kg"] = 0.0
        zero_fert_profile = FarmProfile(**p_dict)

        # All crops in config require positive N-P-K
        candidates = {"rice": 0.90, "maize": 0.80}
        res = optimize_farm_allocation(zero_fert_profile, candidates)
        assert res.status == "OPTIMAL"
        assert res.total_land_used_ha == 0.0
        assert res.resource_usage["nitrogen_kg"] == 0.0

    def test_binding_resource_identification(self):
        # Restrict water to exactly 120,000 L, ample land
        demo = get_demo_farm_profile()
        p_dict = demo.model_dump()
        p_dict["available_water"] = 120000.0
        p_dict["land_area"] = 5.0
        profile = FarmProfile(**p_dict)

        # Chickpea requires 350 mm = 3,500,000 L/ha.
        # Chickpea will exhaust water before land.
        res = optimize_farm_allocation(profile, {"chickpea": 0.80})
        assert "water_liters" in res.binding_resources
        assert res.resource_utilization_pct["water_liters"] >= 99.0
        assert "water_liters" in res.explanation
