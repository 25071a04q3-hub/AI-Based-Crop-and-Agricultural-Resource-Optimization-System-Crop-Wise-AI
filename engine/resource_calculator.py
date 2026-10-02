"""
FarmTwin — Agricultural Resource Calculation & Resource Balance Engine.

Phase 6: Deterministic Resource Requirement & Resource Balance Engine.
- Computes per-hectare and farm-level input consumption profiles (water, N-P-K, budget, labour).
- Compares crop demands directly against FarmProfile inventories.
- Evaluates feasibility, surplus/deficits, and utilization percentages without performing optimization.
- Supports single-crop and multi-crop portfolio aggregations.
- Seamlessly integrates with Phase 2 FarmProfile and Phase 5 scenario transformations.

CRITICAL DATA HONESTY RULES:
--------------------------------------------------------------------------------
1. Only values present in config/crops_profile.json are used (water_req_mm, N, P, K, cost_per_ha).
2. Labour requirements are NOT present in config/crops_profile.json and are strictly reported
   as DATA_UNAVAILABLE without fabricating mock numbers.
3. Fertilizer/cultivation cost is reported with source disclosure; no synthetic prices are added.
4. Rainfall is NOT conflated with irrigation water.
5. This module is a deterministic arithmetic calculation layer — it does NOT optimize.
--------------------------------------------------------------------------------
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from engine.profile import FarmProfile

# ==========================================
# STRICT PHYSICAL & FINANCIAL CONSTANTS
# ==========================================
TONNE_TO_QUINTAL: float = 10.0      # 1 metric tonne = 10 quintals
MM_TO_M3_PER_HA: float = 10.0       # 1 mm water depth over 1 hectare = 10 m³
LITERS_PER_M3: float = 1000.0       # 1 m³ = 1,000 liters
LITERS_PER_MM_HA: float = 10000.0   # 1 mm depth over 1 ha = 10 m³ * 1000 L/m³ = 10,000 liters

BASE_DIR = Path(__file__).resolve().parent.parent
CROPS_CONFIG_PATH = BASE_DIR / "config" / "crops_profile.json"


# ==========================================
# PURE CONVERSION UTILITIES
# ==========================================
def revenue_per_ha(yield_t_per_ha: float, price_per_quintal: float) -> float:
    """
    Calculates gross revenue per hectare in INR.
    Yield is in tonnes/ha, market price in INR/quintal.
    Revenue = yield (t/ha) * 10 (quintals/t) * price (INR/quintal).
    """
    if yield_t_per_ha < 0 or price_per_quintal < 0:
        raise ValueError("Yield and price must be non-negative values.")
    return round(float(yield_t_per_ha * TONNE_TO_QUINTAL * price_per_quintal), 4)


def water_mm_to_m3_per_ha(water_mm: float) -> float:
    """
    Converts water irrigation requirement from mm depth over 1 ha to volume in m³/ha.
    1 mm over 1 ha = 10 m³.
    """
    if water_mm < 0:
        raise ValueError("Water depth must be non-negative.")
    return round(float(water_mm * MM_TO_M3_PER_HA), 4)


def water_mm_to_liters_per_ha(water_mm: float) -> float:
    """
    Converts water irrigation requirement from mm depth over 1 ha to volume in liters/ha.
    1 mm over 1 ha = 10 m³ = 10,000 liters.
    """
    if water_mm < 0:
        raise ValueError("Water depth must be non-negative.")
    return round(float(water_mm * LITERS_PER_MM_HA), 4)


def m3_to_liters(volume_m3: float) -> float:
    """Converts cubic meters (m³) to liters (L)."""
    if volume_m3 < 0:
        raise ValueError("Volume must be non-negative.")
    return round(float(volume_m3 * LITERS_PER_M3), 4)


def liters_to_m3(volume_liters: float) -> float:
    """Converts liters (L) to cubic meters (m³)."""
    if volume_liters < 0:
        raise ValueError("Volume must be non-negative.")
    return round(float(volume_liters / LITERS_PER_M3), 4)


# ==========================================
# DATA CONTRACTS
# ==========================================
class CropResourceProfile(BaseModel):
    """
    Agronomic per-hectare resource requirements for a specific crop.
    Sourced from config/crops_profile.json.
    """
    crop_name: str = Field(description="Normalized lowercase crop identifier")
    water_req_mm: Optional[float] = Field(
        default=None, description="Water requirement in mm depth over 1 crop season"
    )
    water_per_ha_liters: float = Field(
        description="Water requirement in liters per hectare (1 mm = 10,000 L/ha)"
    )
    nitrogen_per_ha_kg: float = Field(description="Recommended Nitrogen (N) requirement in kg/ha")
    phosphorus_per_ha_kg: float = Field(description="Recommended Phosphorus (P) requirement in kg/ha")
    potassium_per_ha_kg: float = Field(description="Recommended Potassium (K) requirement in kg/ha")
    cost_per_ha_inr: Optional[float] = Field(
        default=None, description="Estimated total cultivation/input cost in INR per hectare"
    )
    labour_days_per_ha: Optional[float] = Field(
        default=None, description="Labour requirement in person-days per hectare (null if unrecorded)"
    )
    duration_days: Optional[int] = Field(default=None, description="Crop duration from sowing to harvest")
    price_per_quintal_inr: Optional[float] = Field(default=None, description="Benchmark market price in INR/quintal")
    data_status: str = Field(
        default="VALID", description="Data availability status (e.g. VALID, PARTIAL_NO_LABOUR)"
    )
    source: str = Field(default="config/crops_profile.json", description="Source configuration file")


class CropResourceRequirement(BaseModel):
    """
    Total resource demand for growing a specified crop over a specific land area.
    """
    crop_name: str
    land_area_ha: float = Field(gt=0, description="Allocated land area in hectares (must be > 0)")
    water_required_liters: float = Field(ge=0, description="Total water demand in liters")
    nitrogen_required_kg: float = Field(ge=0, description="Total Nitrogen demand in kg")
    phosphorus_required_kg: float = Field(ge=0, description="Total Phosphorus demand in kg")
    potassium_required_kg: float = Field(ge=0, description="Total Potassium demand in kg")
    fertilizer_cost_inr: Optional[float] = Field(
        default=None, ge=0, description="Estimated input cost in INR (null if cost unrecorded)"
    )
    labour_required_days: Optional[float] = Field(
        default=None, ge=0, description="Estimated labour in person-days (null if unrecorded)"
    )
    data_status: str = Field(description="Data completeness status (e.g. AVAILABLE, PARTIAL_NO_LABOUR)")
    explanation: str = Field(description="Summary of calculated requirements")


class ResourceBalanceItem(BaseModel):
    """
    Single resource comparison: Available vs Required vs Remaining, with utilization and feasibility.
    """
    resource_name: str = Field(description="Resource identifier (e.g. water, nitrogen, budget)")
    unit: str = Field(description="Measurement unit (e.g. liters, kg, INR, person-days, ha)")
    available: Optional[float] = Field(default=None, description="Total farm available capacity")
    required: Optional[float] = Field(default=None, description="Total crop/portfolio demand")
    remaining: Optional[float] = Field(default=None, description="Available minus Required (can be negative)")
    surplus_or_deficit: Optional[float] = Field(
        default=None, description="Positive = surplus, Negative = deficit"
    )
    utilization_pct: Optional[float] = Field(
        default=None, description="Utilization percentage: (Required / Available) * 100"
    )
    is_feasible: bool = Field(description="True if required <= available, False if deficit exists")
    status: str = Field(description="FEASIBLE, INSUFFICIENT, or DATA_UNAVAILABLE")
    details: str = Field(default="", description="Diagnostic explanation")


class ResourceBalance(BaseModel):
    """
    Comprehensive multi-resource balance sheet comparing all operational resources.
    """
    land: ResourceBalanceItem
    water: ResourceBalanceItem
    nitrogen: ResourceBalanceItem
    phosphorus: ResourceBalanceItem
    potassium: ResourceBalanceItem
    budget: ResourceBalanceItem
    labour: ResourceBalanceItem
    overall_feasible: bool = Field(description="True if all evaluated constraints are satisfied")
    constraint_violations: List[str] = Field(
        default_factory=list, description="List of all resource deficits / violation messages"
    )
    summary: str = Field(description="High-level feasibility summary")


class ResourceCalculationReport(BaseModel):
    """
    Comprehensive audit report of crop/portfolio resource requirements and farm balance.
    """
    entity_type: str = Field(description="'SINGLE_CROP' or 'PORTFOLIO'")
    crop_allocations: Dict[str, float] = Field(
        description="Mapping of crop names to allocated land in hectares"
    )
    total_land_used_ha: float = Field(ge=0, description="Sum of allocated hectares")
    land_remaining_ha: float = Field(description="Farm available land minus allocated land")
    requirements: Dict[str, CropResourceRequirement] = Field(
        description="Per-crop requirement breakdowns"
    )
    total_water_liters: float = Field(ge=0, description="Total aggregated water in liters")
    total_n_kg: float = Field(ge=0, description="Total aggregated Nitrogen in kg")
    total_p_kg: float = Field(ge=0, description="Total aggregated Phosphorus in kg")
    total_k_kg: float = Field(ge=0, description="Total aggregated Potassium in kg")
    total_cost_inr: Optional[float] = Field(default=None, description="Total input cost in INR")
    total_labour_days: Optional[float] = Field(default=None, description="Total labour days")
    balance: ResourceBalance = Field(description="Resource balance versus farm profile")
    is_feasible: bool = Field(description="True if all constraints are satisfied")
    constraint_violations: List[str] = Field(default_factory=list)
    data_status: str = Field(description="Data availability indicator")
    explanation: str = Field(description="Human-readable decision explanation")


# ==========================================
# REPOSITORY DATA LOADING & CACHING
# ==========================================
_CROP_PROFILES_CACHE: Optional[Dict[str, CropResourceProfile]] = None


def load_raw_crops_profile() -> Dict[str, Any]:
    """Loads raw json dictionary from config/crops_profile.json."""
    if CROPS_CONFIG_PATH.exists():
        with open(CROPS_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_all_crop_resource_profiles(force_reload: bool = False) -> Dict[str, CropResourceProfile]:
    """
    Parses and returns CropResourceProfile for all crops in config/crops_profile.json.
    Normalizes water depth from mm to liters/ha (1 mm = 10,000 L/ha).
    Notes missing labour data honestly.
    """
    global _CROP_PROFILES_CACHE
    if _CROP_PROFILES_CACHE is not None and not force_reload:
        return _CROP_PROFILES_CACHE

    raw_data = load_raw_crops_profile()
    profiles: Dict[str, CropResourceProfile] = {}

    for crop_raw_name, crop_data in raw_data.items():
        clean_name = crop_raw_name.strip().lower()

        water_mm = float(crop_data.get("water_req_mm", 0.0))
        water_liters_ha = round(water_mm * LITERS_PER_MM_HA, 2)

        n_req = float(crop_data.get("n_req_kg_ha", 0.0))
        p_req = float(crop_data.get("p_req_kg_ha", 0.0))
        k_req = float(crop_data.get("k_req_kg_ha", 0.0))
        cost_val = crop_data.get("cost_per_ha")
        cost_inr = float(cost_val) if cost_val is not None else None

        duration = crop_data.get("duration_days")
        price_q = crop_data.get("price_per_quintal")

        # Labour is not in crops_profile.json -> explicitly None
        labour_val = crop_data.get("labour_days_per_ha")
        labour_days = float(labour_val) if labour_val is not None else None

        status = "VALID" if labour_days is not None else "PARTIAL_NO_LABOUR"

        profiles[clean_name] = CropResourceProfile(
            crop_name=clean_name,
            water_req_mm=water_mm,
            water_per_ha_liters=water_liters_ha,
            nitrogen_per_ha_kg=n_req,
            phosphorus_per_ha_kg=p_req,
            potassium_per_ha_kg=k_req,
            cost_per_ha_inr=cost_inr,
            labour_days_per_ha=labour_days,
            duration_days=int(duration) if duration is not None else None,
            price_per_quintal_inr=float(price_q) if price_q is not None else None,
            data_status=status,
            source="config/crops_profile.json",
        )

    _CROP_PROFILES_CACHE = profiles
    return _CROP_PROFILES_CACHE


def get_crop_resource_profile(crop_name: str) -> Optional[CropResourceProfile]:
    """
    Retrieves the CropResourceProfile for a specific crop.
    Returns None if the crop is not in config/crops_profile.json.
    """
    if not isinstance(crop_name, str):
        return None
    profiles = get_all_crop_resource_profiles()
    return profiles.get(crop_name.strip().lower())


# ==========================================
# DETERMINISTIC REQUIREMENT CALCULATIONS
# ==========================================
def calculate_crop_requirement(crop_name: str, land_area_ha: float) -> CropResourceRequirement:
    """
    Calculates total resource requirements for a single crop given allocated land area.
    Formula:
      water_required = water_per_ha_liters * land_area_ha
      N_required = nitrogen_per_ha_kg * land_area_ha
      P_required = phosphorus_per_ha_kg * land_area_ha
      K_required = potassium_per_ha_kg * land_area_ha
      cost_required = cost_per_ha_inr * land_area_ha (if cost present)
      labour_required = labour_days_per_ha * land_area_ha (if labour present)
    """
    if not isinstance(crop_name, str) or not crop_name.strip():
        raise ValueError("Crop name must be a non-empty string.")
    if land_area_ha <= 0:
        raise ValueError(f"Land area must be greater than zero. Received: {land_area_ha}")

    clean_name = crop_name.strip().lower()
    profile = get_crop_resource_profile(clean_name)

    if profile is None:
        raise ValueError(
            f"Crop '{crop_name}' is not found in config/crops_profile.json. "
            f"Cannot calculate requirements without validated agronomic data."
        )

    water_tot = round(profile.water_per_ha_liters * land_area_ha, 2)
    n_tot = round(profile.nitrogen_per_ha_kg * land_area_ha, 2)
    p_tot = round(profile.phosphorus_per_ha_kg * land_area_ha, 2)
    k_tot = round(profile.potassium_per_ha_kg * land_area_ha, 2)

    cost_tot = (
        round(profile.cost_per_ha_inr * land_area_ha, 2)
        if profile.cost_per_ha_inr is not None
        else None
    )
    labour_tot = (
        round(profile.labour_days_per_ha * land_area_ha, 2)
        if profile.labour_days_per_ha is not None
        else None
    )

    data_status = "COMPLETE" if labour_tot is not None and cost_tot is not None else "PARTIAL_NO_LABOUR"

    explanation = (
        f"{clean_name.capitalize()} on {land_area_ha:.2f} ha requires: "
        f"{water_tot:,.0f} L water, {n_tot:.1f} kg N, {p_tot:.1f} kg P, {k_tot:.1f} kg K."
    )
    if cost_tot is not None:
        explanation += f" Est. cost: ₹{cost_tot:,.0f}."
    if labour_tot is None:
        explanation += " Labour: DATA_UNAVAILABLE."

    return CropResourceRequirement(
        crop_name=clean_name,
        land_area_ha=round(land_area_ha, 4),
        water_required_liters=water_tot,
        nitrogen_required_kg=n_tot,
        phosphorus_required_kg=p_tot,
        potassium_required_kg=k_tot,
        fertilizer_cost_inr=cost_tot,
        labour_required_days=labour_tot,
        data_status=data_status,
        explanation=explanation,
    )


# ==========================================
# RESOURCE BALANCE & FEASIBILITY ENGINE
# ==========================================
def _compute_balance_item(
    resource_name: str,
    unit: str,
    available: Optional[float],
    required: Optional[float],
) -> ResourceBalanceItem:
    """
    Computes feasibility, remaining balance, surplus/deficit, and utilization percentage
    for a single resource. Pure calculation with zero division safety.
    """
    if available is None or required is None:
        return ResourceBalanceItem(
            resource_name=resource_name,
            unit=unit,
            available=available,
            required=required,
            remaining=None,
            surplus_or_deficit=None,
            utilization_pct=None,
            is_feasible=True,
            status="DATA_UNAVAILABLE",
            details=f"{resource_name.capitalize()} benchmark data is not recorded in repository.",
        )

    avail_val = float(available)
    req_val = float(required)
    rem_val = round(avail_val - req_val, 2)
    surplus_def = rem_val

    # Utilization %: handle zero available safely
    if avail_val > 0:
        util_pct = round((req_val / avail_val) * 100.0, 2)
    elif req_val == 0:
        util_pct = 0.0
    else:
        # Available is 0 but required > 0
        util_pct = None

    is_feasible = req_val <= avail_val
    status = "FEASIBLE" if is_feasible else "INSUFFICIENT"

    if is_feasible:
        details = f"Requirement ({req_val:,.1f} {unit}) is within available capacity ({avail_val:,.1f} {unit})."
    else:
        deficit_amt = abs(rem_val)
        details = (
            f"Deficit: Requires {req_val:,.1f} {unit}, but only {avail_val:,.1f} {unit} available "
            f"(short by {deficit_amt:,.1f} {unit})."
        )

    return ResourceBalanceItem(
        resource_name=resource_name,
        unit=unit,
        available=avail_val,
        required=req_val,
        remaining=rem_val,
        surplus_or_deficit=surplus_def,
        utilization_pct=util_pct,
        is_feasible=is_feasible,
        status=status,
        details=details,
    )


def compute_resource_balance(
    land_used_ha: float,
    water_req_liters: float,
    n_req_kg: float,
    p_req_kg: float,
    k_req_kg: float,
    cost_inr: Optional[float],
    labour_days: Optional[float],
    farm_profile: FarmProfile,
) -> ResourceBalance:
    """
    Computes full multi-resource balance sheet against the FarmProfile.
    The original FarmProfile is NOT modified.
    """
    if not isinstance(farm_profile, FarmProfile):
        raise TypeError(f"Expected FarmProfile instance, got {type(farm_profile).__name__}")

    # Extract farm available resources (standardized units)
    avail_land = float(farm_profile.land_area_ha)
    avail_water = float(farm_profile.water_liters)
    avail_n = float(farm_profile.available_n_kg)
    avail_p = float(farm_profile.available_p_kg)
    avail_k = float(farm_profile.available_k_kg)
    avail_budget = float(farm_profile.available_budget_inr)
    avail_labour = float(farm_profile.available_labour_days)

    # 1. Evaluate balance items
    item_land = _compute_balance_item("land", "ha", avail_land, land_used_ha)
    item_water = _compute_balance_item("water", "liters", avail_water, water_req_liters)
    item_n = _compute_balance_item("nitrogen", "kg", avail_n, n_req_kg)
    item_p = _compute_balance_item("phosphorus", "kg", avail_p, p_req_kg)
    item_k = _compute_balance_item("potassium", "kg", avail_k, k_req_kg)
    item_budget = _compute_balance_item("budget", "INR", avail_budget, cost_inr)
    item_labour = _compute_balance_item("labour", "person-days", avail_labour, labour_days)

    # 2. Collect all constraint violations
    violations: List[str] = []
    if not item_land.is_feasible:
        deficit = abs(item_land.remaining) if item_land.remaining is not None else 0
        violations.append(f"Land constraint exceeded: short by {deficit:.2f} ha (allocated {land_used_ha:.2f} ha of {avail_land:.2f} ha).")
    if not item_water.is_feasible:
        deficit = abs(item_water.remaining) if item_water.remaining is not None else 0
        violations.append(f"Water shortage: short by {deficit:,.0f} L (requires {water_req_liters:,.0f} L of {avail_water:,.0f} L).")
    if not item_n.is_feasible:
        deficit = abs(item_n.remaining) if item_n.remaining is not None else 0
        violations.append(f"Nitrogen deficit: short by {deficit:.1f} kg N (requires {n_req_kg:.1f} kg of {avail_n:.1f} kg).")
    if not item_p.is_feasible:
        deficit = abs(item_p.remaining) if item_p.remaining is not None else 0
        violations.append(f"Phosphorus deficit: short by {deficit:.1f} kg P (requires {p_req_kg:.1f} kg of {avail_p:.1f} kg).")
    if not item_k.is_feasible:
        deficit = abs(item_k.remaining) if item_k.remaining is not None else 0
        violations.append(f"Potassium deficit: short by {deficit:.1f} kg K (requires {k_req_kg:.1f} kg of {avail_k:.1f} kg).")
    if not item_budget.is_feasible:
        deficit = abs(item_budget.remaining) if item_budget.remaining is not None else 0
        violations.append(f"Budget deficit: short by ₹{deficit:,.0f} (requires ₹{cost_inr:,.0f} of ₹{avail_budget:,.0f}).")
    if not item_labour.is_feasible:
        deficit = abs(item_labour.remaining) if item_labour.remaining is not None else 0
        violations.append(f"Labour deficit: short by {deficit:.1f} days (requires {labour_days:.1f} of {avail_labour:.1f} days).")

    overall_feasible = len(violations) == 0

    if overall_feasible:
        summary = "All evaluated resource requirements are FEASIBLE under available farm inventories."
    else:
        summary = f"Plan is INFEASIBLE: {len(violations)} constraint violation(s) detected."

    return ResourceBalance(
        land=item_land,
        water=item_water,
        nitrogen=item_n,
        phosphorus=item_p,
        potassium=item_k,
        budget=item_budget,
        labour=item_labour,
        overall_feasible=overall_feasible,
        constraint_violations=violations,
        summary=summary,
    )


# ==========================================
# PUBLIC API: SINGLE-CROP & PORTFOLIO ENGINES
# ==========================================
def calculate_crop_resources(
    crop_name: str,
    land_area_ha: float,
    farm_profile: FarmProfile,
) -> ResourceCalculationReport:
    """
    Calculates resource requirements and balance for growing a single crop on a parcel.
    Pure calculation: does not mutate farm_profile.
    Compatible with scenario-adjusted FarmProfile instances from Phase 5.
    """
    req = calculate_crop_requirement(crop_name, land_area_ha)

    balance = compute_resource_balance(
        land_used_ha=req.land_area_ha,
        water_req_liters=req.water_required_liters,
        n_req_kg=req.nitrogen_required_kg,
        p_req_kg=req.phosphorus_required_kg,
        k_req_kg=req.potassium_required_kg,
        cost_inr=req.fertilizer_cost_inr,
        labour_days=req.labour_required_days,
        farm_profile=farm_profile,
    )

    clean_name = crop_name.strip().lower()
    rem_land = round(float(farm_profile.land_area_ha) - land_area_ha, 4)

    # Construct clean human-readable explanation
    exp_lines = [
        f"Single-Crop Plan: {clean_name.capitalize()} on {land_area_ha:.2f} ha (of {farm_profile.land_area_ha:.2f} ha available).",
        f"Water: Required {req.water_required_liters:,.0f} L | Available {farm_profile.water_liters:,.0f} L | "
        f"Remaining {balance.water.remaining:,.0f} L (Utilization: {balance.water.utilization_pct}%).",
        f"N-P-K: Required {req.nitrogen_required_kg:.1f}N, {req.phosphorus_required_kg:.1f}P, {req.potassium_required_kg:.1f}K kg.",
    ]
    if req.fertilizer_cost_inr is not None:
        exp_lines.append(
            f"Budget: Required ₹{req.fertilizer_cost_inr:,.0f} | Available ₹{farm_profile.available_budget_inr:,.0f} | "
            f"Remaining ₹{balance.budget.remaining:,.0f} (Utilization: {balance.budget.utilization_pct}%)."
        )
    if req.labour_required_days is None:
        exp_lines.append("Labour: DATA_UNAVAILABLE (not recorded in repository).")

    exp_lines.append(f"Status: {'FEASIBLE' if balance.overall_feasible else 'INFEASIBLE'}.")
    if balance.constraint_violations:
        exp_lines.append("Violations: " + "; ".join(balance.constraint_violations))

    explanation = "\n".join(exp_lines)

    return ResourceCalculationReport(
        entity_type="SINGLE_CROP",
        crop_allocations={clean_name: round(land_area_ha, 4)},
        total_land_used_ha=round(land_area_ha, 4),
        land_remaining_ha=rem_land,
        requirements={clean_name: req},
        total_water_liters=req.water_required_liters,
        total_n_kg=req.nitrogen_required_kg,
        total_p_kg=req.phosphorus_required_kg,
        total_k_kg=req.potassium_required_kg,
        total_cost_inr=req.fertilizer_cost_inr,
        total_labour_days=req.labour_required_days,
        balance=balance,
        is_feasible=balance.overall_feasible,
        constraint_violations=balance.constraint_violations,
        data_status=req.data_status,
        explanation=explanation,
    )


def calculate_portfolio_resources(
    crop_allocations: Dict[str, float],
    farm_profile: FarmProfile,
) -> ResourceCalculationReport:
    """
    Aggregates resource demands across a multi-crop portfolio:
      e.g. {"rice": 0.8, "maize": 0.7, "pigeonpeas": 0.5}
    Compares aggregated demand against the FarmProfile.
    Enforces land constraint: total_land_used <= farm_profile.land_area_ha.
    Pure arithmetic aggregation — does NOT optimize allocations.
    """
    if not isinstance(crop_allocations, dict) or not crop_allocations:
        raise ValueError("Crop allocations must be a non-empty dictionary of {crop_name: hectares}.")
    if not isinstance(farm_profile, FarmProfile):
        raise TypeError(f"Expected FarmProfile instance, got {type(farm_profile).__name__}")

    requirements_map: Dict[str, CropResourceRequirement] = {}
    total_land = 0.0
    total_water = 0.0
    total_n = 0.0
    total_p = 0.0
    total_k = 0.0
    total_cost: Optional[float] = 0.0
    total_labour: Optional[float] = None
    all_costs_present = True

    clean_allocations: Dict[str, float] = {}

    for crop_name, area in crop_allocations.items():
        if area <= 0:
            raise ValueError(f"Allocated area for '{crop_name}' must be greater than zero. Received: {area}")
        clean_name = crop_name.strip().lower()
        clean_allocations[clean_name] = round(area, 4)

        req = calculate_crop_requirement(clean_name, area)
        requirements_map[clean_name] = req

        total_land += req.land_area_ha
        total_water += req.water_required_liters
        total_n += req.nitrogen_required_kg
        total_p += req.phosphorus_required_kg
        total_k += req.potassium_required_kg

        if req.fertilizer_cost_inr is not None and all_costs_present:
            total_cost = (total_cost or 0.0) + req.fertilizer_cost_inr
        else:
            all_costs_present = False
            total_cost = None

        if req.labour_required_days is not None:
            total_labour = (total_labour or 0.0) + req.labour_required_days

    total_land = round(total_land, 4)
    total_water = round(total_water, 2)
    total_n = round(total_n, 2)
    total_p = round(total_p, 2)
    total_k = round(total_k, 2)
    if total_cost is not None:
        total_cost = round(total_cost, 2)

    balance = compute_resource_balance(
        land_used_ha=total_land,
        water_req_liters=total_water,
        n_req_kg=total_n,
        p_req_kg=total_p,
        k_req_kg=total_k,
        cost_inr=total_cost,
        labour_days=total_labour,
        farm_profile=farm_profile,
    )

    rem_land = round(float(farm_profile.land_area_ha) - total_land, 4)

    # Explanation construction
    alloc_summary = ", ".join([f"{k.capitalize()}: {v:.2f} ha" for k, v in clean_allocations.items()])
    exp_lines = [
        f"Multi-Crop Portfolio: {alloc_summary}.",
        f"Total Land Used: {total_land:.2f} ha / {farm_profile.land_area_ha:.2f} ha "
        f"(Remaining: {rem_land:.2f} ha, Utilization: {balance.land.utilization_pct}%).",
        f"Total Water: {total_water:,.0f} L / {farm_profile.water_liters:,.0f} L "
        f"(Remaining: {balance.water.remaining:,.0f} L, Utilization: {balance.water.utilization_pct}%).",
        f"Total N-P-K: {total_n:.1f}N, {total_p:.1f}P, {total_k:.1f}K kg.",
    ]
    if total_cost is not None:
        exp_lines.append(
            f"Total Budget: ₹{total_cost:,.0f} / ₹{farm_profile.available_budget_inr:,.0f} "
            f"(Remaining: ₹{balance.budget.remaining:,.0f}, Utilization: {balance.budget.utilization_pct}%)."
        )
    if total_labour is None:
        exp_lines.append("Labour: DATA_UNAVAILABLE (not recorded in repository).")

    exp_lines.append(f"Status: {'FEASIBLE' if balance.overall_feasible else 'INFEASIBLE'}.")
    if balance.constraint_violations:
        exp_lines.append("Violations: " + "; ".join(balance.constraint_violations))

    explanation = "\n".join(exp_lines)
    data_status = "COMPLETE" if total_labour is not None else "PARTIAL_NO_LABOUR"

    return ResourceCalculationReport(
        entity_type="PORTFOLIO",
        crop_allocations=clean_allocations,
        total_land_used_ha=total_land,
        land_remaining_ha=rem_land,
        requirements=requirements_map,
        total_water_liters=total_water,
        total_n_kg=total_n,
        total_p_kg=total_p,
        total_k_kg=total_k,
        total_cost_inr=total_cost,
        total_labour_days=total_labour,
        balance=balance,
        is_feasible=balance.overall_feasible,
        constraint_violations=balance.constraint_violations,
        data_status=data_status,
        explanation=explanation,
    )
