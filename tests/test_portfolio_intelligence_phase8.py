"""
FarmTwin Phase 8 Automated Tests — Crop Portfolio & Soil Rotation Intelligence Engine.

Covers:
1. Single crop portfolio diversity (monoculture)
2. Multi crop portfolio diversity (balanced portfolio)
3. Deterministic Shannon diversity score calculation
4. Diversity classification thresholds (LOW, MODERATE, HIGH)
5. Soil nutrient pressure analysis (LOW, MODERATE, HIGH)
6. Scenario resilience analysis calculation
7. Resilience classification thresholds (LOW, MODERATE, HIGH, DATA_UNAVAILABLE)
8. Portfolio report generation
9. Farmer explanation generation
10. Empty portfolio handling (0.0 ha cultivated)
11. Crop rotation DATA_UNAVAILABLE data honesty audit
12. Integration with Phase 7 FarmOptimizationResult
13. Integration with Phase 5/7 scenario optimization results
14. Warning compilation (monoculture, high water, nutrient pressure, low resilience)
15. UI-safe serializable outputs
16. Strict data honesty: no fake yield usage
17. Strict data honesty: no fake profit usage
18. Pure deterministic behavior
19. Edge cases (zero nutrients, zero scenario land, all zero crops)
20. Full pipeline compatibility (FarmProfile -> Optimizer -> Portfolio Intelligence)
"""
import pytest
from engine.profile import get_demo_farm_profile, FarmProfile
from engine.optimizer import (
    optimize_farm_allocation,
    optimize_across_scenarios,
    FarmOptimizationResult,
    OptimizationMode,
    OptimizationObjective,
)
from engine.portfolio_intelligence import (
    CropPortfolioEntry,
    PortfolioAnalysisResult,
    analyze_portfolio_diversity,
    analyze_nutrient_pressure,
    analyze_rotation_compatibility,
    analyze_resilience,
    generate_portfolio_report,
)


@pytest.fixture
def mock_opt_result():
    """Module-level fixture providing a valid Phase 7 FarmOptimizationResult."""
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
            "phosphorus_kg": 26.0,
            "potassium_kg": 82.0,
            "budget_inr": 82300.0,
            "labour_days": 0.0,
        },
        resource_utilization_pct={
            "land_ha": 45.0,
            "water_liters": 100.0,
            "nitrogen_kg": 11.25,
            "phosphorus_kg": 67.5,
            "potassium_kg": 18.0,
            "budget_inr": 17.7,
            "labour_days": None,
        },
        feasibility=True,
        constraint_violations=[],
        objective_value=0.627,
        expected_profit_inr=None,
        risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
        explanation="Allocated 0.5 ha chickpea and 0.4 ha pigeonpeas.",
        binding_resources=["water_liters"],
    )


class TestPortfolioDiversity:
    """Tests 1-4: Diversity calculation and classification."""

    def test_single_crop_portfolio_diversity(self):
        """Monoculture (1 crop, 100% share) must produce Shannon index 0.0 and LOW_DIVERSITY."""
        alloc = {"rice": 2.0}
        score, status, expl = analyze_portfolio_diversity(alloc)
        assert score == 0.0
        assert status == "LOW_DIVERSITY"
        assert "Low portfolio diversity" in expl

    def test_multi_crop_portfolio_diversity(self):
        """Three evenly balanced crops must produce Shannon index ~ ln(3) = 1.0986 and HIGH_DIVERSITY."""
        alloc = {"rice": 0.5, "maize": 0.5, "chickpea": 0.5}
        score, status, expl = analyze_portfolio_diversity(alloc)
        assert score >= 1.00
        assert status == "HIGH_DIVERSITY"
        assert "High portfolio diversity" in expl

    def test_moderate_diversity_two_crops(self):
        """Two evenly split crops produce ln(2) = 0.6931 -> MODERATE_DIVERSITY."""
        alloc = {"chickpea": 0.5, "pigeonpeas": 0.5}
        score, status, expl = analyze_portfolio_diversity(alloc)
        assert 0.50 <= score < 1.00
        assert status == "MODERATE_DIVERSITY"

    def test_diversity_ignores_zero_allocation_crops(self):
        """Crops with 0.0 ha should not artificially inflate diversity count."""
        alloc = {"rice": 2.0, "maize": 0.0, "cotton": 0.0}
        score, status, _ = analyze_portfolio_diversity(alloc)
        assert score == 0.0
        assert status == "LOW_DIVERSITY"

    def test_empty_portfolio_diversity(self):
        """Zero allocations return 0.0 score and LOW_DIVERSITY gracefully."""
        alloc = {}
        score, status, expl = analyze_portfolio_diversity(alloc)
        assert score == 0.0
        assert status == "LOW_DIVERSITY"
        assert "No crops" in expl


