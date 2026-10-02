"""
FarmTwin — Risk-Aware Farm Portfolio Optimization Engine.

Phase 7: Linear Programming (LP) and Mathematical Resource Allocation.
- Determines mathematically optimal crop acreage allocations (x_i >= 0, sum(x_i) <= total_land).
- Enforces strict multi-resource constraints (land, water, nitrogen, phosphorus, potassium, budget).
- Implements RESOURCE_ONLY optimization mode (maximizing suitability-weighted productive area)
  while historical yield/economic outcomes remain blocked.
- Provides future-compatible CVaR and economic optimization interfaces with strict data honesty gating.
- Seamlessly integrates with Phase 2 FarmProfile, Phase 3 Suitability, Phase 5 Scenarios,
  and Phase 6 Resource Calculation Engine.

CRITICAL DATA HONESTY RULES:
--------------------------------------------------------------------------------
1. Expected profit, revenue, and economic yields remain None / blocked because Phase 4
   historical yield training is blocked.
2. The current active objective is RESOURCE_SUITABILITY: maximize sum(suitability_i * x_i).
   This is a suitability-weighted resource efficiency allocation, NOT a profit maximization.
3. Scenario probabilities and CVaR risk calculations remain strictly gated as
   BLOCKED_INSUFFICIENT_RISK_DATA. No fake probabilities or risk scores are fabricated.
4. Uses scipy.optimize.linprog (HiGHS solver) for explainable, deterministic mathematical optimization.
--------------------------------------------------------------------------------
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from pydantic import BaseModel, Field
from scipy.optimize import linprog

from engine.profile import FarmProfile
from engine.crop_suitability import CropSuitabilityResult
from engine.scenario_simulator import ScenarioDefinition
from engine.resource_calculator import (
    get_crop_resource_profile,
    get_all_crop_resource_profiles,
    calculate_portfolio_resources,
    ResourceCalculationReport,
)


class OptimizationMode(str, Enum):
    """Execution mode for the optimization engine."""
    RESOURCE_ONLY = "RESOURCE_ONLY"
    ECONOMIC_OPTIMIZATION = "ECONOMIC_OPTIMIZATION"


class OptimizationObjective(str, Enum):
    """Objective function formulation."""
    RESOURCE_SUITABILITY = "RESOURCE_SUITABILITY"  # Active: maximize sum(suitability_i * x_i)
    EXPECTED_PROFIT = "EXPECTED_PROFIT"            # Blocked: requires historical yield dataset
    RISK_ADJUSTED_PROFIT = "RISK_ADJUSTED_PROFIT"  # Blocked: requires calibrated CVaR/scenarios


class RiskObjectiveConfig(BaseModel):
    """
    Configuration contract for future CVaR and downside risk formulations.
    Strictly gates execution when scenario probabilities are uncalibrated.
    """
    risk_measure: str = Field(default="CVaR", description="Risk measure (e.g. CVaR, Downside Variance)")
    confidence_level: float = Field(default=0.90, ge=0.50, le=0.99, description="Confidence level alpha (e.g. 0.90)")
    risk_aversion: float = Field(default=0.50, ge=0.0, le=1.0, description="Risk aversion parameter lambda [0, 1]")
    status: str = Field(
        default="BLOCKED_INSUFFICIENT_RISK_DATA",
        description="Execution status: blocked until calibrated scenario probabilities exist"
    )


class ScenarioOptimizationInput(BaseModel):
    """
    Input adapter allowing the optimizer to ingest Phase 5 scenario shock specifications.
    """
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None
    scenario_probability: Optional[float] = Field(
        default=None, description="Calibrated historical probability (None for manual stress tests)"
    )
    resource_adjustments: Dict[str, Any] = Field(default_factory=dict)
    yield_information: Optional[Any] = None
    economic_information: Optional[Any] = None


class FarmOptimizationResult(BaseModel):
    """
    Canonical outcome contract returned by the FarmTwin optimization engine.
    """
    status: str = Field(description="Solver outcome status: OPTIMAL, FEASIBLE, INFEASIBLE, UNBOUNDED, ERROR, BLOCKED")
    optimization_mode: OptimizationMode = Field(description="Active optimization mode")
    objective: OptimizationObjective = Field(description="Mathematical objective utilized")
    candidate_crops: List[str] = Field(description="List of candidate crops evaluated")
    crop_allocations_ha: Dict[str, float] = Field(
        description="Optimal land allocation per crop in hectares (x_i >= 0)"
    )
    total_land_used_ha: float = Field(ge=0, description="Total hectares allocated across candidate crops")
    land_remaining_ha: float = Field(description="Farm available land minus allocated land")
    resource_usage: Dict[str, float] = Field(description="Total consumption per operational resource")
    resource_remaining: Dict[str, float] = Field(description="Unused available balance per resource")
    resource_utilization_pct: Dict[str, Optional[float]] = Field(
        description="Percentage utilization per resource constraint"
    )
    binding_resources: List[str] = Field(
        default_factory=list, description="Resources operating at or near full capacity (>= 99% utilization)"
    )
    feasibility: bool = Field(description="True if solver found a valid feasible allocation satisfying all bounds")
    constraint_violations: List[str] = Field(default_factory=list, description="Violation messages if infeasible")
    objective_value: Optional[float] = Field(default=None, description="Optimal objective function scalar value")
    expected_profit_inr: Optional[float] = Field(
        default=None, description="Expected profit in INR (strictly None while yield model is blocked)"
    )
    risk_status: str = Field(
        default="BLOCKED_INSUFFICIENT_RISK_DATA",
        description="Status of risk/CVaR layer (blocked pending empirical probabilities)"
    )
    explanation: str = Field(description="Farmer-friendly natural language explanation of the plan")
    details: Dict[str, Any] = Field(default_factory=dict, description="Solver diagnostic metadata")


# ==============================================================================
# CANDIDATE NORMALIZATION UTILITIES
# ==============================================================================
def normalize_candidate_crops(
    candidate_crops: Union[List[str], List[CropSuitabilityResult], Dict[str, float]],
    top_n: Optional[int] = None
) -> List[Tuple[str, float]]:
    """
    Normalizes candidate inputs into a uniform list of (crop_name, suitability_score).
    Validates that crop exists in config/crops_profile.json.
    Sorts by suitability descending and slices to top_n.
    """
    if not candidate_crops:
        raise ValueError("Candidate crops list or mapping cannot be empty.")

    parsed: List[Tuple[str, float]] = []
    known_profiles = get_all_crop_resource_profiles()

    if isinstance(candidate_crops, dict):
        for name, score in candidate_crops.items():
            clean = name.strip().lower()
            if clean not in known_profiles:
                raise ValueError(f"Candidate crop '{name}' is not found in config/crops_profile.json.")
            if score < 0.0:
                raise ValueError(f"Suitability score for '{name}' must be non-negative. Received: {score}")
            parsed.append((clean, float(score)))

    elif isinstance(candidate_crops, list):
        for item in candidate_crops:
            if isinstance(item, CropSuitabilityResult):
                clean = item.crop_name.strip().lower()
                if clean not in known_profiles:
                    raise ValueError(f"Candidate crop '{item.crop_name}' is not found in config/crops_profile.json.")
                parsed.append((clean, float(item.suitability_score)))
            elif isinstance(item, str):
                clean = item.strip().lower()
                if clean not in known_profiles:
                    raise ValueError(f"Candidate crop '{item}' is not found in config/crops_profile.json.")
                # Default unit suitability if not specified
                parsed.append((clean, 1.0))
            elif isinstance(item, (tuple, list)) and len(item) == 2:
                clean = str(item[0]).strip().lower()
                score = float(item[1])
                if clean not in known_profiles:
                    raise ValueError(f"Candidate crop '{clean}' is not found in config/crops_profile.json.")
                if score < 0.0:
                    raise ValueError(f"Suitability score for '{clean}' must be non-negative. Received: {score}")
                parsed.append((clean, score))
            else:
                raise TypeError(f"Unsupported candidate crop element type: {type(item).__name__}")

    # Remove duplicates while preserving highest suitability
    unique_candidates: Dict[str, float] = {}
    for crop_name, score in parsed:
        if crop_name not in unique_candidates or score > unique_candidates[crop_name]:
            unique_candidates[crop_name] = score

    # Sort descending by suitability score
    sorted_candidates = sorted(unique_candidates.items(), key=lambda x: x[1], reverse=True)

    if top_n is not None and top_n > 0:
        sorted_candidates = sorted_candidates[:top_n]

    if not sorted_candidates:
        raise ValueError("No valid candidate crops remained after normalization.")

    return sorted_candidates


# ==============================================================================
# CORE LINEAR PROGRAMMING OPTIMIZER
# ==============================================================================
def optimize_farm_allocation(
    farm_profile: FarmProfile,
    candidate_crops: Union[List[str], List[CropSuitabilityResult], Dict[str, float]],
    top_n: int = 5,
    mode: OptimizationMode = OptimizationMode.RESOURCE_ONLY,
    objective: OptimizationObjective = OptimizationObjective.RESOURCE_SUITABILITY,
    risk_config: Optional[RiskObjectiveConfig] = None,
    scenario_input: Optional[ScenarioOptimizationInput] = None,
) -> FarmOptimizationResult:
    """
    Solves the continuous Linear Programming crop allocation problem using SciPy HiGHS.

    Formulation:
    Decision Variables:
        x_i = hectares allocated to candidate crop i  (x_i >= 0)

    Objective (RESOURCE_ONLY / RESOURCE_SUITABILITY):
        Maximize: sum(suitability_score_i * x_i)
        Equivalently: Minimize sum(-suitability_score_i * x_i)

    Constraints:
        1. Land:       sum(x_i) <= farm_profile.land_area_ha
        2. Water:      sum(water_per_ha_liters_i * x_i) <= farm_profile.water_liters
        3. Nitrogen:   sum(n_per_ha_kg_i * x_i) <= farm_profile.available_n_kg
        4. Phosphorus: sum(p_per_ha_kg_i * x_i) <= farm_profile.available_p_kg
        5. Potassium:  sum(k_per_ha_kg_i * x_i) <= farm_profile.available_k_kg
        6. Budget:     sum(cost_per_ha_inr_i * x_i) <= farm_profile.available_budget_inr

    Data Honesty Enforcements:
        - If mode == ECONOMIC_OPTIMIZATION or objective == EXPECTED_PROFIT:
          Safely blocks execution because Phase 4 historical yield model is blocked.
        - expected_profit_inr is strictly None in RESOURCE_ONLY mode.
        - CVaR is strictly marked as BLOCKED_INSUFFICIENT_RISK_DATA.
        - Original farm_profile is never mutated.
    """
    if not isinstance(farm_profile, FarmProfile):
        raise TypeError(f"Expected FarmProfile instance, got {type(farm_profile).__name__}")

    # 1. Economic Optimization Decision Gate
    if mode == OptimizationMode.ECONOMIC_OPTIMIZATION or objective in (
        OptimizationObjective.EXPECTED_PROFIT,
        OptimizationObjective.RISK_ADJUSTED_PROFIT
    ):
        return FarmOptimizationResult(
            status="BLOCKED",
            optimization_mode=mode,
            objective=objective,
            candidate_crops=[],
            crop_allocations_ha={},
            total_land_used_ha=0.0,
            land_remaining_ha=float(farm_profile.land_area_ha),
            resource_usage={},
            resource_remaining={},
            resource_utilization_pct={},
            binding_resources=[],
            feasibility=False,
            constraint_violations=["Economic optimization is blocked: historical crop yield dataset is unavailable."],
            objective_value=None,
            expected_profit_inr=None,
            risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
            explanation=(
                "Economic/profit optimization is currently blocked. Phase 4 established that the repository "
                "lacks an authentic historical crop yield dataset. Use RESOURCE_ONLY mode to optimize "
                "suitability-weighted resource allocation."
            ),
            details={"reason": "NO_HISTORICAL_YIELD_DATASET"},
        )

    # 2. Parse & Normalize Candidate Crops
    candidates = normalize_candidate_crops(candidate_crops, top_n=top_n)
    crop_names = [c[0] for c in candidates]
    suitabilities = [c[1] for c in candidates]
    n_vars = len(candidates)

    # 3. Read Farm Capacity Bounds (standardized units)
    total_land = float(farm_profile.land_area_ha)
    avail_water = float(farm_profile.water_liters)
    avail_n = float(farm_profile.available_n_kg)
    avail_p = float(farm_profile.available_p_kg)
    avail_k = float(farm_profile.available_k_kg)
    avail_budget = float(farm_profile.available_budget_inr)

    # 4. Zero-Capacity Edge Cases Check
    # If all resource capacities are 0 or land is 0, allocation is immediately 0 ha.
    if total_land <= 0 or (avail_water == 0 and avail_budget == 0 and avail_n == 0):
        zero_alloc = {c: 0.0 for c in crop_names}
        return FarmOptimizationResult(
            status="OPTIMAL",
            optimization_mode=mode,
            objective=objective,
            candidate_crops=crop_names,
            crop_allocations_ha=zero_alloc,
            total_land_used_ha=0.0,
            land_remaining_ha=total_land,
            resource_usage={"land_ha": 0.0, "water_liters": 0.0, "nitrogen_kg": 0.0, "phosphorus_kg": 0.0, "potassium_kg": 0.0, "budget_inr": 0.0},
            resource_remaining={"land_ha": total_land, "water_liters": avail_water, "nitrogen_kg": avail_n, "phosphorus_kg": avail_p, "potassium_kg": avail_k, "budget_inr": avail_budget},
            resource_utilization_pct={"land_ha": 0.0, "water_liters": 0.0, "nitrogen_kg": 0.0, "phosphorus_kg": 0.0, "potassium_kg": 0.0, "budget_inr": 0.0},
            binding_resources=["water_liters"] if avail_water == 0 else ["land_ha"],
            feasibility=True,
            constraint_violations=[],
            objective_value=0.0,
            expected_profit_inr=None,
            risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
            explanation="Farm operational capacity is zero. Optimal feasible allocation is 0.00 ha.",
            details={"solver_status": "ZERO_CAPACITY_TRIVIAL_SOLUTION"},
        )

    # 5. Extract Per-Hectare Consumption Coefficients from Phase 6 Engine
    all_profiles = get_all_crop_resource_profiles()
    row_land: List[float] = []
    row_water: List[float] = []
    row_n: List[float] = []
    row_p: List[float] = []
    row_k: List[float] = []
    row_budget: List[float] = []

    for c_name in crop_names:
        prof = all_profiles[c_name]
        row_land.append(1.0)
        row_water.append(float(prof.water_per_ha_liters))
        row_n.append(float(prof.nitrogen_per_ha_kg))
        row_p.append(float(prof.phosphorus_per_ha_kg))
        row_k.append(float(prof.potassium_per_ha_kg))
        # Default 0.0 cost if unrecorded
        row_budget.append(float(prof.cost_per_ha_inr) if prof.cost_per_ha_inr is not None else 0.0)

    # 6. Build SciPy linprog Problem Matrices
    # SciPy minimizes: c^T * x. For maximization, c = -suitability
    c_vector = [-1.0 * s for s in suitabilities]

    # Inequality constraints A_ub * x <= b_ub
    A_ub = [
        row_land,
        row_water,
        row_n,
        row_p,
        row_k,
        row_budget,
    ]
    b_ub = [
        total_land,
        avail_water,
        avail_n,
        avail_p,
        avail_k,
        avail_budget,
    ]

    # Decision variable non-negativity bounds: 0 <= x_i <= total_land
    bounds = [(0.0, total_land) for _ in range(n_vars)]

    # 7. Execute HiGHS Linear Programming Solver
    sol = linprog(
        c=c_vector,
        A_ub=A_ub,
        b_ub=b_ub,
        bounds=bounds,
        method="highs",
    )

    # 8. Handle Solver Outcome
    if not sol.success:
        status_str = "INFEASIBLE" if sol.status == 2 else ("UNBOUNDED" if sol.status == 3 else "ERROR")
        return FarmOptimizationResult(
            status=status_str,
            optimization_mode=mode,
            objective=objective,
            candidate_crops=crop_names,
            crop_allocations_ha={c: 0.0 for c in crop_names},
            total_land_used_ha=0.0,
            land_remaining_ha=total_land,
            resource_usage={},
            resource_remaining={},
            resource_utilization_pct={},
            binding_resources=[],
            feasibility=False,
            constraint_violations=[f"Solver unable to find feasible allocation: {sol.message}"],
            objective_value=None,
            expected_profit_inr=None,
            risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
            explanation=f"Optimization failed: {sol.message}.",
            details={"solver_status": sol.status, "message": sol.message},
        )

    # 9. Extract and Clean Allocations
    raw_alloc = sol.x
    alloc_dict: Dict[str, float] = {}
    total_land_used = 0.0

    for name, area in zip(crop_names, raw_alloc):
        # Floor to 4 decimal places to prevent round-up violations on tight resource boundaries
        clean_area = float(np.floor(max(0.0, float(area)) * 10000.0) / 10000.0)
        if clean_area < 1e-6:
            clean_area = 0.0
        alloc_dict[name] = clean_area
        total_land_used += clean_area

    total_land_used = round(total_land_used, 4)
    land_remaining = round(total_land - total_land_used, 4)

    # 10. Compute Resource Usages & Remaining Balances
    # Filter non-zero crops for reporting
    active_allocations = {k: v for k, v in alloc_dict.items() if v > 0.0}

    if active_allocations:
        report: ResourceCalculationReport = calculate_portfolio_resources(active_allocations, farm_profile)
        used_water = report.total_water_liters
        used_n = report.total_n_kg
        used_p = report.total_p_kg
        used_k = report.total_k_kg
        used_cost = report.total_cost_inr or 0.0
    else:
        used_water = 0.0
        used_n = 0.0
        used_p = 0.0
        used_k = 0.0
        used_cost = 0.0

    resource_usage = {
        "land_ha": total_land_used,
        "water_liters": round(used_water, 2),
        "nitrogen_kg": round(used_n, 2),
        "phosphorus_kg": round(used_p, 2),
        "potassium_kg": round(used_k, 2),
        "budget_inr": round(used_cost, 2),
    }

    resource_remaining = {
        "land_ha": land_remaining,
        "water_liters": round(avail_water - used_water, 2),
        "nitrogen_kg": round(avail_n - used_n, 2),
        "phosphorus_kg": round(avail_p - used_p, 2),
        "potassium_kg": round(avail_k - used_k, 2),
        "budget_inr": round(avail_budget - used_cost, 2),
    }

    def calc_util(used: float, avail: float) -> Optional[float]:
        if avail > 0:
            return round((used / avail) * 100.0, 2)
        return 0.0 if used == 0 else None

    resource_utilization_pct = {
        "land_ha": calc_util(total_land_used, total_land),
        "water_liters": calc_util(used_water, avail_water),
        "nitrogen_kg": calc_util(used_n, avail_n),
        "phosphorus_kg": calc_util(used_p, avail_p),
        "potassium_kg": calc_util(used_k, avail_k),
        "budget_inr": calc_util(used_cost, avail_budget),
    }

    # 11. Identify Binding / Saturated Resources (>= 99.0% utilization)
    binding_resources: List[str] = []
    for r_name, u_pct in resource_utilization_pct.items():
        if u_pct is not None and u_pct >= 99.0:
            binding_resources.append(r_name)

    # In linprog, objective value was minimized, so negate back
    opt_val = round(-1.0 * float(sol.fun), 4)

    # 12. Synthesize Farmer-Friendly Explanation
    nonzero_summary = [f"{v:.2f} ha to {k.capitalize()}" for k, v in alloc_dict.items() if v > 0]
    if nonzero_summary:
        alloc_phrase = f"FarmTwin allocated {', '.join(nonzero_summary)}."
    else:
        alloc_phrase = "No land could be allocated due to binding resource limits."

    binding_phrase = (
        f"Binding constraint(s): {', '.join(binding_resources)} reached full capacity."
        if binding_resources
        else "All resource limits satisfied with remaining surplus."
    )

    explanation = (
        f"{alloc_phrase} "
        f"The allocation prioritizes candidate crops with higher Phase 3 suitability while respecting "
        f"all farm land, water, nutrient, and budget constraints. "
        f"{binding_phrase} "
        f"Optimization Mode: RESOURCE_ONLY (Economic optimization remains blocked pending historical yield data)."
    )

    return FarmOptimizationResult(
        status="OPTIMAL",
        optimization_mode=mode,
        objective=objective,
        candidate_crops=crop_names,
        crop_allocations_ha=alloc_dict,
        total_land_used_ha=total_land_used,
        land_remaining_ha=land_remaining,
        resource_usage=resource_usage,
        resource_remaining=resource_remaining,
        resource_utilization_pct=resource_utilization_pct,
        binding_resources=binding_resources,
        feasibility=True,
        constraint_violations=[],
        objective_value=opt_val,
        expected_profit_inr=None,  # Data Honesty: strictly None
        risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
        explanation=explanation,
        details={
            "solver_method": "highs",
            "solver_message": sol.message,
            "iterations": getattr(sol, "nit", None),
            "ineqlin_marginals": getattr(getattr(sol, "ineqlin", None), "marginals", None).tolist() if hasattr(getattr(sol, "ineqlin", None), "marginals") and getattr(sol, "ineqlin", None).marginals is not None else None,
            "constraint_names": ["land_ha", "water_liters", "nitrogen_kg", "phosphorus_kg", "potassium_kg", "budget_inr"],
        },
    )


# ==============================================================================
# SCENARIO COMPARISON OPTIMIZATION UTILITY
# ==============================================================================
def optimize_across_scenarios(
    farm_profile: FarmProfile,
    candidate_crops: Union[List[str], List[CropSuitabilityResult], Dict[str, float]],
    scenarios: Optional[List[ScenarioDefinition]] = None,
    top_n: int = 5,
) -> Dict[str, FarmOptimizationResult]:
    """
    Runs the deterministic LP optimizer against multiple Phase 5 scenarios
    (e.g., Baseline, Drought, Water Shortage, Excess Rainfall).
    Evaluates how acreage allocations shift when available resources contract or expand.
    """
    if scenarios is None:
        from engine.scenario_simulator import get_predefined_scenarios
        all_s = get_predefined_scenarios()
        scenarios = [s for s in all_s if s.scenario_name in ("Baseline", "Drought", "Water Shortage")]
        if not scenarios:
            scenarios = all_s[:3]

    results: Dict[str, FarmOptimizationResult] = {}
    from engine.scenario_simulator import apply_scenario

    for scen in scenarios:
        adj_profile, err = apply_scenario(farm_profile, scen)
        if adj_profile is None:
            results[scen.scenario_name] = FarmOptimizationResult(
                status="INVALID_SCENARIO",
                optimization_mode=OptimizationMode.RESOURCE_ONLY,
                objective=OptimizationObjective.RESOURCE_SUITABILITY,
                candidate_crops=[],
                crop_allocations_ha={},
                total_land_used_ha=0.0,
                land_remaining_ha=float(farm_profile.land_area_ha),
                resource_usage={},
                resource_remaining={},
                resource_utilization_pct={},
                binding_resources=[],
                feasibility=False,
                constraint_violations=[f"Scenario boundary error: {err}"],
                objective_value=None,
                expected_profit_inr=None,
                risk_status="BLOCKED_INSUFFICIENT_RISK_DATA",
                explanation=f"Scenario {scen.scenario_name} rejected: {err}",
            )
        else:
            opt_res = optimize_farm_allocation(
                farm_profile=adj_profile,
                candidate_crops=candidate_crops,
                top_n=top_n,
                scenario_input=ScenarioOptimizationInput(
                    scenario_id=scen.scenario_id,
                    scenario_name=scen.scenario_name,
                    scenario_probability=scen.probability,
                ),
            )
            results[scen.scenario_name] = opt_res

    return results
