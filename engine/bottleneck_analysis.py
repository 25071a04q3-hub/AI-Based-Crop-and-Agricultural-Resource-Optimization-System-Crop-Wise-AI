"""
FarmTwin — Bottleneck Analysis & Shadow Value Intelligence Engine (Phase 9).

Responsibilities:
1. Resource Constraint Audit: Classifies land, water, N, P, K, and budget into UNDERUTILIZED, ACTIVE, NEAR_BINDING, BINDING.
2. Primary & Secondary Bottleneck Detection: Identifies the most restrictive resource and ranks secondary constraints.
3. Shadow Value Intelligence: Extracts authentic HiGHS dual variables when available; strictly gates fake INR prices.
4. What-If Sensitivity Analysis: Measures empirical objective and acreage deltas from controlled +10% and +20% resource expansions.
5. Resource Lever Ranking: Ranks farm management levers by measured objective improvement.
6. Plain-Language Farmer Explanation: Synthesizes bottleneck insights, unconstrained slack, and expansion advice.

Data Honesty:
- Does NOT fabricate shadow prices or fake currency gains.
- Reports shadow values in suitability-weighted land units per resource unit (not INR).
- Sensitivity deltas stem exclusively from re-running the deterministic LP solver.
"""
from typing import Dict, List, Optional, Tuple, Any
from pydantic import BaseModel, Field

from engine.profile import FarmProfile
from engine.optimizer import (
    FarmOptimizationResult,
    optimize_farm_allocation,
)
from engine.portfolio_intelligence import PortfolioAnalysisResult


class BottleneckAnalysisResult(BaseModel):
    """Structured output report of the FarmTwin Bottleneck & Resource Intelligence Engine."""
    primary_bottleneck: Optional[str] = None
    primary_bottleneck_utilization: Optional[float] = None
    secondary_bottlenecks: List[str] = Field(default_factory=list)
    constraint_states: Dict[str, str] = Field(default_factory=dict)
    shadow_value_status: str
    shadow_values: Dict[str, Optional[float]] = Field(default_factory=dict)
    resource_lever_ranking: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    explanation: str


def analyze_resource_constraints(
    resource_utilization_pct: Dict[str, Optional[float]]
) -> Dict[str, str]:
    """
    Classifies farm resource constraints into utilization regimes using
    FarmTwin Heuristic Thresholds:
    - < 60.0%: UNDERUTILIZED (substantial surplus capacity exists)
    - 60.0% - 90.0%: ACTIVE (substantial consumption within safe limits)
    - 90.0% - 99.0%: NEAR_BINDING (approaching capacity limit; may restrict future expansion)
    - >= 99.0%: BINDING (fully saturated; directly limiting current land allocation)
    - None: UNCONSTRAINED (e.g. labour when unrecorded)

    Returns:
        Dict mapping resource name -> constraint state string
    """
    tracked_resources = [
        "land_ha",
        "water_liters",
        "nitrogen_kg",
        "phosphorus_kg",
        "potassium_kg",
        "budget_inr",
    ]

    states: Dict[str, str] = {}
    for res in tracked_resources:
        pct = resource_utilization_pct.get(res)
        if pct is None:
            states[res] = "UNCONSTRAINED"
        elif pct >= 99.0:
            states[res] = "BINDING"
        elif pct >= 90.0:
            states[res] = "NEAR_BINDING"
        elif pct >= 60.0:
            states[res] = "ACTIVE"
        else:
            states[res] = "UNDERUTILIZED"

    return states


