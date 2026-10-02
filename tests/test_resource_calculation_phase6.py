"""
Tests for FarmTwin Phase 6: Resource Calculation & Resource Balance Engine.

Validates:
1. Per-hectare requirement calculations (water, N, P, K, cost, labour)
2. Exact unit conversions (depth mm -> m³ -> liters)
3. Farm-level single-crop calculation and balance
4. Sufficient vs insufficient water feasibility
5. Sufficient vs insufficient N/P/K feasibility
6. Budget feasibility and deficit tracking
7. Labour data honesty (DATA_UNAVAILABLE reporting)
8. Multi-crop portfolio aggregation
9. Multi-crop land overflow constraint (total land > farm land)
10. Preservation of all constraint violations
11. Purity: FarmProfile is never mutated
12. Scenario compatibility: baseline vs drought-adjusted water vs water shortage
13. Utilization percentage calculations and zero-division safety
14. Surplus and deficit calculations
15. Edge cases: zero available water, zero budget, zero labour
16. Input validation: negative land, zero land, empty allocations, unknown crops
"""
import copy
import pytest

from engine.profile import FarmProfile, get_demo_farm_profile
from engine.scenario_simulator import get_predefined_scenarios, apply_scenario
from engine.resource_calculator import (
    TONNE_TO_QUINTAL,
    MM_TO_M3_PER_HA,
    LITERS_PER_M3,
    LITERS_PER_MM_HA,
    revenue_per_ha,
    water_mm_to_m3_per_ha,
    water_mm_to_liters_per_ha,
    m3_to_liters,
    liters_to_m3,
    CropResourceProfile,
    CropResourceRequirement,
    ResourceBalanceItem,
    ResourceBalance,
    ResourceCalculationReport,
    get_crop_resource_profile,
    get_all_crop_resource_profiles,
    calculate_crop_requirement,
    compute_resource_balance,
    calculate_crop_resources,
    calculate_portfolio_resources,
)


class TestBasicPerHectareAndUnitCalculations:
    """Verifies per-hectare requirement parsing, unit conversions, and formula scaling."""

    def test_unit_conversion_identities(self):
        # 1 mm depth over 1 ha = 10 m³ = 10,000 liters
        assert water_mm_to_m3_per_ha(1.0) == 10.0
        assert water_mm_to_liters_per_ha(1.0) == 10000.0
        assert m3_to_liters(1.0) == 1000.0
        assert liters_to_m3(1000.0) == 1.0

        # Worked agronomic check: 1200 mm for rice = 12,000 m³/ha = 12,000,000 L/ha
        assert water_mm_to_liters_per_ha(1200.0) == 12000000.0

    def test_crop_resource_profile_loading(self):
        rice_profile = get_crop_resource_profile("rice")
        assert rice_profile is not None
        assert rice_profile.crop_name == "rice"
        assert rice_profile.water_req_mm == 1200.0
        assert rice_profile.water_per_ha_liters == 1200.0 * LITERS_PER_MM_HA
        assert rice_profile.nitrogen_per_ha_kg == 120.0
        assert rice_profile.phosphorus_per_ha_kg == 60.0
        assert rice_profile.potassium_per_ha_kg == 40.0
        assert rice_profile.cost_per_ha_inr == 35000.0
        # Labour is not in crops_profile.json
        assert rice_profile.labour_days_per_ha is None
        assert rice_profile.data_status == "PARTIAL_NO_LABOUR"

    def test_single_crop_scaling_formulas(self):
        # 1.5 ha of maize (from crops_profile: 500mm water, 100kg N, 50kg P, 30kg K, 25000 INR cost)
        maize_req = calculate_crop_requirement("maize", 1.5)
        assert maize_req.crop_name == "maize"
        assert maize_req.land_area_ha == 1.5
        # Water: 500 mm * 10,000 L/mm * 1.5 ha = 7,500,000 L
        assert maize_req.water_required_liters == 7500000.0
        # N: 100 * 1.5 = 150 kg
        assert maize_req.nitrogen_required_kg == 150.0
        # P: 50 * 1.5 = 75 kg
        assert maize_req.phosphorus_required_kg == 75.0
        # K: 30 * 1.5 = 45 kg
        assert maize_req.potassium_required_kg == 45.0
        # Cost: 25,000 * 1.5 = 37,500 INR
        assert maize_req.fertilizer_cost_inr == 37500.0
        assert maize_req.labour_required_days is None


