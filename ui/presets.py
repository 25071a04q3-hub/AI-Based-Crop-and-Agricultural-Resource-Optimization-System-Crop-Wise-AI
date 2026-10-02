"""
FarmTwin — Prototype Presets and Pipeline Coordinator.

Provides deterministic farm presets and the unified end-to-end pipeline execution
helper for the Streamlit decision dashboard.
"""
from typing import Dict, Any, List, Optional
from engine.profile import FarmProfile, Season, LandUnit, WaterUnit
from engine.crop_suitability import (
    predict_crop_suitability,
    get_or_train_suitability_model,
    CropSuitabilityResult,
)
from engine.optimizer import (
    optimize_farm_allocation,
    optimize_across_scenarios,
    FarmOptimizationResult,
)
from engine.portfolio_intelligence import (
    generate_portfolio_report,
    PortfolioAnalysisResult,
)
from engine.bottleneck_analysis import (
    generate_bottleneck_report,
    BottleneckAnalysisResult,
)
from engine.adaptive_reserve import (
    generate_adaptive_report,
    simulate_resource_change,
    AdaptiveReserveResult,
)
from engine.yield_prediction import (
    predict_yield,
    YieldPredictionResult,
)


DEMO_PRESETS: Dict[str, Dict[str, Any]] = {
    "Balanced Farm (Telangana)": {
        "description": "1.0 ha diverse farm with balanced water and fertilizer. Demonstrates optimal multi-crop land allocation.",
        "payload": {
            "farm_id": "FARM-BALANCED",
            "farmer_name": "Ramesh Kumar",
            "state": "Telangana",
            "district": "Warangal",
            "latitude": 17.9689,
            "longitude": 79.5941,
            "land_area": 1.0,
            "land_unit": "hectare",
            "nitrogen_n_kg_ha": 80.0,
            "phosphorus_p_kg_ha": 40.0,
            "potassium_k_kg_ha": 50.0,
            "ph": 6.8,
            "temperature_c": 28.0,
            "humidity_percent": 65.0,
            "rainfall_mm": 200.0,
            "available_water": 12000000.0,
            "water_unit": "liter",
            "available_n_kg": 120.0,
            "available_p_kg": 60.0,
            "available_k_kg": 50.0,
            "available_budget_inr": 50000.0,
            "available_labour_days": 100.0,
            "season": "kharif",
            "year": 2026,
            "risk_tolerance": 0.50,
            "is_demo": True,
        }
    },
    "Water-Stressed Farm (Rajasthan)": {
        "description": "2.0 ha arid parcel with critically scarce irrigation water. Proves WATER as the binding 100% bottleneck and drought-hardy crop adaptation.",
        "payload": {
            "farm_id": "FARM-WATER-STRESSED",
            "farmer_name": "Bhanwar Lal",
            "state": "Rajasthan",
            "district": "Jodhpur",
            "latitude": 26.2389,
            "longitude": 73.0243,
            "land_area": 2.0,
            "land_unit": "hectare",
            "nitrogen_n_kg_ha": 40.0,
            "phosphorus_p_kg_ha": 25.0,
            "potassium_k_kg_ha": 30.0,
            "ph": 7.8,
            "temperature_c": 34.0,
            "humidity_percent": 35.0,
            "rainfall_mm": 45.0,
            "available_water": 2500000.0,
            "water_unit": "liter",
            "available_n_kg": 120.0,
            "available_p_kg": 60.0,
            "available_k_kg": 80.0,
            "available_budget_inr": 80000.0,
            "available_labour_days": 80.0,
            "season": "kharif",
            "year": 2026,
            "risk_tolerance": 0.20,
            "is_demo": True,
        }
    },
    "Fertilizer-Constrained Farm (Bihar)": {
        "description": "2.0 ha parcel with abundant water but severe chemical fertilizer deficiency. Proves PHOSPHORUS/NITROGEN as the binding constraint ceiling.",
        "payload": {
            "farm_id": "FARM-FERT-CONSTRAINED",
            "farmer_name": "Sanjay Mahto",
            "state": "Bihar",
            "district": "Muzaffarpur",
            "latitude": 26.1209,
            "longitude": 85.3647,
            "land_area": 2.0,
            "land_unit": "hectare",
            "nitrogen_n_kg_ha": 30.0,
            "phosphorus_p_kg_ha": 15.0,
            "potassium_k_kg_ha": 20.0,
            "ph": 6.5,
            "temperature_c": 27.0,
            "humidity_percent": 78.0,
            "rainfall_mm": 140.0,
            "available_water": 15000000.0,
            "water_unit": "liter",
            "available_n_kg": 35.0,
            "available_p_kg": 15.0,
            "available_k_kg": 20.0,
            "available_budget_inr": 80000.0,
            "available_labour_days": 90.0,
            "season": "kharif",
            "year": 2026,
            "risk_tolerance": 0.40,
            "is_demo": True,
        }
    },
    "Capital-Constrained Farm (Maharashtra)": {
        "description": "3.0 ha commercial parcel with ample land and water but severely restricted working capital. Proves BUDGET (INR) as the binding bottleneck.",
        "payload": {
            "farm_id": "FARM-CAPITAL-CONSTRAINED",
            "farmer_name": "Anil Patil",
            "state": "Maharashtra",
            "district": "Nagpur",
            "latitude": 21.1458,
            "longitude": 79.0882,
            "land_area": 3.0,
            "land_unit": "hectare",
            "nitrogen_n_kg_ha": 60.0,
            "phosphorus_p_kg_ha": 35.0,
            "potassium_k_kg_ha": 45.0,
            "ph": 6.9,
            "temperature_c": 32.0,
            "humidity_percent": 50.0,
            "rainfall_mm": 75.0,
            "available_water": 15000000.0,
            "water_unit": "liter",
            "available_n_kg": 150.0,
            "available_p_kg": 80.0,
            "available_k_kg": 100.0,
            "available_budget_inr": 25000.0,
            "available_labour_days": 60.0,
            "season": "kharif",
            "year": 2026,
            "risk_tolerance": 0.85,
            "is_demo": True,
        }
    }
}