def identify_primary_bottleneck(
    resource_utilization_pct: Dict[str, Optional[float]]
) -> Tuple[Optional[str], Optional[float], str]:
    """
    Identifies the single most restrictive constraint limiting farm acreage.

    Returns:
        (primary_bottleneck_name, utilization_pct, plain_language_reason)
    """
    tracked_resources = [
        "water_liters",
        "land_ha",
        "budget_inr",
        "nitrogen_kg",
        "phosphorus_kg",
        "potassium_kg",
    ]

    valid_utils = {
        r: resource_utilization_pct[r]
        for r in tracked_resources
        if resource_utilization_pct.get(r) is not None
    }

    if not valid_utils:
        return (None, None, "No resource utilization metrics are available.")

    # Sort descending by utilization
    sorted_res = sorted(valid_utils.items(), key=lambda x: x[1], reverse=True)
    top_res, top_util = sorted_res[0]

    friendly_names = {
        "water_liters": "Irrigation Water",
        "land_ha": "Operational Land",
        "budget_inr": "Operating Budget",
        "nitrogen_kg": "Nitrogen (N)",
        "phosphorus_kg": "Phosphorus (P)",
        "potassium_kg": "Potassium (K)",
    }

    name_label = friendly_names.get(top_res, top_res)

    if top_util >= 99.0:
        reason = (
            f"{name_label} is fully saturated ({top_util:.1f}% utilization). "
            f"It represents the strict binding ceiling preventing further land expansion."
        )
    elif top_util >= 90.0:
        reason = (
            f"{name_label} is near binding ({top_util:.1f}% utilization). "
            f"It is the primary operational friction point on the farm."
        )
    elif top_util >= 60.0:
        reason = (
            f"{name_label} has the highest consumption ({top_util:.1f}% utilization), "
            f"though all farm constraints currently retain operational headroom."
        )
    else:
        reason = (
            f"All tracked resources are currently underutilized (peak is {name_label} at {top_util:.1f}%). "
            f"The farm has ample resource slack."
        )

    return (top_res, round(top_util, 2), reason)


def identify_secondary_bottlenecks(
    resource_utilization_pct: Dict[str, Optional[float]],
    primary_bottleneck: Optional[str] = None
) -> List[str]:
    """
    Returns an ordered list of secondary bottlenecks based on descending utilization.
    Excludes the primary bottleneck.
    """
    tracked_resources = [
        "water_liters",
        "land_ha",
        "budget_inr",
        "nitrogen_kg",
        "phosphorus_kg",
        "potassium_kg",
    ]

    valid_utils = {
        r: resource_utilization_pct[r]
        for r in tracked_resources
        if resource_utilization_pct.get(r) is not None and r != primary_bottleneck
    }

    # Sort descending by utilization
    sorted_res = sorted(valid_utils.items(), key=lambda x: x[1], reverse=True)
    return [r for r, _ in sorted_res]


def analyze_shadow_values(
    optimization_result: FarmOptimizationResult
) -> Tuple[str, Dict[str, Optional[float]], str]:
    """
    Extracts authentic dual variables (marginals) from the SciPy HiGHS solver output
    stored in optimization_result.details.

    Data Honesty Rule:
    - If solver duals are unavailable or cannot be validated, returns SHADOW_VALUES_UNAVAILABLE.
    - Does NOT fabricate shadow prices.
    - Reports shadow values in units of suitability-weighted land (ha) per resource unit, NOT INR.

    Returns:
        (shadow_value_status, shadow_values_dict, explanation)
    """
    if not optimization_result.feasibility or optimization_result.status != "OPTIMAL":
        return (
            "SHADOW_VALUES_UNAVAILABLE",
            {},
            "Dual shadow values are unavailable because the optimization problem is infeasible or un-solved."
        )

    details = optimization_result.details or {}
    marginals = details.get("ineqlin_marginals")
    constraint_names = details.get("constraint_names")

    if not marginals or not constraint_names or len(marginals) != len(constraint_names):
        return (
            "SHADOW_VALUES_UNAVAILABLE",
            {},
            "Trustworthy solver dual multipliers are not exposed in this optimization result. "
            "In strict compliance with the Data Honesty Rule, shadow values are safely withheld."
        )

    shadow_dict: Dict[str, Optional[float]] = {}
    active_shadows = []

    # SciPy HiGHS minimizes -objective, so dual variables for A_ub * x <= b_ub satisfy:
    # d(objective) / d(b_j) = -marginal_j = |marginal_j|
    for name, m in zip(constraint_names, marginals):
        if m is not None:
            # Positive marginal rate of improvement in suitability-weighted land
            val = round(abs(float(m)), 6)
            shadow_dict[name] = val
            if val > 1e-6:
                active_shadows.append(f"{name}: +{val:.6f}")
        else:
            shadow_dict[name] = None

    if active_shadows:
        expl = (
            f"Dual shadow values extracted directly from HiGHS LP solver: {', '.join(active_shadows)}. "
            "Values represent the marginal gain in total suitability-weighted land per additional unit of resource. "
            "(Note: Measured in suitability land units, not currency, because economic yield forecasting is blocked)."
        )
    else:
        expl = (
            "All dual variables are zero; farm constraints have remaining slack and are not restricting the objective."
        )

    return ("SOLVER_DUALS_ACTIVE", shadow_dict, expl)


