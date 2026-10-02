"""
FarmTwin Phase 9 Automated Tests — Bottleneck Analysis & Shadow Value Intelligence Engine.

Covers:
1. Binding resource detection (>= 99%)
2. Near-binding detection (90% - 99%)
3. Underutilized detection (< 60%)
4. Primary bottleneck selection
5. Secondary bottleneck ordering by descending utilization
6. Sensitivity analysis execution (+10%, +20% re-optimization runs)
7. Resource lever ranking logic
8. Explanation generation
9. Shadow value unavailable handling (when unexposed or infeasible)
10. Actual dual value handling from HiGHS solver
11. Empty allocation handling (zero land cultivated)
12. Infeasible optimization handling
13. UI-safe serializable outputs
14. Deterministic behavior
15. Integration with Phase 7 FarmOptimizationResult
16. Integration with Phase 8 PortfolioAnalysisResult
17. Edge cases (all underutilized, missing utilization keys)
18. Warning generation for binding / near-binding constraints
19. Full end-to-end pipeline compatibility (Profile -> Suitability -> Optimizer -> Portfolio -> Bottleneck)
20. Data honesty verification (no fake INR shadow prices, no fabricated economics)
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
from engine.bottleneck_analysis import (
    BottleneckAnalysisResult,
    analyze_resource_constraints,
    identify_primary_bottleneck,
    identify_secondary_bottlenecks,
    analyze_shadow_values,
    run_resource_sensitivity_analysis,
    rank_resource_levers,
    generate_bottleneck_report,
)


@pytest.fixture
def mock_water_binding_result():
    """Returns a mock result where water is binding (100%) and phosphorus is near-binding (92%)."""
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
        details={
            "solver_method": "highs",
            "solver_message": "Optimization terminated successfully",
            "iterations": 3,
            "ineqlin_marginals": [0.0, -0.00000627, 0.0, 0.0, 0.0, 0.0],
            "constraint_names": ["land_ha", "water_liters", "nitrogen_kg", "phosphorus_kg", "potassium_kg", "budget_inr"],
        },
    )


class TestConstraintAuditingAndBottleneckDetection:
    """Tests 1-5: Constraint state classifications and bottleneck identification."""

    def test_binding_resource_detection(self):
        """Utilization >= 99% must be classified as BINDING."""
        utils = {"water_liters": 100.0, "land_ha": 45.0}
        states = analyze_resource_constraints(utils)
        assert states["water_liters"] == "BINDING"
        assert states["land_ha"] == "UNDERUTILIZED"

    def test_near_binding_detection(self):
        """Utilization in [90%, 99%) must be classified as NEAR_BINDING."""
        utils = {"phosphorus_kg": 94.5, "budget_inr": 75.0}
        states = analyze_resource_constraints(utils)
        assert states["phosphorus_kg"] == "NEAR_BINDING"
        assert states["budget_inr"] == "ACTIVE"

    def test_underutilized_detection(self):
        """Utilization < 60% must be classified as UNDERUTILIZED."""
        utils = {"nitrogen_kg": 15.0, "potassium_kg": 20.0}
        states = analyze_resource_constraints(utils)
        assert states["nitrogen_kg"] == "UNDERUTILIZED"
        assert states["potassium_kg"] == "UNDERUTILIZED"

    def test_primary_bottleneck_selection(self, mock_water_binding_result):
        """Highest utilization constraint should be selected as primary bottleneck."""
        prim_res, prim_util, reason = identify_primary_bottleneck(mock_water_binding_result.resource_utilization_pct)
        assert prim_res == "water_liters"
        assert prim_util == 100.0
        assert "binding ceiling" in reason.lower()

    def test_secondary_bottleneck_ordering(self, mock_water_binding_result):
        """Subsequent bottlenecks must be ordered in descending utilization, excluding primary."""
        sec = identify_secondary_bottlenecks(
            mock_water_binding_result.resource_utilization_pct,
            primary_bottleneck="water_liters"
        )
        assert sec[0] == "phosphorus_kg"  # 92.1%
        assert "water_liters" not in sec


class TestShadowValueIntelligence:
    """Tests 9-10, 20: Dual variable extraction and strict honesty gating."""

    def test_actual_dual_value_extraction(self, mock_water_binding_result):
        """Authentic HiGHS dual multipliers are extracted as positive marginal rate of improvement."""
        status, shadows, expl = analyze_shadow_values(mock_water_binding_result)
        assert status == "SOLVER_DUALS_ACTIVE"
        assert "water_liters" in shadows
        assert shadows["water_liters"] == pytest.approx(0.000006, abs=1e-6)
        assert "HiGHS LP solver" in expl
        assert "not currency" in expl.lower()

    def test_shadow_values_unavailable_when_missing(self):
        """If details lacks dual multipliers, returns SHADOW_VALUES_UNAVAILABLE."""
        res = FarmOptimizationResult(
            status="OPTIMAL",
            optimization_mode=OptimizationMode.RESOURCE_ONLY,
            objective=OptimizationObjective.RESOURCE_SUITABILITY,
            candidate_crops=["chickpea"],
            crop_allocations_ha={"chickpea": 1.0},
            total_land_used_ha=1.0,
            land_remaining_ha=0.0,
            resource_usage={},
            resource_remaining={},
            resource_utilization_pct={},
            feasibility=True,
            constraint_violations=[],
            objective_value=0.7,
            expected_profit_inr=None,
            risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
            explanation="Test",
            details={},
        )
        status, shadows, expl = analyze_shadow_values(res)
        assert status == "SHADOW_VALUES_UNAVAILABLE"
        assert shadows == {}
        assert "safely withheld" in expl.lower()

    def test_infeasible_optimization_shadow_values(self):
        """Infeasible plans return SHADOW_VALUES_UNAVAILABLE."""
        res = FarmOptimizationResult(
            status="INFEASIBLE",
            optimization_mode=OptimizationMode.RESOURCE_ONLY,
            objective=OptimizationObjective.RESOURCE_SUITABILITY,
            candidate_crops=["chickpea"],
            crop_allocations_ha={},
            total_land_used_ha=0.0,
            land_remaining_ha=2.0,
            resource_usage={},
            resource_remaining={},
            resource_utilization_pct={},
            feasibility=False,
            constraint_violations=["Impossible bounds"],
            objective_value=None,
            expected_profit_inr=None,
            risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
            explanation="Infeasible",
        )
        status, _, expl = analyze_shadow_values(res)
        assert status == "SHADOW_VALUES_UNAVAILABLE"
        assert "infeasible" in expl.lower()

    def test_no_fake_inr_shadow_prices(self, mock_water_binding_result):
        """Shadow value outputs must never contain fake Rupee or INR values."""
        _, _, expl = analyze_shadow_values(mock_water_binding_result)
        assert "₹" not in expl
        assert "INR" not in expl


class TestSensitivityAnalysisAndLeverRanking:
    """Tests 6-7: What-If re-optimization experiments and lever ranking."""

    def test_sensitivity_analysis_execution(self):
        """Sensitivity experiments re-run optimizer with +10% and +20% expansions."""
        profile = get_demo_farm_profile()
        candidates = {"chickpea": 0.71, "pigeonpeas": 0.68}
        sens = run_resource_sensitivity_analysis(profile, candidates, top_n=2)

        assert "water_liters" in sens
        assert "+10%" in sens["water_liters"]
        assert "+20%" in sens["water_liters"]
        assert "objective_delta" in sens["water_liters"]["+10%"]
        assert "land_delta_ha" in sens["water_liters"]["+10%"]

    def test_resource_lever_ranking_identifies_water_leverage(self):
        """When water is binding, +10% water expansion yields the top-ranked management lever."""
        profile = get_demo_farm_profile()
        candidates = {"chickpea": 0.71, "pigeonpeas": 0.68}
        sens = run_resource_sensitivity_analysis(profile, candidates, top_n=2)
        ranking = rank_resource_levers(sens)

        assert len(ranking) >= 4
        # Top ranked lever must have rank 1
        assert ranking[0]["rank"] == 1
        # Water is the binding constraint on the demo profile, so it should deliver the top improvement
        assert ranking[0]["resource"] == "water_liters"
        assert ranking[0]["objective_delta_pct_10"] > 5.0
        assert ranking[0]["impact_label"] == "HIGH_IMPACT"


class TestReportGenerationAndExplanations:
    """Tests 8, 11, 13, 14, 17, 18: Bottleneck report assembly, warnings, edge cases."""

    def test_generate_bottleneck_report_structure(self, mock_water_binding_result):
        """BottleneckAnalysisResult includes all required fields with proper types."""
        profile = get_demo_farm_profile()
        cands = {"chickpea": 0.71, "pigeonpeas": 0.68}
        report = generate_bottleneck_report(
            optimization_result=mock_water_binding_result,
            farm_profile=profile,
            candidate_crops=cands,
        )

        assert isinstance(report, BottleneckAnalysisResult)
        assert report.primary_bottleneck == "water_liters"
        assert report.primary_bottleneck_utilization == 100.0
        assert "phosphorus_kg" in report.secondary_bottlenecks
        assert report.constraint_states["water_liters"] == "BINDING"
        assert report.shadow_value_status == "SOLVER_DUALS_ACTIVE"
        assert len(report.resource_lever_ranking) > 0
        assert len(report.warnings) > 0
        assert len(report.explanation) > 50

    def test_warning_compilation(self, mock_water_binding_result):
        """Binding and near-binding constraints generate explicit warning alerts."""
        report = generate_bottleneck_report(mock_water_binding_result)
        warning_text = " ".join(report.warnings)
        assert "Binding constraint: Water Liters is 100% exhausted" in warning_text
        assert "Near-binding" in warning_text

    def test_empty_allocation_handling(self):
        """Zero allocation farm yields an appropriate underutilized or unconstrained report."""
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
            resource_utilization_pct={"water_liters": 0.0, "land_ha": 0.0},
            feasibility=True,
            constraint_violations=[],
            objective_value=0.0,
            expected_profit_inr=None,
            risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
            explanation="Empty",
        )
        report = generate_bottleneck_report(empty_res)
        assert report.constraint_states["water_liters"] == "UNDERUTILIZED"
        assert "ample remaining capacity" in report.explanation.lower()

    def test_all_underutilized_edge_case(self):
        """When all resources are < 60%, reason indicates abundant headroom."""
        utils = {"water_liters": 30.0, "land_ha": 25.0, "budget_inr": 10.0}
        _, _, reason = identify_primary_bottleneck(utils)
        assert "underutilized" in reason.lower()
        assert "ample resource slack" in reason.lower()

    def test_deterministic_bottleneck_report(self, mock_water_binding_result):
        """Repeated evaluations of the same result produce identical reports."""
        r1 = generate_bottleneck_report(mock_water_binding_result)
        r2 = generate_bottleneck_report(mock_water_binding_result)
        assert r1.primary_bottleneck == r2.primary_bottleneck
        assert r1.constraint_states == r2.constraint_states
        assert r1.explanation == r2.explanation


class TestPipelineEndToEndIntegration:
    """Tests 15-16, 19: Full integration across Phases 1 to 9."""

    def test_full_pipeline_phase1_through_phase9(self):
        """Executes full live pipeline: Profile -> Optimize (Ph7) -> Portfolio (Ph8) -> Bottleneck (Ph9)."""
        profile = get_demo_farm_profile()
        candidates = {"chickpea": 0.71, "pigeonpeas": 0.68, "maize": 0.76}

        # 1. Phase 7 Optimization
        opt_res = optimize_farm_allocation(profile, candidates, top_n=3)
        assert opt_res.feasibility is True
        assert opt_res.details.get("ineqlin_marginals") is not None

        # 2. Phase 8 Portfolio Intelligence
        port_res = generate_portfolio_report(opt_res)
        assert port_res.total_crops > 0

        # 3. Phase 9 Bottleneck Analysis
        bottle_res = generate_bottleneck_report(
            optimization_result=opt_res,
            farm_profile=profile,
            candidate_crops=candidates,
            top_n=3,
            portfolio_result=port_res,
        )

        assert isinstance(bottle_res, BottleneckAnalysisResult)
        assert bottle_res.primary_bottleneck == "water_liters"
        assert bottle_res.primary_bottleneck_utilization >= 99.0
        assert bottle_res.shadow_value_status == "SOLVER_DUALS_ACTIVE"
        assert len(bottle_res.resource_lever_ranking) > 0
        assert bottle_res.resource_lever_ranking[0]["resource"] == "water_liters"
        assert len(bottle_res.explanation) > 50

    def test_secondary_bottlenecks_empty_when_no_other_active_constraints(self):
        """When only one resource has utilization data, secondary bottlenecks list is empty."""
        utils = {"water_liters": 95.0}
        sec = identify_secondary_bottlenecks(utils, primary_bottleneck="water_liters")
        assert sec == []

    def test_sensitivity_analysis_infeasible_graceful_handling(self):
        """Sensitivity analysis handles zero/unconstrained resources cleanly without throwing exceptions."""
        profile = get_demo_farm_profile()
        candidates = {"chickpea": 0.71}
        # Run sensitivity analysis
        sens = run_resource_sensitivity_analysis(profile, candidates, top_n=1)
        assert isinstance(sens, dict)
        for res_k, exp_dict in sens.items():
            assert "+10%" in exp_dict

    def test_explanation_contains_actionable_advice(self, mock_water_binding_result):
        """Report explanation must include actionable relaxation lever advice when levers exist."""
        profile = get_demo_farm_profile()
        cands = {"chickpea": 0.71, "pigeonpeas": 0.68}
        report = generate_bottleneck_report(mock_water_binding_result, profile, cands)
        assert "Actionable Advice" in report.explanation
        assert "Irrigation Water" in report.explanation

    def test_ui_safe_serializable_structure(self, mock_water_binding_result):
        """BottleneckAnalysisResult must be cleanly serializable to JSON/dict for UI and API consumption."""
        report = generate_bottleneck_report(mock_water_binding_result)
        d = report.model_dump()
        assert isinstance(d, dict)
        assert "primary_bottleneck" in d
        assert "constraint_states" in d
        assert "shadow_value_status" in d