class TestNutrientPressure:
    """Tests 5: Nutrient sustainability analysis and heuristic thresholds."""

    def test_high_nutrient_pressure_threshold(self):
        """Utilization >= 90% on any nutrient triggers HIGH_PRESSURE."""
        util = {"nitrogen_kg": 95.0, "phosphorus_kg": 40.0, "potassium_kg": 20.0}
        status, expl, _ = analyze_nutrient_pressure(util)
        assert status == "HIGH_PRESSURE"
        assert "High soil nutrient pressure detected" in expl
        assert "NITROGEN" in expl

    def test_moderate_nutrient_pressure_threshold(self):
        """Peak utilization between 60% and 90% triggers MODERATE_PRESSURE."""
        util = {"nitrogen_kg": 50.0, "phosphorus_kg": 75.0, "potassium_kg": 20.0}
        status, expl, _ = analyze_nutrient_pressure(util)
        assert status == "MODERATE_PRESSURE"
        assert "Moderate soil nutrient pressure" in expl

    def test_low_nutrient_pressure_threshold(self):
        """All nutrients < 60% triggers LOW_PRESSURE."""
        util = {"nitrogen_kg": 25.0, "phosphorus_kg": 30.0, "potassium_kg": 15.0}
        status, expl, _ = analyze_nutrient_pressure(util)
        assert status == "LOW_PRESSURE"
        assert "Low soil nutrient pressure" in expl

    def test_nutrient_pressure_missing_data(self):
        """Empty utilization dict returns DATA_UNAVAILABLE."""
        util = {}
        status, expl, _ = analyze_nutrient_pressure(util)
        assert status == "DATA_UNAVAILABLE"
        assert "unavailable" in expl.lower()


class TestRotationIntelligence:
    """Tests 8 & 11: Crop rotation data honesty and repository audit."""

    def test_rotation_status_reports_data_unavailable_honestly(self):
        """Repository currently has null rotation family and empty rules; must return DATA_UNAVAILABLE."""
        status, expl = analyze_rotation_compatibility(["rice", "maize"])
        assert status == "DATA_UNAVAILABLE"
        assert "unpopulated in repository configs" in expl
        assert "crops_profile.json" in expl


class TestScenarioResilience:
    """Tests 6-7: Resilience ratio calculation and stress survival."""

    def test_resilience_high_classification(self):
        """Retaining >= 80% cultivated area under worst scenario yields HIGH_RESILIENCE."""
        baseline_land = 1.0
        scenarios = {
            "Drought": {"total_land_used_ha": 0.85},
            "Excess Rainfall": {"total_land_used_ha": 0.95},
        }
        score, status, expl = analyze_resilience(baseline_land, scenarios)
        assert score == 0.85
        assert status == "HIGH_RESILIENCE"
        assert "High scenario resilience" in expl

    def test_resilience_moderate_classification(self):
        """Retaining 50-80% cultivated area yields MODERATE_RESILIENCE."""
        baseline_land = 1.0
        scenarios = {
            "Drought": {"total_land_used_ha": 0.65},
            "Water Shortage": {"total_land_used_ha": 0.70},
        }
        score, status, expl = analyze_resilience(baseline_land, scenarios)
        assert score == 0.65
        assert status == "MODERATE_RESILIENCE"
        assert "Moderate scenario resilience" in expl

    def test_resilience_low_classification(self):
        """Retaining < 50% cultivated area yields LOW_RESILIENCE."""
        baseline_land = 1.0
        scenarios = {
            "Severe Drought": {"total_land_used_ha": 0.35},
        }
        score, status, expl = analyze_resilience(baseline_land, scenarios)
        assert score == 0.35
        assert status == "LOW_RESILIENCE"
        assert "Low scenario resilience" in expl

    def test_resilience_data_unavailable_when_no_scenarios(self):
        """If scenario results are None or empty, returns DATA_UNAVAILABLE."""
        score, status, expl = analyze_resilience(1.0, None)
        assert score is None
        assert status == "DATA_UNAVAILABLE"

    def test_resilience_handles_zero_baseline_land(self):
        """Zero baseline cultivated area returns 0.0 and LOW_RESILIENCE."""
        score, status, _ = analyze_resilience(0.0, {"Drought": {"total_land_used_ha": 0.0}})
        assert score == 0.0
        assert status == "LOW_RESILIENCE"


