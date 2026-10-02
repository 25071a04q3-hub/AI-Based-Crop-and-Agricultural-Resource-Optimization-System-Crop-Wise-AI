"""
FarmTwin Phase 10 Automated Tests — Adaptive Reserve & Mid-Season Re-Optimization Engine.

Covers:
1. Reserve calculations (available, used, remaining reserve, reserve_pct)
2. Exhausted reserve detection (0% reserve)
3. Critical reserve detection (<10% reserve)
4. Healthy reserve detection (>=25% reserve)
5. General trigger evaluation
6. Water shift trigger detection
7. Budget shift trigger detection
8. Fertilizer shift trigger detection
9. Climate scenario change trigger detection
10. Stability score calculation across scenarios
11. Stability classification thresholds (HIGH, MODERATE, LOW)
12. Adaptive recommendations generation
13. Mid-season recourse simulation execution
14. Empty inputs handling
15. Infeasible optimization inputs handling
16. UI-safe serializable outputs
17. Deterministic behavior & reproducibility
18. Integration with Phase 7 FarmOptimizationResult
19. Integration with Phase 8 PortfolioAnalysisResult
20. Integration with Phase 9 BottleneckAnalysisResult
21. Full end-to-end pipeline compatibility (Profile -> Suitability -> Optimizer -> Portfolio -> Bottleneck -> Adaptive)
"""
import pytest
from engine.profile import get_demo_farm_profile, FarmProfile
from engine.optimizer import (
    optimize_farm_allocation,
    FarmOptimizationResult,
    OptimizationMode,
    OptimizationObjective,
)
from engine.portfolio_intelligence import generate_portfolio_report
from engine.bottleneck_analysis import generate_bottleneck_report
from engine.adaptive_reserve import (
    ReoptimizationTriggerConfig,
    AdaptiveReserveResult,
    analyze_resource_reserves,
    identify_critical_reserves,
    evaluate_reoptimization_triggers,
    analyze_plan_stability,
    generate_adaptive_recommendations,
    simulate_resource_change,
    generate_adaptive_report,
)


@pytest.fixture
def mock_phase7_result():
    """Mock Phase 7 result where water is 100% exhausted and phosphorus is at 7.9% reserve margin (critical)."""
    return FarmOptimizationResult(
        status="OPTIMAL",
        optimization_mode=OptimizationMode.RESOURCE_ONLY,
        objective=OptimizationObjective.RESOURCE_SUITABILITY,
        candidate_crops=["chickpea", "pigeonpeas"],
        crop_allocations_ha={"chickpea": 0.5, "pigeonpeas": 0.4},
        total_land_used_ha=0.9,
        land_remaining_ha=1.1,
        resource_usage={
            "land_ha": 0.9,
            "water_liters": 100000.0,
            "nitrogen_kg": 18.0,
            "phosphorus_kg": 54.0,
            "potassium_kg": 18.0,
            "budget_inr": 17700.0,
            "labour_days": 0.0,
        },
        resource_remaining={
            "land_ha": 1.1,
            "water_liters": 0.0,
            "nitrogen_kg": 142.0,
            "phosphorus_kg": 4.6,
            "potassium_kg": 82.0,
            "budget_inr": 82300.0,
            "labour_days": 0.0,
        },
        resource_utilization_pct={
            "land_ha": 45.0,
            "water_liters": 100.0,
            "nitrogen_kg": 11.25,
            "phosphorus_kg": 92.1,
            "potassium_kg": 18.0,
            "budget_inr": 17.7,
            "labour_days": None,
        },
        feasibility=True,
        constraint_violations=[],
        objective_value=0.627,
        expected_profit_inr=None,
        risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
        explanation="Water saturated allocation",
        binding_resources=["water_liters"],
        details={},
    )


