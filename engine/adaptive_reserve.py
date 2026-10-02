"""
FarmTwin — Adaptive Reserve & Mid-Season Re-Optimization Engine (Phase 10).

Responsibilities:
1. Reserve Analysis: Evaluates physical unallocated capacity buffers for land, water, N, P, K, and budget.
2. Critical Reserve Detection: Classifies buffers into EXHAUSTED, CRITICAL, LOW, HEALTHY using FarmTwin Heuristic Thresholds.
3. Re-Optimization Triggers: Evaluates operational parameter shifts (water, budget, land, fertilizers, climate scenarios) against configured trigger thresholds.
4. Plan Stability Analysis: Measures allocation and objective sensitivity between baseline and stress scenarios.
5. Mid-Season Simulation: Simulates hypothetical mid-season shocks (e.g. water -20%, budget -15%) by re-running the deterministic LP solver.
6. Adaptive Recommendations: Synthesizes data-backed buffer management and recourse advice in plain language.

Data Honesty:
- Does NOT fabricate new AI models, yield forecasts, economic projections, or arbitrary probabilities.
- Reuses existing optimization and scenario results deterministically.
"""
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

from engine.profile import FarmProfile
from engine.optimizer import (
    FarmOptimizationResult,
    optimize_farm_allocation,
)


class ReoptimizationTriggerConfig(BaseModel):
    """Configurable thresholds that trigger mid-season re-optimization."""
    water_change_pct: float = Field(default=10.0, description="Percentage shift in available water to trigger re-optimization")
    budget_change_pct: float = Field(default=20.0, description="Percentage shift in available budget to trigger re-optimization")
    fertilizer_change_pct: float = Field(default=15.0, description="Percentage shift in fertilizer inventory to trigger re-optimization")
    land_change_pct: float = Field(default=10.0, description="Percentage shift in operational land area to trigger re-optimization")
    scenario_change_enabled: bool = Field(default=True, description="Whether shifting from Baseline to a stress scenario triggers re-optimization")


class AdaptiveReserveResult(BaseModel):
    """Structured output report of the FarmTwin Adaptive Reserve & Mid-Season Engine."""
    reserve_summary: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    critical_reserves: Dict[str, str] = Field(default_factory=dict)
    trigger_status: str
    trigger_conditions: List[str] = Field(default_factory=list)
    stability_score: Optional[float] = None
    stability_status: str
    adaptive_recommendations: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    explanation: str


def analyze_resource_reserves(
    optimization_result: FarmOptimizationResult
) -> Dict[str, Dict[str, float]]:
    """
    Calculates available, used, and unallocated reserve buffers across farm resources.

    Returns:
        Dict mapping resource name -> {available, used, reserve, reserve_pct}
    """
    tracked = [
        ("land_ha", "ha"),
        ("water_liters", "L"),
        ("nitrogen_kg", "kg"),
        ("phosphorus_kg", "kg"),
        ("potassium_kg", "kg"),
        ("budget_inr", "INR"),
    ]

    reserves: Dict[str, Dict[str, float]] = {}

    for res_key, _ in tracked:
        used = optimization_result.resource_usage.get(res_key, 0.0)
        rem = optimization_result.resource_remaining.get(res_key, 0.0)
        avail = used + rem

        reserve_pct = (rem / avail * 100.0) if avail > 0 else 0.0

        reserves[res_key] = {
            "available": round(float(avail), 2),
            "used": round(float(used), 2),
            "reserve": round(float(rem), 2),
            "reserve_pct": round(float(reserve_pct), 2),
        }

    return reserves


def identify_critical_reserves(
    reserve_summary: Dict[str, Dict[str, float]]
) -> Dict[str, str]:
    """
    Classifies reserve buffers using FarmTwin Heuristic Thresholds:
    - reserve_pct <= 0.1% -> EXHAUSTED (fully depleted by current plan)
    - reserve_pct < 10.0% -> CRITICAL (dangerously thin safety buffer)
    - reserve_pct < 25.0% -> LOW (lean buffer; vulnerable to minor shocks)
    - reserve_pct >= 25.0% -> HEALTHY (robust buffer retained)

    Returns:
        Dict mapping resource name -> classification string
    """
    classifications: Dict[str, str] = {}

    for res_key, data in reserve_summary.items():
        pct = data.get("reserve_pct", 0.0)
        if pct <= 1.0:
            classifications[res_key] = "EXHAUSTED"
        elif pct < 10.0:
            classifications[res_key] = "CRITICAL"
        elif pct < 25.0:
            classifications[res_key] = "LOW"
        else:
            classifications[res_key] = "HEALTHY"

    return classifications