class TestFeasibilityAndBalanceConstraints:
    """Verifies feasibility evaluation, deficit detection, and constraint violation logging."""

    def test_sufficient_resources_feasible(self):
        # Demo profile: 2 ha, water 100,000 L, N 160 kg, P 80 kg, K 100 kg, budget 100,000 INR
        # Chickpea on 1.0 ha: 350 mm = 3,500,000 L (would exceed 100,000 L water!)
        # Let's test with a profile configured with abundant resources
        profile = get_demo_farm_profile()
        profile_dict = profile.model_dump()
        profile_dict["available_water"] = 5000000.0  # 5,000,000 L
        profile_dict["available_n_kg"] = 200.0
        profile_dict["available_p_kg"] = 200.0
        profile_dict["available_k_kg"] = 200.0
        profile_dict["available_budget_inr"] = 200000.0
        rich_profile = FarmProfile(**profile_dict)

        report = calculate_crop_resources("chickpea", 1.0, rich_profile)
        assert report.is_feasible is True
        assert report.balance.overall_feasible is True
        assert len(report.constraint_violations) == 0
        assert report.balance.water.is_feasible is True
        assert report.balance.nitrogen.is_feasible is True
        assert report.balance.budget.is_feasible is True

    def test_insufficient_water_detected(self):
        # Demo farm has 100,000 L available water.
        # Rice on 1.0 ha requires 1200 mm = 12,000,000 L.
        demo = get_demo_farm_profile()
        report = calculate_crop_resources("rice", 1.0, demo)

        assert report.is_feasible is False
        assert report.balance.overall_feasible is False
        assert report.balance.water.is_feasible is False
        assert report.balance.water.status == "INSUFFICIENT"
        assert report.balance.water.surplus_or_deficit < 0
        # Deficit = 12,000,000 - 100,000 = 11,900,000 L short
        assert report.balance.water.remaining == 100000.0 - 12000000.0
        assert any("Water shortage" in v for v in report.constraint_violations)

    def test_insufficient_nutrients_detected(self):
        # Demo profile: N = 160 kg, P = 80 kg, K = 100 kg.
        # Banana on 1.0 ha requires 200 kg N, 80 kg P, 220 kg K.
        # Exceeds N (200 > 160) and K (220 > 100).
        demo = get_demo_farm_profile()
        report = calculate_crop_resources("banana", 1.0, demo)

        assert report.balance.nitrogen.is_feasible is False
        assert report.balance.nitrogen.remaining == -40.0  # 160 - 200
        assert report.balance.potassium.is_feasible is False
        assert report.balance.potassium.remaining == -120.0  # 100 - 220
        # P is exactly 80 kg, so remaining is 0 kg (feasible)
        assert report.balance.phosphorus.is_feasible is True
        assert report.balance.phosphorus.remaining == 0.0

        # Must preserve BOTH violations
        violations = " ".join(report.constraint_violations)
        assert "Nitrogen deficit" in violations
        assert "Potassium deficit" in violations

    def test_insufficient_budget_detected(self):
        demo = get_demo_farm_profile()
        # Set budget to 20,000 INR
        profile_dict = demo.model_dump()
        profile_dict["available_budget_inr"] = 20000.0
        tight_budget_profile = FarmProfile(**profile_dict)

        # Grapes on 1.0 ha requires 90,000 INR cost
        report = calculate_crop_resources("grapes", 1.0, tight_budget_profile)
        assert report.balance.budget.is_feasible is False
        assert report.balance.budget.remaining == -70000.0  # 20,000 - 90,000
        assert any("Budget deficit" in v for v in report.constraint_violations)

    def test_labour_data_honesty(self):
        """Verifies that unrecorded labour data is reported as DATA_UNAVAILABLE and not fabricated."""
        demo = get_demo_farm_profile()
        report = calculate_crop_resources("rice", 1.0, demo)
        assert report.balance.labour.status == "DATA_UNAVAILABLE"
        assert report.balance.labour.required is None
        assert report.balance.labour.utilization_pct is None
        assert "not recorded" in report.balance.labour.details