class TestReserveAnalysisAndCriticalDetection:
    """Tests 1-4: Reserve buffer calculations and health classification."""

    def test_reserve_calculations(self, mock_phase7_result):
        """Calculates available, used, reserve, and reserve_pct accurately."""
        reserves = analyze_resource_reserves(mock_phase7_result)
        assert "water_liters" in reserves
        assert reserves["water_liters"]["available"] == 100000.0
        assert reserves["water_liters"]["used"] == 100000.0
        assert reserves["water_liters"]["reserve"] == 0.0
        assert reserves["water_liters"]["reserve_pct"] == 0.0

        assert "land_ha" in reserves
        assert reserves["land_ha"]["available"] == 2.0
        assert reserves["land_ha"]["used"] == 0.9
        assert reserves["land_ha"]["reserve"] == 1.1
        assert reserves["land_ha"]["reserve_pct"] == 55.0

    def test_exhausted_reserve_detection(self, mock_phase7_result):
        """0% reserve must be classified as EXHAUSTED."""
        reserves = analyze_resource_reserves(mock_phase7_result)
        critical = identify_critical_reserves(reserves)
        assert critical["water_liters"] == "EXHAUSTED"

    def test_critical_reserve_detection(self, mock_phase7_result):
        """Reserve < 10% (e.g. phosphorus with 4.6 kg left out of 58.6 kg = 7.85%) is CRITICAL."""
        reserves = analyze_resource_reserves(mock_phase7_result)
        critical = identify_critical_reserves(reserves)
        assert critical["phosphorus_kg"] == "CRITICAL"

    def test_healthy_reserve_detection(self, mock_phase7_result):
        """Reserve >= 25% (e.g. Land with 55% reserve) is classified as HEALTHY."""
        reserves = analyze_resource_reserves(mock_phase7_result)
        critical = identify_critical_reserves(reserves)
        assert critical["land_ha"] == "HEALTHY"
        assert critical["nitrogen_kg"] == "HEALTHY"
        assert critical["budget_inr"] == "HEALTHY"


class TestReoptimizationTriggers:
    """Tests 5-9: Trigger condition evaluations."""

    def test_trigger_evaluation_stable_when_no_shifts(self):
        """When observed conditions equal current conditions, status is PLAN_STABLE."""
        profile = get_demo_farm_profile()
        status, conds = evaluate_reoptimization_triggers(current_profile=profile)
        assert status == "PLAN_STABLE"
        assert len(conds) > 0

    def test_water_trigger_tripped(self):
        """A >10% water reduction trips the water re-optimization trigger."""
        profile = get_demo_farm_profile()
        # available_water on demo profile is 100,000 L -> shift to 85,000 L (-15%)
        observed = {"available_water": 85000.0}
        status, conds = evaluate_reoptimization_triggers(profile, observed_conditions=observed)
        assert status == "REOPTIMIZATION_REQUIRED"
        assert any("water" in c.lower() for c in conds)

    def test_budget_trigger_tripped(self):
        """A >20% budget reduction trips the budget trigger."""
        profile = get_demo_farm_profile()
        # budget on demo profile is 100,000 -> shift to 75,000 (-25%)
        observed = {"available_budget_inr": 75000.0}
        status, conds = evaluate_reoptimization_triggers(profile, observed_conditions=observed)
        assert status == "REOPTIMIZATION_REQUIRED"
        assert any("budget" in c.lower() for c in conds)

    def test_fertilizer_trigger_tripped(self):
        """A >15% fertilizer change trips the fertilizer trigger."""
        profile = get_demo_farm_profile()
        # available_n_kg on demo profile is 160 kg -> shift to 120 kg (-25%)
        observed = {"available_n_kg": 120.0}
        status, conds = evaluate_reoptimization_triggers(profile, observed_conditions=observed)
        assert status == "REOPTIMIZATION_REQUIRED"
        assert any("nitrogen" in c.lower() for c in conds)

    def test_scenario_trigger_tripped(self):
        """Switching from Baseline to a stress scenario trips the climate trigger."""
        profile = get_demo_farm_profile()
        status, conds = evaluate_reoptimization_triggers(profile, active_scenario="Drought")
        assert status == "REOPTIMIZATION_REQUIRED"
        assert any("drought" in c.lower() for c in conds)