def run_resource_sensitivity_analysis(
    farm_profile: FarmProfile,
    candidate_crops: Any,
    top_n: int = 5,
    delta_pcts: List[float] = [10.0, 20.0]
) -> Dict[str, Dict[str, Any]]:
    """
    Runs controlled What-If re-optimization experiments to measure how relaxing
    specific resource constraints improves the optimization objective and land cultivation.

    Method:
    - Pure empirical solver re-runs; NO analytical approximations or fake economics.
    - Evaluates: water_liters, budget_inr, land_ha, nitrogen_kg, phosphorus_kg, potassium_kg.
    """
    # 1. Compute baseline
    base_res = optimize_farm_allocation(
        farm_profile=farm_profile,
        candidate_crops=candidate_crops,
        top_n=top_n
    )

    base_obj = base_res.objective_value or 0.0
    base_land = base_res.total_land_used_ha

    tracked_levers = [
        ("water_liters", "available_water"),
        ("budget_inr", "available_budget_inr"),
        ("land_ha", "land_area"),
        ("nitrogen_kg", "available_n_kg"),
        ("phosphorus_kg", "available_p_kg"),
        ("potassium_kg", "available_k_kg"),
    ]

    results: Dict[str, Dict[str, Any]] = {}

    for lever_key, profile_field in tracked_levers:
        lever_experiments = {}
        for delta in delta_pcts:
            # Create modified profile with relaxed constraint
            profile_data = farm_profile.model_dump()
            curr_val = profile_data.get(profile_field)

            if curr_val is not None and curr_val > 0:
                profile_data[profile_field] = curr_val * (1.0 + delta / 100.0)
                try:
                    mod_profile = FarmProfile(**profile_data)
                    new_res = optimize_farm_allocation(
                        farm_profile=mod_profile,
                        candidate_crops=candidate_crops,
                        top_n=top_n
                    )
                    new_obj = new_res.objective_value or 0.0
                    new_land = new_res.total_land_used_ha

                    obj_delta = round(new_obj - base_obj, 4)
                    obj_delta_pct = round((obj_delta / base_obj * 100.0), 2) if base_obj > 0 else 0.0
                    land_delta = round(new_land - base_land, 4)

                    lever_experiments[f"+{int(delta)}%"] = {
                        "new_objective": round(new_obj, 4),
                        "objective_delta": obj_delta,
                        "objective_delta_pct": obj_delta_pct,
                        "new_land_ha": round(new_land, 4),
                        "land_delta_ha": land_delta,
                        "status": new_res.status,
                    }
                except Exception as e:
                    lever_experiments[f"+{int(delta)}%"] = {"error": str(e)}
            else:
                lever_experiments[f"+{int(delta)}%"] = {
                    "new_objective": round(base_obj, 4),
                    "objective_delta": 0.0,
                    "objective_delta_pct": 0.0,
                    "new_land_ha": round(base_land, 4),
                    "land_delta_ha": 0.0,
                    "status": "UNCONSTRAINED_OR_ZERO",
                }

        results[lever_key] = lever_experiments

    return results