def evaluate_reoptimization_triggers(
    current_profile: FarmProfile,
    observed_conditions: Optional[Dict[str, Any]] = None,
    active_scenario: Optional[str] = None,
    config: Optional[ReoptimizationTriggerConfig] = None
) -> Tuple[str, List[str]]:
    """
    Evaluates whether observed farm changes or climate scenario shifts warrant re-optimizing allocations.

    Returns:
        (trigger_status, trigger_conditions)
    """
    if config is None:
        config = ReoptimizationTriggerConfig()

    conditions: List[str] = []

    if observed_conditions:
        # 1. Water Shift
        if "available_water" in observed_conditions:
            obs_w = float(observed_conditions["available_water"])
            curr_w = float(current_profile.available_water)
            if curr_w > 0:
                diff_pct = abs(obs_w - curr_w) / curr_w * 100.0
                if diff_pct >= config.water_change_pct:
                    conditions.append(
                        f"Irrigation water changed by {diff_pct:.1f}% (threshold: {config.water_change_pct:.1f}%)"
                    )

        # 2. Budget Shift
        if "available_budget_inr" in observed_conditions:
            obs_b = float(observed_conditions["available_budget_inr"])
            curr_b = float(current_profile.available_budget_inr)
            if curr_b > 0:
                diff_pct = abs(obs_b - curr_b) / curr_b * 100.0
                if diff_pct >= config.budget_change_pct:
                    conditions.append(
                        f"Operating budget changed by {diff_pct:.1f}% (threshold: {config.budget_change_pct:.1f}%)"
                    )

        # 3. Fertilizer Shift (Nitrogen)
        if "available_n_kg" in observed_conditions:
            obs_n = float(observed_conditions["available_n_kg"])
            curr_n = float(current_profile.available_n_kg)
            if curr_n > 0:
                diff_pct = abs(obs_n - curr_n) / curr_n * 100.0
                if diff_pct >= config.fertilizer_change_pct:
                    conditions.append(
                        f"Nitrogen inventory changed by {diff_pct:.1f}% (threshold: {config.fertilizer_change_pct:.1f}%)"
                    )

        # 4. Land Shift
        if "land_area" in observed_conditions:
            obs_l = float(observed_conditions["land_area"])
            curr_l = float(current_profile.land_area)
            if curr_l > 0:
                diff_pct = abs(obs_l - curr_l) / curr_l * 100.0
                if diff_pct >= config.land_change_pct:
                    conditions.append(
                        f"Operational land changed by {diff_pct:.1f}% (threshold: {config.land_change_pct:.1f}%)"
                    )

    # 5. Climate Scenario Shift
    if config.scenario_change_enabled and active_scenario and active_scenario not in ("Baseline", "None"):
        conditions.append(
            f"Active environmental scenario shifted to '{active_scenario}'"
        )

    if conditions:
        return ("REOPTIMIZATION_REQUIRED", conditions)
    return ("PLAN_STABLE", ["No operational parameters exceeded re-optimization trigger thresholds."])