class TestPlanStabilityAnalysis:
    """Tests 10-11: Plan stability metric across stress scenarios."""

    def test_plan_stability_calculation_and_classification(self, mock_phase7_result):
        """Measures maximum allocation shift across scenarios and classifies stability."""
        scenarios = {
            "Drought": FarmOptimizationResult(
                status="OPTIMAL",
                optimization_mode=OptimizationMode.RESOURCE_ONLY,
                objective=OptimizationObjective.RESOURCE_SUITABILITY,
                candidate_crops=["chickpea", "pigeonpeas"],
                crop_allocations_ha={"chickpea": 0.45, "pigeonpeas": 0.35},
                total_land_used_ha=0.8,
                land_remaining_ha=1.2,
                resource_usage={},
                resource_remaining={},
                resource_utilization_pct={},
                feasibility=True,
                constraint_violations=[],
                objective_value=0.55,
                expected_profit_inr=None,
                risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
                explanation="Drought",
            )
        }
        score, status, expl = analyze_plan_stability(mock_phase7_result, scenarios)
        assert score is not None
        assert score >= 0.85
        assert status == "HIGH_STABILITY"
        assert "High plan stability" in expl

    def test_plan_stability_low_classification(self, mock_phase7_result):
        """Large allocation contraction yields LOW_STABILITY."""
        scenarios = {
            "Severe Drought": FarmOptimizationResult(
                status="OPTIMAL",
                optimization_mode=OptimizationMode.RESOURCE_ONLY,
                objective=OptimizationObjective.RESOURCE_SUITABILITY,
                candidate_crops=["chickpea", "pigeonpeas"],
                crop_allocations_ha={"chickpea": 0.1, "pigeonpeas": 0.05},
                total_land_used_ha=0.15,
                land_remaining_ha=1.85,
                resource_usage={},
                resource_remaining={},
                resource_utilization_pct={},
                feasibility=True,
                constraint_violations=[],
                objective_value=0.1,
                expected_profit_inr=None,
                risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
                explanation="Severe Drought",
            )
        }
        score, status, _ = analyze_plan_stability(mock_phase7_result, scenarios)
        assert score is not None
        assert score < 0.60
        assert status == "LOW_STABILITY"

    def test_plan_stability_data_unavailable_without_scenarios(self, mock_phase7_result):
        """Omitted scenario dict returns DATA_UNAVAILABLE."""
        score, status, _ = analyze_plan_stability(mock_phase7_result, None)
        assert score is None
        assert status == "DATA_UNAVAILABLE"


class TestAdaptiveRecommendationsAndSimulation:
    """Tests 12-17: Recommendations, mid-season simulation, and edge cases."""

    def test_adaptive_recommendations_generation(self, mock_phase7_result):
        """Generates clear, actionable buffer advice for exhausted and healthy reserves."""
        reserves = analyze_resource_reserves(mock_phase7_result)
        critical = identify_critical_reserves(reserves)
        recs = generate_adaptive_recommendations(
            reserve_summary=reserves,
            critical_reserves=critical,
            stability_status="HIGH_STABILITY",
            trigger_status="PLAN_STABLE",
            trigger_conditions=[]
        )
        assert len(recs) >= 2
        rec_text = " ".join(recs)
        assert "Water Liters" in rec_text
        assert "Land Ha" in rec_text

    def test_simulate_resource_change_execution(self):
        """Mid-season simulation re-runs solver under -20% water and reports exact differences."""
        profile = get_demo_farm_profile()
        candidates = {"chickpea": 0.71, "pigeonpeas": 0.68}
        sim = simulate_resource_change(profile, candidates, top_n=2, resource_changes_pct={"available_water": -20.0})

        assert "baseline_land_ha" in sim
        assert "updated_land_ha" in sim
        assert sim["updated_land_ha"] < sim["baseline_land_ha"]
        assert sim["land_delta_ha"] < 0
        assert sim["updated_status"] == "OPTIMAL"

    def test_infeasible_inputs_handling(self):
        """Infeasible plans are processed safely without exceptions."""
        infeasible_res = FarmOptimizationResult(
            status="INFEASIBLE",
            optimization_mode=OptimizationMode.RESOURCE_ONLY,
            objective=OptimizationObjective.RESOURCE_SUITABILITY,
            candidate_crops=[],
            crop_allocations_ha={},
            total_land_used_ha=0.0,
            land_remaining_ha=2.0,
            resource_usage={},
            resource_remaining={},
            resource_utilization_pct={},
            feasibility=False,
            constraint_violations=["Contradictory constraints"],
            objective_value=None,
            expected_profit_inr=None,
            risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
            explanation="Infeasible",
        )
        report = generate_adaptive_report(infeasible_res)
        assert isinstance(report, AdaptiveReserveResult)
        assert report.trigger_status == "PLAN_STABLE"

    def test_empty_inputs_handling(self):
        """Zero allocation results yield a valid report with zero used reserves."""
        empty_res = FarmOptimizationResult(
            status="OPTIMAL",
            optimization_mode=OptimizationMode.RESOURCE_ONLY,
            objective=OptimizationObjective.RESOURCE_SUITABILITY,
            candidate_crops=[],
            crop_allocations_ha={},
            total_land_used_ha=0.0,
            land_remaining_ha=2.0,
            resource_usage={"water_liters": 0.0},
            resource_remaining={"water_liters": 100000.0},
            resource_utilization_pct={"water_liters": 0.0},
            feasibility=True,
            constraint_violations=[],
            objective_value=0.0,
            expected_profit_inr=None,
            risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
            explanation="Empty",
        )
        report = generate_adaptive_report(empty_res)
        assert report.critical_reserves["water_liters"] == "HEALTHY"

    def test_ui_safe_serializable_structure(self, mock_phase7_result):
        """AdaptiveReserveResult serializes cleanly to dict/JSON for UI and APIs."""
        report = generate_adaptive_report(mock_phase7_result)
        d = report.model_dump()
        assert isinstance(d, dict)
        assert "reserve_summary" in d
        assert "critical_reserves" in d
        assert "trigger_status" in d

    def test_deterministic_behavior(self, mock_phase7_result):
        """Repeated evaluations of the same inputs yield identical reports."""
        r1 = generate_adaptive_report(mock_phase7_result)
        r2 = generate_adaptive_report(mock_phase7_result)
        assert r1.trigger_status == r2.trigger_status
        assert r1.critical_reserves == r2.critical_reserves
        assert r1.explanation == r2.explanation