class TestMultiCropPortfolioCalculations:
    """Verifies arithmetic aggregation across multi-crop portfolios."""

    def test_portfolio_resource_aggregation(self):
        demo = get_demo_farm_profile()
        # Allocate: Rice 0.5 ha, Maize 0.5 ha
        # Rice 0.5 ha: 600mm water = 6,000,000 L, 60kg N, 30kg P, 20kg K, 17,500 cost
        # Maize 0.5 ha: 250mm water = 2,500,000 L, 50kg N, 25kg P, 15kg K, 12,500 cost
        allocations = {"rice": 0.5, "maize": 0.5}
        report = calculate_portfolio_resources(allocations, demo)

        assert report.entity_type == "PORTFOLIO"
        assert report.total_land_used_ha == 1.0
        assert report.land_remaining_ha == float(demo.land_area_ha) - 1.0
        assert report.total_water_liters == 6000000.0 + 2500000.0
        assert report.total_n_kg == 60.0 + 50.0
        assert report.total_p_kg == 30.0 + 25.0
        assert report.total_k_kg == 20.0 + 15.0
        assert report.total_cost_inr == 17500.0 + 12500.0

    def test_portfolio_land_overflow_infeasible(self):
        demo = get_demo_farm_profile()  # land_area_ha = 2.0 ha
        # Allocate 2.5 ha total (exceeds farm capacity)
        allocations = {"rice": 1.5, "maize": 1.0}
        report = calculate_portfolio_resources(allocations, demo)

        assert report.is_feasible is False
        assert report.balance.land.is_feasible is False
        assert report.balance.land.remaining == -0.5
        assert any("Land constraint exceeded" in v for v in report.constraint_violations)

    def test_portfolio_does_not_optimize(self):
        """Verifies that engine merely aggregates and does NOT alter allocation numbers."""
        demo = get_demo_farm_profile()
        allocations = {"chickpea": 0.3, "mungbean": 0.4}
        report = calculate_portfolio_resources(allocations, demo)
        assert report.crop_allocations == {"chickpea": 0.3, "mungbean": 0.4}


class TestScenarioCompatibility:
    """Verifies compatibility with Phase 5 transformed scenario conditions."""

    def test_baseline_vs_drought_scenario_water_balance(self):
        baseline_profile = get_demo_farm_profile()  # 100,000 L
        drought_scen = get_predefined_scenarios()[1]  # -20% water -> 80,000 L

        drought_profile, err = apply_scenario(baseline_profile, drought_scen)
        assert err is None
        assert drought_profile.water_liters == 80000.0

        # Chickpea on 0.02 ha = 350 mm * 10,000 * 0.02 = 70,000 L
        # Baseline (100,000 L) -> Remaining = 30,000 L (Feasible)
        base_rep = calculate_crop_resources("chickpea", 0.02, baseline_profile)
        assert base_rep.balance.water.is_feasible is True
        assert base_rep.balance.water.available == 100000.0
        assert base_rep.balance.water.remaining == 30000.0

        # Drought (80,000 L) -> Remaining = 10,000 L (Feasible, but tighter)
        drought_rep = calculate_crop_resources("chickpea", 0.02, drought_profile)
        assert drought_rep.balance.water.is_feasible is True
        assert drought_rep.balance.water.available == 80000.0
        assert drought_rep.balance.water.remaining == 10000.0

    def test_water_shortage_scenario_flips_feasibility(self):
        baseline_profile = get_demo_farm_profile()  # 100,000 L
        water_shortage_scen = get_predefined_scenarios()[3]  # -30% water -> 70,000 L

        shortage_profile, _ = apply_scenario(baseline_profile, water_shortage_scen)
        assert shortage_profile.water_liters == 70000.0

        # Water requirement = 80,000 L (e.g. 0.02 ha of pigeonpeas = 400 mm * 10,000 * 0.02 = 80,000 L)
        # Feasible under Baseline (100,000 L)
        base_rep = calculate_crop_resources("pigeonpeas", 0.02, baseline_profile)
        assert base_rep.balance.water.is_feasible is True

        # Infeasible under Water Shortage (70,000 L < 80,000 L)
        shortage_rep = calculate_crop_resources("pigeonpeas", 0.02, shortage_profile)
        assert shortage_rep.balance.water.is_feasible is False
        assert shortage_rep.balance.water.remaining == -10000.0