class TestReportGenerationAndIntegration:
    """Tests 8-10, 12-15: Report compilation, warnings, and Phase 7 integration."""

    def test_generate_portfolio_report_structure(self, mock_opt_result):
        """Report must contain all required fields and valid types."""
        scenarios = {
            "Drought": FarmOptimizationResult(
                status="OPTIMAL",
                optimization_mode=OptimizationMode.RESOURCE_ONLY,
                objective=OptimizationObjective.RESOURCE_SUITABILITY,
                candidate_crops=["chickpea", "pigeonpeas"],
                crop_allocations_ha={"chickpea": 0.4, "pigeonpeas": 0.32},
                total_land_used_ha=0.72,
                land_remaining_ha=1.28,
                resource_usage={"water_liters": 80000.0, "land_ha": 0.72, "nitrogen_kg": 14.4, "phosphorus_kg": 43.2, "potassium_kg": 14.4, "budget_inr": 14160.0, "labour_days": 0.0},
                resource_remaining={"water_liters": 0.0, "land_ha": 1.28, "nitrogen_kg": 145.6, "phosphorus_kg": 36.8, "potassium_kg": 85.6, "budget_inr": 85840.0, "labour_days": 0.0},
                resource_utilization_pct={"water_liters": 100.0, "land_ha": 36.0, "nitrogen_kg": 9.0, "phosphorus_kg": 54.0, "potassium_kg": 14.4, "budget_inr": 14.16, "labour_days": None},
                feasibility=True,
                constraint_violations=[],
                objective_value=0.5,
                expected_profit_inr=None,
                risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
                explanation="Drought allocation",
                binding_resources=["water_liters"],
            )
        }
        report = generate_portfolio_report(mock_opt_result, scenarios)
        assert isinstance(report, PortfolioAnalysisResult)
        assert report.total_crops == 2
        assert report.total_land_used_ha == 0.9
        assert report.diversity_status == "MODERATE_DIVERSITY"
        assert report.resilience_status == "HIGH_RESILIENCE"
        assert report.resilience_score == pytest.approx(0.8, abs=0.01)
        assert report.nutrient_pressure_status == "MODERATE_PRESSURE"
        assert report.rotation_status == "DATA_UNAVAILABLE"

    def test_warnings_compilation(self, mock_opt_result):
        """Report compiles warnings for high water dependence and unpopulated rotation metadata."""
        report = generate_portfolio_report(mock_opt_result)
        warning_text = " ".join(report.warnings)
        assert "High water dependence" in warning_text
        assert "Crop rotation data unavailable" in warning_text

    def test_farmer_explanation_synthesis(self, mock_opt_result):
        """Farmer explanation must be coherent and informative without technical jargon."""
        report = generate_portfolio_report(mock_opt_result)
        assert len(report.explanation) > 50
        assert "Your farm portfolio contains 2 crop(s)" in report.explanation


class TestDataHonestyAndPipelineEndToEnd:
    """Tests 16-20: Data honesty verification and full end-to-end pipeline run."""

    def test_no_fake_yield_or_profit_in_portfolio_result(self, mock_opt_result):
        """Portfolio report must never expose or synthesize profit or yield values."""
        report = generate_portfolio_report(mock_opt_result)
        report_dict = report.model_dump()
        assert "profit" not in report_dict
        assert "yield" not in report_dict

    def test_deterministic_portfolio_report_reproducibility(self, mock_opt_result):
        """Repeated evaluations of the same allocation must yield identical scores and statuses."""
        rep1 = generate_portfolio_report(mock_opt_result)
        rep2 = generate_portfolio_report(mock_opt_result)
        assert rep1.diversity_score == rep2.diversity_score
        assert rep1.diversity_status == rep2.diversity_status
        assert rep1.resilience_score == rep2.resilience_score
        assert rep1.nutrient_pressure_status == rep2.nutrient_pressure_status

    def test_full_pipeline_phase1_through_phase8(self):
        """Executes full live pipeline: Profile -> Optimization (Phase 7) -> Portfolio Intelligence (Phase 8)."""
        profile = get_demo_farm_profile()
        candidates = {"chickpea": 0.71, "pigeonpeas": 0.68, "maize": 0.76}

        # 1. Run live Phase 7 Optimization
        opt_res = optimize_farm_allocation(farm_profile=profile, candidate_crops=candidates, top_n=3)
        assert opt_res.feasibility is True

        # 2. Run live Phase 7 Scenario Optimization
        scen_results = optimize_across_scenarios(farm_profile=profile, candidate_crops=candidates, top_n=3)
        assert len(scen_results) >= 2

        # 3. Run Phase 8 Portfolio Intelligence
        port_report = generate_portfolio_report(opt_res, scen_results)
        assert isinstance(port_report, PortfolioAnalysisResult)
        assert port_report.total_crops > 0
        assert port_report.diversity_score >= 0.0
        assert port_report.resilience_status in ("HIGH_RESILIENCE", "MODERATE_RESILIENCE", "LOW_RESILIENCE")
        assert port_report.nutrient_pressure_status in ("LOW_PRESSURE", "MODERATE_PRESSURE", "HIGH_PRESSURE")
        assert port_report.rotation_status == "DATA_UNAVAILABLE"
