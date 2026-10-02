"""
FarmTwin — Future Scenario Simulator & Farm Stress Testing Engine.

Implements multi-future scenario definition, stress condition transformations,
boundary validation, reproducible randomized scenario generation, and scenario evaluation.

CORE ARCHITECTURAL PRINCIPLE:
--------------------------------------------------------------------------------
Scenario Generation and Condition Transformation do NOT depend on Scenario Outcome Availability.
Because Phase 4 model training is currently blocked (no authentic historical yield data),
scenario outcome fields (yield, production, revenue, profit) strictly remain None / unavailable,
and outcomes are evaluated with status 'BLOCKED_NO_YIELD_MODEL'.
No fake numbers, synthetic yield, or fabricated profits are ever produced.
--------------------------------------------------------------------------------
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from engine.profile import FarmProfile
from engine.yield_prediction import get_or_train_yield_models, predict_yield


class ScenarioCategory(str, Enum):
    """Categorical classification of agricultural future scenarios."""
    NORMAL = "NORMAL"
    WEATHER_STRESS = "WEATHER_STRESS"
    WATER_STRESS = "WATER_STRESS"
    INPUT_COST_STRESS = "INPUT_COST_STRESS"
    MARKET_STRESS = "MARKET_STRESS"
    COMBINED_STRESS = "COMBINED_STRESS"


class ScenarioStatus(str, Enum):
    """Execution status for scenario outcome evaluation."""
    READY = "READY"
    BLOCKED_NO_YIELD_MODEL = "BLOCKED_NO_YIELD_MODEL"
    INVALID_SCENARIO = "INVALID_SCENARIO"
    EVALUATION_ERROR = "EVALUATION_ERROR"


class ScenarioDefinition(BaseModel):
    """
    Structured data contract for agricultural stress scenarios.
    Specifies environmental, resource, and macroeconomic shock percentages/deltas.
    """
    scenario_id: str = Field(description="Unique identifier for the scenario")
    scenario_name: str = Field(description="Human-readable scenario name")
    category: ScenarioCategory = Field(
        default=ScenarioCategory.NORMAL, description="Scenario stress category"
    )
    description: str = Field(
        default="", description="Detailed contextual description of the scenario"
    )

    # Weather shocks
    rainfall_change_pct: float = Field(
        default=0.0, description="Percentage change in seasonal rainfall (-100% to +300%)"
    )
    temperature_change_c: float = Field(
        default=0.0, description="Absolute change in temperature in degrees Celsius (e.g. +2.5°C)"
    )
    humidity_change_pct: float = Field(
        default=0.0, description="Percentage point change in relative humidity (-50% to +50%)"
    )

    # Resource shocks
    water_change_pct: float = Field(
        default=0.0, description="Percentage change in available irrigation water (-100% to +100%)"
    )

    # Macroeconomic shocks (factor applied to future unit prices)
    fertilizer_price_change_pct: float = Field(
        default=0.0, description="Percentage change in fertilizer input costs (e.g. +25%)"
    )
    market_price_change_pct: float = Field(
        default=0.0, description="Percentage change in farm-gate market crop price (e.g. -15%)"
    )

    # Probability contract: must remain None unless empirical historical data exists
    probability: Optional[float] = Field(
        default=None, description="Empirical probability of occurrence (null if manual stress test)"
    )
    probability_source: Optional[str] = Field(
        default="Probability not estimated (prototype stress scenario)",
        description="Source citation for probability estimation"
    )


class ScenarioResult(BaseModel):
    """
    Structured outcome contract for an evaluated scenario.
    Distinctly separates scenario inputs/conditions from scenario outcomes.
    """
    scenario_id: str
    scenario_name: str
    category: ScenarioCategory
    status: ScenarioStatus

    # Transformed Physical & Economic Conditions
    adjusted_rainfall_mm: Optional[float] = None
    adjusted_temperature_c: Optional[float] = None
    adjusted_humidity_percent: Optional[float] = None
    adjusted_water_liters: Optional[float] = None
    adjusted_fertilizer_price_factor: float = 1.0
    adjusted_market_price_factor: float = 1.0

    # Yield & Production Outcomes (None when yield model is blocked)
    crop_name: Optional[str] = None
    yield_p10: Optional[float] = None
    yield_p50: Optional[float] = None
    yield_p90: Optional[float] = None
    production_p10: Optional[float] = None
    production_p50: Optional[float] = None
    production_p90: Optional[float] = None

    # Economic Outcomes (None until legitimate cost/revenue models exist)
    revenue: Optional[float] = None
    profit: Optional[float] = None

    # Audit & Explanation
    explanation: str = Field(description="Factual, human-readable explanation of the scenario conditions")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic details or error logs")


# ==============================================================================
# PREDEFINED STANDARD SCENARIOS
# ==============================================================================

def get_predefined_scenarios() -> List[ScenarioDefinition]:
    """
    Returns the standard suite of 7 agricultural stress-test scenarios.
    These represent standardized agronomic stress assumptions for resilience testing.
    """
    return [
        ScenarioDefinition(
            scenario_id="SCEN-001",
            scenario_name="Baseline",
            category=ScenarioCategory.NORMAL,
            description="Normal operating conditions without climate or macroeconomic shocks.",
            rainfall_change_pct=0.0,
            temperature_change_c=0.0,
            humidity_change_pct=0.0,
            water_change_pct=0.0,
            fertilizer_price_change_pct=0.0,
            market_price_change_pct=0.0,
        ),
        ScenarioDefinition(
            scenario_id="SCEN-002",
            scenario_name="Drought",
            category=ScenarioCategory.WEATHER_STRESS,
            description="Severe meteorological drought: rainfall deficit of 30% and 20% irrigation reduction.",
            rainfall_change_pct=-30.0,
            temperature_change_c=+1.5,
            humidity_change_pct=-10.0,
            water_change_pct=-20.0,
            fertilizer_price_change_pct=0.0,
            market_price_change_pct=0.0,
        ),
        ScenarioDefinition(
            scenario_id="SCEN-003",
            scenario_name="Excess Rainfall",
            category=ScenarioCategory.WEATHER_STRESS,
            description="Abnormal monsoon rainfall surge (+30%) with elevated humidity.",
            rainfall_change_pct=+30.0,
            temperature_change_c=-0.5,
            humidity_change_pct=+15.0,
            water_change_pct=+10.0,
            fertilizer_price_change_pct=0.0,
            market_price_change_pct=0.0,
        ),
        ScenarioDefinition(
            scenario_id="SCEN-004",
            scenario_name="Water Shortage",
            category=ScenarioCategory.WATER_STRESS,
            description="Severe irrigation constraint (-30% usable water) due to reservoir or canal rationing.",
            rainfall_change_pct=0.0,
            temperature_change_c=0.0,
            humidity_change_pct=0.0,
            water_change_pct=-30.0,
            fertilizer_price_change_pct=0.0,
            market_price_change_pct=0.0,
        ),
        ScenarioDefinition(
            scenario_id="SCEN-005",
            scenario_name="Fertilizer Price Shock",
            category=ScenarioCategory.INPUT_COST_STRESS,
            description="Fertilizer cost inflation (+25%) while physical farm conditions remain normal.",
            rainfall_change_pct=0.0,
            temperature_change_c=0.0,
            humidity_change_pct=0.0,
            water_change_pct=0.0,
            fertilizer_price_change_pct=+25.0,
            market_price_change_pct=0.0,
        ),
        ScenarioDefinition(
            scenario_id="SCEN-006",
            scenario_name="Market Price Shock",
            category=ScenarioCategory.MARKET_STRESS,
            description="Wholesale farm-gate crop prices drop by 15% due to regional oversupply.",
            rainfall_change_pct=0.0,
            temperature_change_c=0.0,
            humidity_change_pct=0.0,
            water_change_pct=0.0,
            fertilizer_price_change_pct=0.0,
            market_price_change_pct=-15.0,
        ),
        ScenarioDefinition(
            scenario_id="SCEN-007",
            scenario_name="Combined Stress",
            category=ScenarioCategory.COMBINED_STRESS,
            description="Compounded crisis: drought (-30% rain, -20% water), fertilizer inflation (+25%), and price crash (-15%).",
            rainfall_change_pct=-30.0,
            temperature_change_c=+2.0,
            humidity_change_pct=-10.0,
            water_change_pct=-20.0,
            fertilizer_price_change_pct=+25.0,
            market_price_change_pct=-15.0,
        ),
    ]


# ==============================================================================
# FARM CONDITION TRANSFORMATION & BOUNDARY VALIDATION
# ==============================================================================

def apply_scenario(
    profile: FarmProfile,
    scenario: ScenarioDefinition
) -> Tuple[Optional[FarmProfile], Optional[str]]:
    """
    Applies scenario shocks to a farm profile without mutating the original object.
    Enforces strict physical boundaries:
    - rainfall_mm >= 0
    - available_water >= 0
    - humidity_percent in [0.0, 100.0]
    - temperature_c in [-20.0, 60.0]

    Returns:
        (adjusted_profile, None) if successful and physically valid.
        (None, error_message) if scenario violates physical boundaries or profile invariants.
    """
    if not isinstance(profile, FarmProfile):
        raise TypeError(f"Expected FarmProfile instance, got {type(profile).__name__}")
    if not isinstance(scenario, ScenarioDefinition):
        raise TypeError(f"Expected ScenarioDefinition instance, got {type(scenario).__name__}")

    # 1. Transform rainfall
    raw_rain = float(profile.rainfall_mm)
    rain_delta = raw_rain * (scenario.rainfall_change_pct / 100.0)
    adjusted_rain = raw_rain + rain_delta
    if adjusted_rain < 0:
        return None, (
            f"Physical Boundary Violation: Rainfall cannot become negative "
            f"({raw_rain:.1f}mm + {scenario.rainfall_change_pct:.1f}% = {adjusted_rain:.1f}mm)."
        )

    # 2. Transform temperature
    raw_temp = float(profile.temperature_c)
    adjusted_temp = raw_temp + scenario.temperature_change_c
    if adjusted_temp < -20.0 or adjusted_temp > 60.0:
        return None, (
            f"Physical Boundary Violation: Temperature {adjusted_temp:.1f}°C is outside valid range [-20°C, 60°C]."
        )

    # 3. Transform humidity
    raw_hum = float(profile.humidity_percent)
    adjusted_hum = raw_hum + scenario.humidity_change_pct
    if adjusted_hum < 0.0 or adjusted_hum > 100.0:
        return None, (
            f"Physical Boundary Violation: Humidity {adjusted_hum:.1f}% is outside physical range [0%, 100%]."
        )

    # 4. Transform water
    raw_water = float(profile.available_water)
    water_delta = raw_water * (scenario.water_change_pct / 100.0)
    adjusted_water = raw_water + water_delta
    if adjusted_water < 0:
        return None, (
            f"Physical Boundary Violation: Usable water cannot become negative "
            f"({raw_water:.1f} + {scenario.water_change_pct:.1f}% = {adjusted_water:.1f})."
        )

    # 5. Construct a fresh, independent FarmProfile copy
    profile_dict = profile.model_dump()
    profile_dict["rainfall_mm"] = round(adjusted_rain, 2)
    profile_dict["temperature_c"] = round(adjusted_temp, 2)
    profile_dict["humidity_percent"] = round(adjusted_hum, 2)
    profile_dict["available_water"] = round(adjusted_water, 2)

    try:
        adjusted_profile = FarmProfile(**profile_dict)
        return adjusted_profile, None
    except Exception as exc:
        return None, f"FarmProfile Invariant Error: {str(exc)}"


# ==============================================================================
# RANDOM SCENARIO GENERATION (CONTROLLED PROTOTYPE)
# ==============================================================================

def generate_random_scenarios(
    n_scenarios: int = 100,
    random_state: int = 42,
    rainfall_range_pct: Tuple[float, float] = (-50.0, 50.0),
    temp_range_c: Tuple[float, float] = (-5.0, 5.0),
    humidity_range_pct: Tuple[float, float] = (-25.0, 25.0),
    water_range_pct: Tuple[float, float] = (-40.0, 40.0),
    fert_price_range_pct: Tuple[float, float] = (-20.0, 40.0),
    market_price_range_pct: Tuple[float, float] = (-30.0, 30.0),
) -> List[ScenarioDefinition]:
    """
    Generates synthetic randomized stress-test scenarios for testing.
    Uses fixed random_state for strict reproducibility.

    DISCLAIMER:
    These are stress-test scenarios for software testing, NOT calibrated climate forecasts.
    """
    if n_scenarios <= 0:
        return []

    rng = np.random.default_rng(random_state)
    scenarios: List[ScenarioDefinition] = []

    for i in range(1, n_scenarios + 1):
        r_rain = float(rng.uniform(*rainfall_range_pct))
        r_temp = float(rng.uniform(*temp_range_c))
        r_hum = float(rng.uniform(*humidity_range_pct))
        r_water = float(rng.uniform(*water_range_pct))
        r_fert = float(rng.uniform(*fert_price_range_pct))
        r_mkt = float(rng.uniform(*market_price_range_pct))

        # Categorize dominant stress
        if r_rain < -20.0 and r_water < -15.0 and (r_fert > 15.0 or r_mkt < -15.0):
            cat = ScenarioCategory.COMBINED_STRESS
        elif r_water < -20.0:
            cat = ScenarioCategory.WATER_STRESS
        elif abs(r_rain) > 25.0 or abs(r_temp) > 3.0:
            cat = ScenarioCategory.WEATHER_STRESS
        elif r_fert > 20.0:
            cat = ScenarioCategory.INPUT_COST_STRESS
        elif r_mkt < -15.0:
            cat = ScenarioCategory.MARKET_STRESS
        else:
            cat = ScenarioCategory.NORMAL

        desc = (
            f"Randomized Stress Scenario #{i}: "
            f"Rainfall {r_rain:+.1f}%, Temp {r_temp:+.1f}°C, Water {r_water:+.1f}%, "
            f"Fert Price {r_fert:+.1f}%, Market Price {r_mkt:+.1f}%."
        )

        scen = ScenarioDefinition(
            scenario_id=f"RND-{i:04d}",
            scenario_name=f"Random Stress #{i}",
            category=cat,
            description=desc,
            rainfall_change_pct=round(r_rain, 1),
            temperature_change_c=round(r_temp, 1),
            humidity_change_pct=round(r_hum, 1),
            water_change_pct=round(r_water, 1),
            fertilizer_price_change_pct=round(r_fert, 1),
            market_price_change_pct=round(r_mkt, 1),
            probability=None,
            probability_source="Prototype randomized stress distribution (uncalibrated)",
        )
        scenarios.append(scen)

    return scenarios


def generate_scenarios(
    include_predefined: bool = True,
    n_random: int = 0,
    random_state: int = 42
) -> List[ScenarioDefinition]:
    """
    Unified generator returning predefined and/or randomized scenarios.
    """
    scenarios: List[ScenarioDefinition] = []
    if include_predefined:
        scenarios.extend(get_predefined_scenarios())
    if n_random > 0:
        scenarios.extend(generate_random_scenarios(n_scenarios=n_random, random_state=random_state))
    return scenarios


# ==============================================================================
# SCENARIO SIMULATION & EVALUATION ENGINE
# ==============================================================================

def simulate_scenario(
    profile: FarmProfile,
    scenario: ScenarioDefinition,
    crop_name: Optional[str] = None,
) -> ScenarioResult:
    """
    Evaluates a single scenario against a farm profile.
    Separates condition transformations from outcome evaluation.

    If Phase 4 yield models are blocked:
    - Yield/Production/Revenue/Profit outcomes remain None.
    - Status is set to BLOCKED_NO_YIELD_MODEL.
    - No fabricated numbers are generated.
    """
    # 1. Apply scenario transformation
    adjusted_profile, error_msg = apply_scenario(profile, scenario)

    fert_price_factor = round(1.0 + (scenario.fertilizer_price_change_pct / 100.0), 4)
    market_price_factor = round(1.0 + (scenario.market_price_change_pct / 100.0), 4)

    # Handle boundary/validation errors
    if adjusted_profile is None:
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.scenario_name,
            category=scenario.category,
            status=ScenarioStatus.INVALID_SCENARIO,
            adjusted_rainfall_mm=None,
            adjusted_temperature_c=None,
            adjusted_humidity_percent=None,
            adjusted_water_liters=None,
            adjusted_fertilizer_price_factor=fert_price_factor,
            adjusted_market_price_factor=market_price_factor,
            crop_name=crop_name,
            yield_p10=None,
            yield_p50=None,
            yield_p90=None,
            production_p10=None,
            production_p50=None,
            production_p90=None,
            revenue=None,
            profit=None,
            explanation=f"Scenario rejected due to boundary violation: {error_msg}",
            details={"error": error_msg},
        )

    # 2. Extract adjusted physical conditions
    adj_rain = float(adjusted_profile.rainfall_mm)
    adj_temp = float(adjusted_profile.temperature_c)
    adj_hum = float(adjusted_profile.humidity_percent)
    # Normalized water is stored in liters
    adj_water = float(adjusted_profile.water_liters)

    # 3. Build human-readable condition explanation
    explanation_parts: List[str] = []
    if scenario.rainfall_change_pct != 0.0:
        explanation_parts.append(f"Rainfall {scenario.rainfall_change_pct:+.1f}% ({adj_rain:.1f} mm)")
    if scenario.water_change_pct != 0.0:
        explanation_parts.append(f"Water {scenario.water_change_pct:+.1f}% ({adj_water:,.0f} L)")
    if scenario.temperature_change_c != 0.0:
        explanation_parts.append(f"Temperature {scenario.temperature_change_c:+.1f}°C ({adj_temp:.1f}°C)")
    if scenario.fertilizer_price_change_pct != 0.0:
        explanation_parts.append(f"Fertilizer cost {scenario.fertilizer_price_change_pct:+.1f}% (factor {fert_price_factor:.2f}x)")
    if scenario.market_price_change_pct != 0.0:
        explanation_parts.append(f"Market price {scenario.market_price_change_pct:+.1f}% (factor {market_price_factor:.2f}x)")

    if not explanation_parts:
        summary_explanation = "Baseline: No environmental or macroeconomic shocks applied."
    else:
        summary_explanation = f"Scenario Conditions: {', '.join(explanation_parts)}."

    # 4. Phase 4 Yield Model Integration Adapter
    # Check if a legitimate historical yield model is available
    yield_models_bundle, yield_status_info = get_or_train_yield_models()

    if yield_models_bundle is None or crop_name is None:
        # Expected State in Phase 5: Yield model blocked due to lack of historical dataset
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.scenario_name,
            category=scenario.category,
            status=ScenarioStatus.BLOCKED_NO_YIELD_MODEL,
            adjusted_rainfall_mm=adj_rain,
            adjusted_temperature_c=adj_temp,
            adjusted_humidity_percent=adj_hum,
            adjusted_water_liters=adj_water,
            adjusted_fertilizer_price_factor=fert_price_factor,
            adjusted_market_price_factor=market_price_factor,
            crop_name=crop_name,
            yield_p10=None,
            yield_p50=None,
            yield_p90=None,
            production_p10=None,
            production_p50=None,
            production_p90=None,
            revenue=None,
            profit=None,
            explanation=summary_explanation,
            details={
                "yield_status": yield_status_info.get("status", "BLOCKED"),
                "reason": "Yield outcomes are unavailable because historical yield model training is blocked.",
            },
        )

    # 5. Future Case: Yield model is available
    try:
        yield_pred = predict_yield(adjusted_profile, crop_name)
        if yield_pred.status != "AVAILABLE":
            return ScenarioResult(
                scenario_id=scenario.scenario_id,
                scenario_name=scenario.scenario_name,
                category=scenario.category,
                status=ScenarioStatus.BLOCKED_NO_YIELD_MODEL,
                adjusted_rainfall_mm=adj_rain,
                adjusted_temperature_c=adj_temp,
                adjusted_humidity_percent=adj_hum,
                adjusted_water_liters=adj_water,
                adjusted_fertilizer_price_factor=fert_price_factor,
                adjusted_market_price_factor=market_price_factor,
                crop_name=crop_name,
                yield_p10=None,
                yield_p50=None,
                yield_p90=None,
                production_p10=None,
                production_p50=None,
                production_p90=None,
                revenue=None,
                profit=None,
                explanation=summary_explanation,
                details={"yield_status": yield_pred.status},
            )

        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.scenario_name,
            category=scenario.category,
            status=ScenarioStatus.READY,
            adjusted_rainfall_mm=adj_rain,
            adjusted_temperature_c=adj_temp,
            adjusted_humidity_percent=adj_hum,
            adjusted_water_liters=adj_water,
            adjusted_fertilizer_price_factor=fert_price_factor,
            adjusted_market_price_factor=market_price_factor,
            crop_name=crop_name,
            yield_p10=yield_pred.p10_yield_t_per_ha,
            yield_p50=yield_pred.p50_yield_t_per_ha,
            yield_p90=yield_pred.p90_yield_t_per_ha,
            production_p10=yield_pred.farm_yield_p10_tonnes,
            production_p50=yield_pred.farm_yield_p50_tonnes,
            production_p90=yield_pred.farm_yield_p90_tonnes,
            revenue=None,  # Not calculated until Phase 6 economic models
            profit=None,   # Not calculated until Phase 6 economic models
            explanation=summary_explanation,
            details={"yield_prediction": yield_pred.model_dump()},
        )
    except Exception as exc:
        return ScenarioResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.scenario_name,
            category=scenario.category,
            status=ScenarioStatus.EVALUATION_ERROR,
            adjusted_rainfall_mm=adj_rain,
            adjusted_temperature_c=adj_temp,
            adjusted_humidity_percent=adj_hum,
            adjusted_water_liters=adj_water,
            adjusted_fertilizer_price_factor=fert_price_factor,
            adjusted_market_price_factor=market_price_factor,
            crop_name=crop_name,
            yield_p10=None,
            yield_p50=None,
            yield_p90=None,
            production_p10=None,
            production_p50=None,
            production_p90=None,
            revenue=None,
            profit=None,
            explanation=f"Error evaluating scenario: {str(exc)}",
            details={"error": str(exc)},
        )


def simulate_scenarios(
    profile: FarmProfile,
    scenarios: List[ScenarioDefinition],
    crop_name: Optional[str] = None,
) -> List[ScenarioResult]:
    """
    Evaluates a collection of scenarios against a farm profile.
    """
    return [simulate_scenario(profile, sc, crop_name=crop_name) for sc in scenarios]


# ==============================================================================
# SCENARIO COMPARISON & TABULAR EXPORT
# ==============================================================================

def compare_scenarios(results: List[ScenarioResult]) -> pd.DataFrame:
    """
    Generates a clean tabular comparison across evaluated scenarios.
    Explicitly reports condition changes and outcome statuses.
    """
    records = []
    for r in results:
        records.append({
            "Scenario ID": r.scenario_id,
            "Scenario Name": r.scenario_name,
            "Category": r.category.value if isinstance(r.category, ScenarioCategory) else str(r.category),
            "Rainfall (mm)": r.adjusted_rainfall_mm if r.adjusted_rainfall_mm is not None else "N/A",
            "Water (L)": f"{r.adjusted_water_liters:,.0f}" if r.adjusted_water_liters is not None else "N/A",
            "Temp (°C)": r.adjusted_temperature_c if r.adjusted_temperature_c is not None else "N/A",
            "Fert. Factor": f"{r.adjusted_fertilizer_price_factor:.2f}x",
            "Market Factor": f"{r.adjusted_market_price_factor:.2f}x",
            "Yield Outcome Status": r.status.value if isinstance(r.status, ScenarioStatus) else str(r.status),
            "Explanation": r.explanation,
        })
    return pd.DataFrame(records)