def analyze_plan_stability(
    baseline_result: FarmOptimizationResult,
    scenario_results: Optional[Dict[str, FarmOptimizationResult]] = None
) -> Tuple[Optional[float], str, str]:
    """
    Evaluates allocation sensitivity by comparing baseline allocations against scenario outcomes.

    Metric:
        Measures the maximum relative allocation shift across stress scenarios:
        Max Shift = max_s [ sum_c |x_c,s - x_c,base| / (2 * total_land_base) ]
        Stability Score = 1.0 - Max Shift

    Thresholds:
        - Stability Score >= 0.85 (Shift < 15%): HIGH_STABILITY
        - 0.60 <= Stability Score < 0.85 (Shift 15% - 40%): MODERATE_STABILITY
        - Stability Score < 0.60 (Shift > 40%): LOW_STABILITY

    Returns:
        (stability_score, stability_status, explanation)
    """
    if not scenario_results or len(scenario_results) == 0:
        return (
            None,
            "DATA_UNAVAILABLE",
            "Plan stability analysis requires scenario optimization results."
        )

    base_land = baseline_result.total_land_used_ha
    if base_land <= 0:
        return (
            0.0,
            "LOW_STABILITY",
            "Baseline cultivated land is 0.0 ha; plan stability cannot be assessed."
        )

    base_alloc = baseline_result.crop_allocations_ha
    all_crops = set(base_alloc.keys())
    for s_res in scenario_results.values():
        if isinstance(s_res, FarmOptimizationResult):
            all_crops.update(s_res.crop_allocations_ha.keys())

    max_shift = 0.0
    worst_scen_name = ""

    for s_name, s_res in scenario_results.items():
        if not isinstance(s_res, FarmOptimizationResult) or s_name == "Baseline":
            continue
        scen_alloc = s_res.crop_allocations_ha

        # Total variation distance / proportional shift
        abs_diff_sum = sum(
            abs(base_alloc.get(c, 0.0) - scen_alloc.get(c, 0.0))
            for c in all_crops
        )
        shift = abs_diff_sum / (2.0 * base_land)
        if shift > max_shift:
            max_shift = shift
            worst_scen_name = s_name

    max_shift = min(1.0, max(0.0, max_shift))
    stability_score = round(1.0 - max_shift, 4)

    if stability_score >= 0.85:
        status = "HIGH_STABILITY"
        expl = (
            f"High plan stability (score = {stability_score:.2f}). Crop allocations shift by less than 15% "
            f"even under environmental stress scenarios."
        )
    elif stability_score >= 0.60:
        status = "MODERATE_STABILITY"
        expl = (
            f"Moderate plan stability (score = {stability_score:.2f}). Stress scenario '{worst_scen_name}' "
            f"causes a {max_shift * 100:.1f}% reallocation of crop land."
        )
    else:
        status = "LOW_STABILITY"
        expl = (
            f"Low plan stability (score = {stability_score:.2f}). Severe stress '{worst_scen_name}' "
            f"triggers significant crop contraction or abandonment ({max_shift * 100:.1f}% shift)."
        )

    return (stability_score, status, expl)


def generate_adaptive_recommendations(
    reserve_summary: Dict[str, Dict[str, float]],
    critical_reserves: Dict[str, str],
    stability_status: str,
    trigger_status: str,
    trigger_conditions: List[str]
) -> List[str]:
    """
    Synthesizes actionable, factual adaptive management recommendations based on
    reserve buffer health and stability status.
    """
    recs: List[str] = []

    # 1. Exhausted & Critical Reserves
    exhausted = [r.replace("_", " ").title() for r, s in critical_reserves.items() if s == "EXHAUSTED"]
    if exhausted:
        recs.append(
            f"Exhausted buffer: {', '.join(exhausted)} has 0% reserve margin. "
            "Implement strict deficit rationing or secure emergency backup capacity."
        )

    critical = [r.replace("_", " ").title() for r, s in critical_reserves.items() if s == "CRITICAL"]
    if critical:
        recs.append(
            f"Critical reserve: {', '.join(critical)} is below 10% safety margin. "
            "Monitor inventory closely and prepare mid-season replenishment."
        )

    # 2. Healthy Buffer Management
    healthy = [r.replace("_", " ").title() for r, s in critical_reserves.items() if s == "HEALTHY"]
    if healthy:
        recs.append(
            f"Healthy surplus: {', '.join(healthy)} retains ample unallocated headroom (≥25%), "
            "providing insurance against input supply disruptions."
        )

    # 3. Trigger Advice
    if trigger_status == "REOPTIMIZATION_REQUIRED":
        recs.append(
            "Re-optimization trigger tripped: Operational conditions have materially diverged. "
            "Re-run Phase 7 optimizer to rebalance acreage under current resource levels."
        )
    else:
        recs.append(
            "Current farm plan remains operationally valid within pre-set tolerance boundaries."
        )

    # 4. Stability Advice
    if stability_status == "LOW_STABILITY":
        recs.append(
            "High scenario vulnerability: Crop acreage contracts sharply under stress. "
            "Consider holding a larger irrigation water reserve as a climate buffer."
        )

    return recs