class TestFullPipelineIntegration:
    """Tests 18-21: End-to-end integration across all phases."""

    def test_full_pipeline_phase1_through_phase10(self):
        """Executes full live pipeline: Profile -> Optimize -> Portfolio -> Bottleneck -> Adaptive."""
        profile = get_demo_farm_profile()
        candidates = {"chickpea": 0.71, "pigeonpeas": 0.68, "maize": 0.76}

        # 1. Phase 7 Optimization
        opt_res = optimize_farm_allocation(profile, candidates, top_n=3)
        assert opt_res.feasibility is True

        # 2. Phase 8 Portfolio Intelligence
        port_res = generate_portfolio_report(opt_res)
        assert port_res.total_crops > 0

        # 3. Phase 9 Bottleneck Analysis
        bottle_res = generate_bottleneck_report(opt_res, profile, candidates, top_n=3)
        assert bottle_res.primary_bottleneck == "water_liters"

        # 4. Phase 10 Adaptive Reserve & Re-Optimization
        adapt_res = generate_adaptive_report(
            optimization_result=opt_res,
            farm_profile=profile,
            candidate_crops=candidates,
        )

        assert isinstance(adapt_res, AdaptiveReserveResult)
        assert "water_liters" in adapt_res.reserve_summary
        assert adapt_res.critical_reserves["water_liters"] == "EXHAUSTED"
        assert adapt_res.critical_reserves["land_ha"] == "HEALTHY"
        assert len(adapt_res.adaptive_recommendations) > 0
        assert len(adapt_res.explanation) > 50

    def test_low_reserve_detection_threshold(self):
        """Reserve between 10% and 25% is classified as LOW."""
        mock_summary = {
            "potassium_kg": {"available": 100.0, "used": 82.0, "reserve": 18.0, "reserve_pct": 18.0}
        }
        res = identify_critical_reserves(mock_summary)
        assert res["potassium_kg"] == "LOW"

    def test_simulate_resource_change_budget_reduction(self):
        """Mid-season simulation with budget reduction runs without error and reports deltas."""
        profile = get_demo_farm_profile()
        candidates = {"chickpea": 0.71, "pigeonpeas": 0.68}
        sim = simulate_resource_change(profile, candidates, top_n=2, resource_changes_pct={"available_budget_inr": -30.0})
        assert "baseline_land_ha" in sim
        assert "updated_land_ha" in sim
        assert "applied_changes" in sim