def get_preset_profile(preset_name: str) -> FarmProfile:
    """Returns a validated FarmProfile instance for a given preset name."""
    if preset_name not in DEMO_PRESETS:
        preset_name = "Balanced Farm (Telangana)"
    payload = DEMO_PRESETS[preset_name]["payload"]
    return FarmProfile(**payload)


def execute_full_decision_pipeline(
    profile: FarmProfile,
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Executes the entire verified FarmTwin decision pipeline (Phases 3 through 10)
    deterministically in ~200-300ms and returns a structured dictionary of outputs.
    """
    # 1. AI Crop Suitability (Phase 3)
    suitability_model, suitability_metrics = get_or_train_suitability_model()
    suitability_results: List[CropSuitabilityResult] = predict_crop_suitability(
        profile=profile,
        model=suitability_model
    )
    top_candidates = suitability_results[:top_n]
    top_crop = top_candidates[0].crop_name if top_candidates else "rice"

    # 2. Honest Yield Prediction Gate (Phase 4)
    yield_result: YieldPredictionResult = predict_yield(
        profile=profile,
        crop_name=top_crop
    )

    # 3. Continuous LP Optimization (Phase 7)
    opt_result: FarmOptimizationResult = optimize_farm_allocation(
        farm_profile=profile,
        candidate_crops=top_candidates,
        top_n=top_n
    )

    # 4. Multi-Scenario Stress Testing (Phases 5 & 7)
    scenario_results: Dict[str, FarmOptimizationResult] = optimize_across_scenarios(
        farm_profile=profile,
        candidate_crops=top_candidates,
        top_n=top_n
    )

    # 5. Crop Portfolio & Diversity Analysis (Phase 8)
    portfolio_report: PortfolioAnalysisResult = generate_portfolio_report(
        optimization_result=opt_result,
        scenario_results=scenario_results,
    )

    # 6. Bottleneck Analysis & Dual Shadow Multipliers (Phase 9)
    bottleneck_report: BottleneckAnalysisResult = generate_bottleneck_report(
        optimization_result=opt_result,
        farm_profile=profile,
        candidate_crops=top_candidates,
        top_n=top_n,
        portfolio_result=portfolio_report,
    )

    # 7. Adaptive Reserve & Mid-Season Recourse (Phase 10)
    adaptive_report: AdaptiveReserveResult = generate_adaptive_report(
        optimization_result=opt_result,
        farm_profile=profile,
        candidate_crops=top_candidates,
        scenario_results=scenario_results,
    )

    return {
        "profile": profile,
        "suitability_results": suitability_results,
        "suitability_metrics": suitability_metrics,
        "top_candidates": top_candidates,
        "top_crop": top_crop,
        "yield_result": yield_result,
        "opt_result": opt_result,
        "scenario_results": scenario_results,
        "portfolio_report": portfolio_report,
        "bottleneck_report": bottleneck_report,
        "adaptive_report": adaptive_report,
    }