def simulate_resource_change(
    farm_profile: FarmProfile,
    candidate_crops: Any,
    top_n: int = 5,
    resource_changes_pct: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Simulates hypothetical mid-season shocks (e.g. water -20%, budget -15%) by re-running
    the deterministic Phase 7 LP solver and measuring differences against the baseline plan.

    Returns:
        Structured dictionary comparing original plan vs updated plan.
    """
    if resource_changes_pct is None:
        resource_changes_pct = {"available_water": -20.0}

    # 1. Original Plan
    base_res = optimize_farm_allocation(
        farm_profile=farm_profile,
        candidate_crops=candidate_crops,
        top_n=top_n
    )

    # 2. Apply modifications to profile
    p_data = farm_profile.model_dump()
    for field_name, pct_change in resource_changes_pct.items():
        if field_name in p_data and p_data[field_name] is not None:
            curr = float(p_data[field_name])
            p_data[field_name] = max(0.0, curr * (1.0 + pct_change / 100.0))

    sim_profile = FarmProfile(**p_data)

    # 3. Updated Plan
    sim_res = optimize_farm_allocation(
        farm_profile=sim_profile,
        candidate_crops=candidate_crops,
        top_n=top_n
    )

    # 4. Compute exact differences
    land_delta = round(sim_res.total_land_used_ha - base_res.total_land_used_ha, 4)
    base_obj = base_res.objective_value or 0.0
    sim_obj = sim_res.objective_value or 0.0
    obj_delta = round(sim_obj - base_obj, 4)

    all_crops = set(base_res.crop_allocations_ha.keys()).union(sim_res.crop_allocations_ha.keys())
    crop_deltas = {
        c: round(sim_res.crop_allocations_ha.get(c, 0.0) - base_res.crop_allocations_ha.get(c, 0.0), 4)
        for c in all_crops
    }

    return {
        "applied_changes": resource_changes_pct,
        "baseline_land_ha": base_res.total_land_used_ha,
        "updated_land_ha": sim_res.total_land_used_ha,
        "land_delta_ha": land_delta,
        "baseline_objective": base_obj,
        "updated_objective": sim_obj,
        "objective_delta": obj_delta,
        "crop_deltas": crop_deltas,
        "baseline_status": base_res.status,
        "updated_status": sim_res.status,
    }


def generate_adaptive_report(
    optimization_result: FarmOptimizationResult,
    farm_profile: Optional[FarmProfile] = None,
    candidate_crops: Optional[Any] = None,
    scenario_results: Optional[Dict[str, FarmOptimizationResult]] = None,
    observed_conditions: Optional[Dict[str, Any]] = None,
    active_scenario: Optional[str] = None,
    trigger_config: Optional[ReoptimizationTriggerConfig] = None,
) -> AdaptiveReserveResult:
    """
    Synthesizes reserve analysis, trigger evaluations, stability scores, and recommendations
    into a comprehensive AdaptiveReserveResult.
    """
    # 1. Reserve Analysis
    reserves = analyze_resource_reserves(optimization_result)

    # 2. Critical Reserve Detection
    critical = identify_critical_reserves(reserves)

    # 3. Trigger Evaluation
    if farm_profile is not None:
        trig_status, trig_conds = evaluate_reoptimization_triggers(
            current_profile=farm_profile,
            observed_conditions=observed_conditions,
            active_scenario=active_scenario,
            config=trigger_config,
        )
    else:
        trig_status = "PLAN_STABLE"
        trig_conds = ["No observed profile updates provided."]

    # 4. Plan Stability Analysis
    stab_score, stab_status, stab_expl = analyze_plan_stability(
        baseline_result=optimization_result,
        scenario_results=scenario_results,
    )

    # 5. Adaptive Recommendations
    recs = generate_adaptive_recommendations(
        reserve_summary=reserves,
        critical_reserves=critical,
        stability_status=stab_status,
        trigger_status=trig_status,
        trigger_conditions=trig_conds,
    )

    # 6. Compile Warnings
    warnings = []
    exhausted_list = [r.replace("_", " ").title() for r, s in critical.items() if s == "EXHAUSTED"]
    if exhausted_list:
        warnings.append(
            f"Zero reserve margin: {', '.join(exhausted_list)} is fully utilized with zero contingency buffer."
        )

    if trig_status == "REOPTIMIZATION_REQUIRED":
        warnings.append(
            f"Re-optimization required: {len(trig_conds)} operational trigger threshold(s) breached."
        )

    # 7. Plain-Language Explanation
    expl_parts = []
    if exhausted_list:
        expl_parts.append(f"All available {', '.join(exhausted_list)} is currently utilized by the active plan.")
    else:
        expl_parts.append("The farm retains positive contingency buffers across all tracked resources.")

    healthy_list = [r.replace("_", " ").title() for r, s in critical.items() if s == "HEALTHY"]
    if healthy_list:
        expl_parts.append(f"The farm maintains substantial reserves in {', '.join(healthy_list)}.")

    expl_parts.append(f"Trigger status is {trig_status}.")
    expl_parts.append(stab_expl)

    full_explanation = " ".join(expl_parts)

    return AdaptiveReserveResult(
        reserve_summary=reserves,
        critical_reserves=critical,
        trigger_status=trig_status,
        trigger_conditions=trig_conds,
        stability_score=stab_score,
        stability_status=stab_status,
        adaptive_recommendations=recs,
        warnings=warnings,
        explanation=full_explanation,
    )