class TestPurityAndEdgeCases:
    """Verifies FarmProfile immutability, zero-resource handling, and input error checking."""

    def test_farm_profile_purity(self):
        """CRITICAL: Verifies original FarmProfile is not modified in any way."""
        profile = get_demo_farm_profile()
        profile_copy = copy.deepcopy(profile.model_dump())

        _ = calculate_crop_resources("rice", 1.0, profile)
        _ = calculate_portfolio_resources({"rice": 0.5, "maize": 0.5}, profile)

        assert profile.model_dump() == profile_copy

    def test_zero_available_resources(self):
        profile = get_demo_farm_profile()
        profile_dict = profile.model_dump()
        profile_dict["available_water"] = 0.0
        profile_dict["available_budget_inr"] = 0.0
        profile_dict["available_labour_days"] = 0.0
        zero_profile = FarmProfile(**profile_dict)

        report = calculate_crop_resources("rice", 0.5, zero_profile)
        assert report.balance.water.is_feasible is False
        assert report.balance.water.utilization_pct is None  # Handled safely without ZeroDivisionError
        assert report.balance.budget.is_feasible is False
        assert report.balance.budget.utilization_pct is None

    def test_invalid_land_area_rejected(self):
        profile = get_demo_farm_profile()
        with pytest.raises(ValueError, match="greater than zero"):
            calculate_crop_resources("rice", 0.0, profile)

        with pytest.raises(ValueError, match="greater than zero"):
            calculate_crop_resources("rice", -1.0, profile)

        with pytest.raises(ValueError, match="greater than zero"):
            calculate_portfolio_resources({"rice": -0.5}, profile)

    def test_empty_or_unknown_crop_rejected(self):
        profile = get_demo_farm_profile()
        with pytest.raises(ValueError, match="non-empty string"):
            calculate_crop_resources("", 1.0, profile)

        with pytest.raises(ValueError, match="not found in config"):
            calculate_crop_resources("unknown_crop_xyz", 1.0, profile)

        with pytest.raises(ValueError, match="non-empty dictionary"):
            calculate_portfolio_resources({}, profile)

    def test_utilization_percentages_calculated_accurately(self):
        profile = get_demo_farm_profile()
        profile_dict = profile.model_dump()
        profile_dict["available_water"] = 200000.0  # 200,000 L
        profile_dict["available_n_kg"] = 200.0       # 200 kg
        test_profile = FarmProfile(**profile_dict)

        # Chickpea 1.0 ha: water = 3,500,000 L, N = 20 kg
        # Let's test on 0.02 ha: water = 70,000 L, N = 0.4 kg
        # Water utilization: 70,000 / 200,000 * 100 = 35.0%
        # N utilization: 0.4 / 200.0 * 100 = 0.2%
        report = calculate_crop_resources("chickpea", 0.02, test_profile)
        assert report.balance.water.utilization_pct == 35.0
        assert report.balance.nitrogen.utilization_pct == 0.2

    def test_surplus_and_deficit_exact_values(self):
        profile = get_demo_farm_profile()
        profile_dict = profile.model_dump()
        profile_dict["available_n_kg"] = 100.0
        profile_dict["available_p_kg"] = 30.0
        test_profile = FarmProfile(**profile_dict)

        # Maize on 1.0 ha requires N = 100 kg, P = 50 kg
        report = calculate_crop_resources("maize", 1.0, test_profile)
        # N: available 100, required 100 -> surplus/deficit = 0.0 (exact match)
        assert report.balance.nitrogen.surplus_or_deficit == 0.0
        assert report.balance.nitrogen.is_feasible is True
        # P: available 30, required 50 -> surplus/deficit = -20.0 (deficit)
        assert report.balance.phosphorus.surplus_or_deficit == -20.0
        assert report.balance.phosphorus.is_feasible is False

    def test_all_22_crop_profiles_loaded_completely(self):
        profiles = get_all_crop_resource_profiles()
        assert len(profiles) == 22
        for crop_name, p in profiles.items():
            assert p.water_per_ha_liters > 0
            assert p.nitrogen_per_ha_kg >= 0
            assert p.phosphorus_per_ha_kg >= 0
            assert p.potassium_per_ha_kg >= 0
            assert p.cost_per_ha_inr is not None and p.cost_per_ha_inr > 0
            # Labour is honestly reported as None across all 22 crops
            assert p.labour_days_per_ha is None
            assert p.data_status == "PARTIAL_NO_LABOUR"

    def test_revenue_per_ha_validation_and_calculation(self):
        # 4 tonnes/ha at 2500 INR/quintal (10 quintals/t) = 4 * 10 * 2500 = 100,000 INR
        assert revenue_per_ha(4.0, 2500.0) == 100000.0
        with pytest.raises(ValueError, match="non-negative"):
            revenue_per_ha(-1.0, 2500.0)
        with pytest.raises(ValueError, match="non-negative"):
            revenue_per_ha(4.0, -100.0)

    def test_negative_unit_conversions_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            water_mm_to_m3_per_ha(-5.0)
        with pytest.raises(ValueError, match="non-negative"):
            water_mm_to_liters_per_ha(-5.0)
        with pytest.raises(ValueError, match="non-negative"):
            m3_to_liters(-10.0)
        with pytest.raises(ValueError, match="non-negative"):
            liters_to_m3(-100.0)