def rank_resource_levers(
    sensitivity_results: Dict[str, Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Ranks management resource levers in descending order of objective improvement
    measured from the +10% relaxation experiment.
    """
    ranking_entries = []

    friendly_names = {
        "water_liters": "Irrigation Water",
        "land_ha": "Operational Land Area",
        "budget_inr": "Operating Budget",
        "nitrogen_kg": "Nitrogen Fertilizer (N)",
        "phosphorus_kg": "Phosphorus Fertilizer (P)",
        "potassium_kg": "Potassium Fertilizer (K)",
    }

    for res_key, deltas in sensitivity_results.items():
        exp10 = deltas.get("+10%", {})
        delta_pct = exp10.get("objective_delta_pct", 0.0)
        land_delta = exp10.get("land_delta_ha", 0.0)

        if delta_pct >= 5.0:
            impact = "HIGH_IMPACT"
        elif delta_pct > 0.01:
            impact = "MODERATE_IMPACT"
        else:
            impact = "NO_IMPACT"

        ranking_entries.append({
            "resource": res_key,
            "resource_label": friendly_names.get(res_key, res_key),
            "objective_delta_pct_10": delta_pct,
            "land_delta_ha_10": land_delta,
            "impact_label": impact,
        })

    # Sort descending by objective improvement percentage, then land delta
    ranking_entries.sort(key=lambda x: (x["objective_delta_pct_10"], x["land_delta_ha_10"]), reverse=True)

    for idx, entry in enumerate(ranking_entries, start=1):
        entry["rank"] = idx

    return ranking_entries


def generate_bottleneck_report(
    optimization_result: FarmOptimizationResult,
    farm_profile: Optional[FarmProfile] = None,
    candidate_crops: Optional[Any] = None,
    top_n: int = 5,
    portfolio_result: Optional[PortfolioAnalysisResult] = None,
) -> BottleneckAnalysisResult:
    """
    Synthesizes constraint analysis, primary/secondary bottlenecks, HiGHS solver duals,
    What-If sensitivity experiments, and plain-language farmer advice into a BottleneckAnalysisResult.
    """
    utils = optimization_result.resource_utilization_pct

    # 1. Constraint States
    constraint_states = analyze_resource_constraints(utils)

    # 2. Primary Bottleneck
    prim_res, prim_util, prim_reason = identify_primary_bottleneck(utils)

    # 3. Secondary Bottlenecks
    sec_bottlenecks = identify_secondary_bottlenecks(utils, primary_bottleneck=prim_res)

    # 4. Shadow Value Intelligence
    shadow_status, shadow_vals, shadow_expl = analyze_shadow_values(optimization_result)

    # 5. Sensitivity & Lever Ranking (if farm_profile and candidate_crops provided)
    sensitivity_results = {}
    lever_ranking = []
    if farm_profile is not None and candidate_crops is not None and optimization_result.feasibility:
        sensitivity_results = run_resource_sensitivity_analysis(
            farm_profile=farm_profile,
            candidate_crops=candidate_crops,
            top_n=top_n
        )
        lever_ranking = rank_resource_levers(sensitivity_results)

    # 6. Compile Warnings
    warnings = []
    if prim_res and prim_util and prim_util >= 99.0:
        friendly = prim_res.replace("_", " ").title()
        warnings.append(
            f"Binding constraint: {friendly} is 100% exhausted. Land allocation cannot expand without additional {friendly}."
        )

    near_binding = [r for r, s in constraint_states.items() if s == "NEAR_BINDING"]
    if near_binding:
        near_str = ", ".join([r.replace("_", " ").title() for r in near_binding])
        warnings.append(f"Near-binding constraint(s): {near_str} are above 90% utilization.")

    # 7. Synthesize Farmer Explanation
    prim_name = prim_res.replace("_", " ").title() if prim_res else "None"
    expl_parts = [
        f"Primary Bottleneck: {prim_name}.",
        prim_reason,
    ]

    underutilized = [r.replace("_", " ").title() for r, s in constraint_states.items() if s == "UNDERUTILIZED"]
    if underutilized:
        expl_parts.append(
            f"The farm has ample remaining capacity in: {', '.join(underutilized)}."
        )

    if lever_ranking:
        top_lever = lever_ranking[0]
        if top_lever["objective_delta_pct_10"] > 0.01:
            expl_parts.append(
                f"Actionable Advice: Relaxing {top_lever['resource_label']} by +10% provides the greatest leverage, "
                f"increasing productive allocation by +{top_lever['objective_delta_pct_10']:.1f}% (+{top_lever['land_delta_ha_10']:.2f} ha)."
            )
        else:
            expl_parts.append(
                "No single resource relaxation significantly improves the objective under current candidate crop profiles."
            )

    expl_parts.append(shadow_expl)
    full_explanation = " ".join(expl_parts)

    return BottleneckAnalysisResult(
        primary_bottleneck=prim_res,
        primary_bottleneck_utilization=prim_util,
        secondary_bottlenecks=sec_bottlenecks,
        constraint_states=constraint_states,
        shadow_value_status=shadow_status,
        shadow_values=shadow_vals,
        resource_lever_ranking=lever_ranking,
        warnings=warnings,
        explanation=full_explanation,
    )
