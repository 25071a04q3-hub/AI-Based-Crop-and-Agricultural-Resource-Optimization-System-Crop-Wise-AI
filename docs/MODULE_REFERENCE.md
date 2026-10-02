# FarmTwin — Module Reference & API Specification

This document provides a comprehensive API reference and interface specification for all core modules within the **FarmTwin — Adaptive Farm Decision Engine** (`engine/`).

---

## 1. Farm Profile Engine (`engine/profile.py`)

### Overview
Validates and encapsulates all farm-level agronomic, meteorological, soil, and resource parameters into an immutable, type-enforced Pydantic data model. Normalizes land to hectares, water to liters, and currency to INR.

### Classes & Data Models

#### `LandUnit(str, Enum)`
- `HECTARE = "hectare"` (alias: `ha`, `hectares`)
- `ACRE = "acre"` (alias: `ac`, `acres`)

#### `WaterUnit(str, Enum)`
- `LITER = "liter"` (alias: `l`, `liters`, `litres`)
- `M3 = "m3"` (alias: `m^3`, `cubic_meter`, `cubic metres`)

#### `Season(str, Enum)`
- `KHARIF = "kharif"`
- `RABI = "rabi"`
- `ZAID = "zaid"`

#### `FarmProfile(BaseModel)`
The canonical validated farm data contract.

| Field | Type | Unit | Range / Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `farm_id` | `str` | - | Non-empty string | Unique parcel identifier. |
| `farmer_name` | `Optional[str]` | - | Optional string | Operator identification. |
| `state` | `Optional[str]` | - | Optional string | Operational state. |
| `district` | `Optional[str]` | - | Optional string | Operational district. |
| `latitude` | `Optional[float]` | ° | $-90.0 \le \text{lat} \le 90.0$ | GPS latitude. |
| `longitude` | `Optional[float]` | ° | $-180.0 \le \text{lon} \le 180.0$ | GPS longitude. |
| `land_area` | `float` | user unit | $> 0$ | Entered operational land area. |
| `land_unit` | `LandUnit` | - | `hectare` or `acre` | Unit of entered land area. |
| `land_area_ha` | `float` | ha | Computed | Normalized area ($1\text{ acre} \approx 0.404686\text{ ha}$). |
| `nitrogen_n_kg_ha` | `float` | kg/ha | $\ge 0$ | Available soil Nitrogen. |
| `phosphorus_p_kg_ha`| `float` | kg/ha | $\ge 0$ | Available soil Phosphorus. |
| `potassium_k_kg_ha` | `float` | kg/ha | $\ge 0$ | Available soil Potassium. |
| `ph` | `float` | pH | $0.0 \le \text{pH} \le 14.0$ | Soil acidity/alkalinity. |
| `temperature_c` | `float` | °C | $-20.0 \le T \le 60.0$ | Ambient temperature. |
| `humidity_percent` | `float` | % | $0.0 \le H \le 100.0$ | Relative atmospheric humidity. |
| `rainfall_mm` | `float` | mm | $\ge 0$ | Expected seasonal precipitation. |
| `available_water` | `float` | user unit | $\ge 0$ | Usable irrigation water. |
| `water_unit` | `WaterUnit` | - | `liter` or `m3` | Unit of entered water volume. |
| `water_liters` | `float` | Liters | Computed | Normalized water ($1\text{ m}^3 = 1,000\text{ L}$). |
| `available_n_kg` | `float` | kg | $\ge 0$ | Available Nitrogen fertilizer inventory. |
| `available_p_kg` | `float` | kg | $\ge 0$ | Available Phosphorus fertilizer inventory. |
| `available_k_kg` | `float` | kg | $\ge 0$ | Available Potassium fertilizer inventory. |
| `available_budget_inr`| `float` | INR (₹) | $\ge 0$ | Available seasonal working capital. |
| `available_labour_days`| `float` | days | $\ge 0$ | Total farm labour availability. |
| `season` | `Season` | - | Valid Enum | Target cropping season. |
| `year` | `int` | - | $2000 \le Y \le 2100$ | Planning calendar year. |
| `risk_tolerance` | `float` | - | $0.0 \le R \le 1.0$ | Risk preference parameter. |

### Core Functions
- `format_validation_errors(e: ValidationError) -> List[str]`: Converts Pydantic errors into farmer-friendly messages.
- `get_demo_farm_profile() -> FarmProfile`: Instantiates a synthetic reference farm profile (Telangana, 2 ha, Kharif).

---

## 2. Crop Suitability Engine (`engine/crop_suitability.py`)

### Overview
Evaluates the agronomic suitability of 22 candidate crops given soil chemistry (N, P, K, pH) and climatic factors (temperature, humidity, rainfall). Employs a scikit-learn `RandomForestClassifier` trained dynamically from `data/raw/crop_recommendation.csv` (2,200 rows, 22 balanced classes) and cached in-memory.

### Classes & Data Models

#### `CropSuitabilityResult(BaseModel)`
- `crop_name`: `str` — Canonical crop identifier (e.g., `rice`, `coffee`, `cotton`).
- `suitability_score`: `float` — Normalized probability $[0.0, 1.0]$.
- `suitability_level`: `str` — `Highly Suitable` ($\ge 0.80$), `Suitable` ($\ge 0.60$), `Moderately Suitable` ($\ge 0.40$), `Low Suitability` ($< 0.40$).
- `rank`: `int` — Ordinal ranking starting at 1.
- `model_probability`: `float` — Raw probability output from ensemble.
- `supporting_features`: `Dict[str, Any]` — Input soil and climate snapshot.
- `explanation`: `str` — Plain-language agronomic evaluation.

### Core Functions
- `train_suitability_model(df=None, random_state=42, test_size=0.2) -> Tuple[RandomForestClassifier, Dict[str, Any]]`: Trains Random Forest ($n=100$, $\text{max\_depth}=12$, stratified split).
- `get_or_train_suitability_model(force_retrain=False) -> Tuple[RandomForestClassifier, Dict[str, Any]]`: In-memory singleton loader (`_MODEL_CACHE`) preventing redundant retraining during execution.
- `predict_crop_suitability(profile: FarmProfile, model=None, top_n=None) -> List[CropSuitabilityResult]`: Computes suitability scores and ranks all 22 candidate crops.

---

## 3. Probabilistic Yield Engine (`engine/yield_prediction.py`)

### Overview
Defines the quantile-based yield forecasting interface ($P_{10}, P_{50}, P_{90}$). Enforces rigorous data honesty safeguards: because the repository lacks a validated historical micro-climate yield dataset, model training is **safely blocked** by design.

### Classes & Data Models

#### `YieldPredictionResult(BaseModel)`
- `crop_name`: `str` — Target crop identifier.
- `status`: `str` — `BLOCKED_NO_HISTORICAL_DATASET` (or `AVAILABLE` if valid dataset is supplied).
- `p10_yield_t_per_ha`: `Optional[float]` — 10th percentile yield lower bound ($\text{t/ha}$).
- `p50_yield_t_per_ha`: `Optional[float]` — Median expected yield ($\text{t/ha}$).
- `p90_yield_t_per_ha`: `Optional[float]` — 90th percentile yield upper bound ($\text{t/ha}$).
- `farm_yield_p10_tonnes`: `Optional[float]` — Total farm-level production lower bound.
- `farm_yield_p50_tonnes`: `Optional[float]` — Total farm-level production median.
- `farm_yield_p90_tonnes`: `Optional[float]` — Total farm-level production upper bound.
- `unit`: `str` — Standardized to `tonnes_per_hectare`.
- `message`: `str` — Status message explaining dataset gating.
- `methodology`: `str` — Technical description of the quantile regression architecture.

### Core Functions
- `audit_and_validate_yield_dataset(csv_path=None) -> Tuple[bool, Dict[str, Any]]`: Audits potential datasets against sample size ($\ge 200$), per-crop counts ($\ge 15$), and temporal columns (`year`).
- `predict_yield(profile: FarmProfile, crop_name: str) -> YieldPredictionResult`: Checks the Decision Gate and honestly returns blocked status with `None` yield values when uncalibrated.

---

## 4. Scenario Simulation Engine (`engine/scenario_simulator.py`)

### Overview
Implements deterministic agricultural stress-testing across 7 predefined environmental and macroeconomic shock futures, condition transformations, boundary clamps, and reproducible randomized scenario sweeps. Treated strictly as stress-test perturbations, NOT calibrated climate forecasts (`probability = None`).

### Classes & Data Models

#### `ScenarioCategory(str, Enum)`
- `NORMAL`, `WEATHER_STRESS`, `WATER_STRESS`, `INPUT_COST_STRESS`, `MARKET_STRESS`, `COMBINED_STRESS`

#### `ScenarioStatus(str, Enum)`
- `READY`, `BLOCKED_NO_YIELD_MODEL`, `INVALID_SCENARIO`, `EVALUATION_ERROR`

#### `ScenarioDefinition(BaseModel)`
- `scenario_id`: `str`
- `scenario_name`: `str`
- `rainfall_change_pct`: `float`
- `temperature_change_c`: `float`
- `humidity_change_pct`: `float`
- `water_change_pct`: `float`
- `fertilizer_price_change_pct`: `float`
- `market_price_change_pct`: `float`
- `probability`: `Optional[float] = None` (Null by contract)

#### `ScenarioResult(BaseModel)`
- `scenario_id`: `str`
- `scenario_name`: `str`
- `status`: `ScenarioStatus` (`BLOCKED_NO_YIELD_MODEL`)
- `adjusted_rainfall_mm`: `Optional[float]`
- `adjusted_temperature_c`: `Optional[float]`
- `adjusted_humidity_percent`: `Optional[float]`
- `adjusted_water_liters`: `Optional[float]`
- `explanation`: `str`

### Core Functions
- `get_predefined_scenarios() -> List[ScenarioDefinition]`: Returns the 7 standardized stress scenarios (Baseline, Drought, Excess Rainfall, Water Shortage, Fertilizer Price Shock, Market Price Shock, Combined Stress).
- `apply_scenario(profile: FarmProfile, scenario: ScenarioDefinition) -> Tuple[FarmProfile, Dict[str, Any]]`: Perturbs farm conditions with non-negativity clamps.
- `simulate_scenario(profile: FarmProfile, scenario: ScenarioDefinition, crop_name: Optional[str] = None) -> ScenarioResult`: Executes stress simulation and returns structured conditions.

---

## 5. Resource Calculation Engine (`engine/resource_calculator.py`)

### Overview
Calculates per-hectare and farm-level input consumption profiles (water, N, P, K, budget, labour) by querying verified agronomic crop norms in `config/crops_profile.json`. Compares crop demands directly against `FarmProfile` capacity limits.

### Classes & Data Models

#### `CropResourceProfile(BaseModel)`
- `crop_name`: `str`
- `water_per_ha_liters`: `float` ($1\text{ mm} = 10,000\text{ L/ha}$)
- `nitrogen_per_ha_kg`: `float`
- `phosphorus_per_ha_kg`: `float`
- `potassium_per_ha_kg`: `float`
- `cost_per_ha_inr`: `Optional[float]`
- `labour_days_per_ha`: `Optional[float]` (`None` / `DATA_UNAVAILABLE`)

#### `ResourceCalculationReport(BaseModel)`
- `total_land_ha`: `float`
- `total_water_liters`: `float`
- `total_n_kg`: `float`
- `total_p_kg`: `float`
- `total_k_kg`: `float`
- `total_cost_inr`: `Optional[float]`
- `is_feasible`: `bool`
- `surplus_deficit`: `Dict[str, float]`
- `utilization_pct`: `Dict[str, Optional[float]]`

### Core Functions
- `get_crop_resource_profile(crop_name: str) -> CropResourceProfile`: Loads crop-specific consumption rates.
- `calculate_portfolio_resources(crop_allocations_ha: Dict[str, float], farm_profile: FarmProfile) -> ResourceCalculationReport`: Computes multi-crop balance sheet against available farm resources.

---

## 6. Risk-Aware Farm Optimizer (`engine/optimizer.py`)

### Overview
Solves optimal continuous land allocation using the C++ SciPy HiGHS simplex solver (`scipy.optimize.linprog(method='highs')`). Operates in `RESOURCE_ONLY` mode, maximizing suitability-weighted productive area under simultaneous multi-resource constraints.

### Mathematical Formulation
$$\max_{\mathbf{x}} \sum_{i \in C} s_i \cdot x_i \quad \Longleftrightarrow \quad \min_{\mathbf{x}} \sum_{i \in C} (-s_i) \cdot x_i$$
$$\text{Subject to:}$$
$$\sum_{i \in C} x_i \le A_{\text{total}}, \quad \sum_{i \in C} w_i \cdot x_i \le W_{\text{avail}}, \quad \sum_{i \in C} b_i \cdot x_i \le B_{\text{avail}}$$
$$\sum_{i \in C} N_i \cdot x_i \le N_{\text{avail}}, \quad \sum_{i \in C} P_i \cdot x_i \le P_{\text{avail}}, \quad \sum_{i \in C} K_i \cdot x_i \le K_{\text{avail}}$$
$$0 \le x_i \le A_{\text{total}}, \quad \forall i \in C$$

### Classes & Data Models

#### `OptimizationMode(str, Enum)`
- `RESOURCE_ONLY` (active)
- `ECONOMIC_OPTIMIZATION` (blocked pending historical yield data)

#### `FarmOptimizationResult(BaseModel)`
- `status`: `str` (`OPTIMAL`, `INFEASIBLE`, `BLOCKED`)
- `optimization_mode`: `OptimizationMode`
- `crop_allocations_ha`: `Dict[str, float]` — Hectares allocated per crop ($x_i \ge 0$).
- `total_land_used_ha`: `float`
- `land_remaining_ha`: `float`
- `resource_usage`: `Dict[str, float]`
- `resource_remaining`: `Dict[str, float]`
- `resource_utilization_pct`: `Dict[str, Optional[float]]`
- `binding_resources`: `List[str]` ($\ge 99\%$ utilization)
- `feasibility`: `bool`
- `objective_value`: `Optional[float]`
- `expected_profit_inr`: `Optional[float] = None` (strictly null in `RESOURCE_ONLY`)
- `details`: `Dict[str, Any]` (stores HiGHS duals `ineqlin_marginals`)

### Core Functions
- `optimize_farm_allocation(farm_profile: FarmProfile, candidate_crops, top_n=5, mode=OptimizationMode.RESOURCE_ONLY) -> FarmOptimizationResult`: Sets up matrices and executes the HiGHS simplex solver.
- `optimize_across_scenarios(farm_profile: FarmProfile, candidate_crops, scenarios=None, top_n=5) -> Dict[str, FarmOptimizationResult]`: Optimizes allocations across multiple climate futures.

---

## 7. Portfolio Intelligence Engine (`engine/portfolio_intelligence.py`)

### Overview
Evaluates crop diversity using the deterministic Shannon Diversity Index ($H'$), tracks soil nutrient extraction pressure, honestly reports crop rotation metadata as `DATA_UNAVAILABLE`, and measures stress scenario resilience.

### Classes & Data Models

#### `PortfolioAnalysisResult(BaseModel)`
- `total_crops`: `int`
- `total_land_used_ha`: `float`
- `diversity_score`: `float` ($H'$)
- `diversity_status`: `str` (`LOW_DIVERSITY` $< 0.50$, `MODERATE_DIVERSITY` $0.50 - 1.00$, `HIGH_DIVERSITY` $\ge 1.00$)
- `resilience_score`: `Optional[float]`
- `resilience_status`: `str`
- `nutrient_pressure_status`: `str` (`LOW_PRESSURE`, `MODERATE_PRESSURE`, `HIGH_PRESSURE`)
- `rotation_status`: `str` (`DATA_UNAVAILABLE`)
- `warnings`: `List[str]`
- `explanation`: `str`

### Core Functions
- `analyze_portfolio_diversity(crop_allocations: Dict[str, float]) -> Tuple[float, str, str]`: Computes Shannon Diversity:
  $$H' = -\sum_{i=1}^k p_i \ln(p_i)$$
- `analyze_nutrient_pressure(resource_utilization_pct: Dict[str, Optional[float]]) -> Tuple[str, str, Dict[str, Optional[float]]]`: Classifies soil nutrient extraction.
- `analyze_rotation_compatibility(crop_names: List[str], config_dir=None) -> Tuple[str, str]`: Audits repository rotation matrix and safely reports `DATA_UNAVAILABLE`.
- `analyze_resilience(baseline_land_used_ha: float, scenario_results=None) -> Tuple[Optional[float], str, str]`: Computes worst-case cultivated area retention ratio.

---

## 8. Bottleneck Analysis Engine (`engine/bottleneck_analysis.py`)

### Overview
Extracts authentic mathematical dual variables ($\lambda_j$) from the HiGHS solver, classifies constraints into operational regimes, and runs $+10\% / +20\%$ What-If sensitivity sweeps.

### Classes & Data Models

#### `BottleneckAnalysisResult(BaseModel)`
- `primary_bottleneck`: `Optional[str]`
- `primary_bottleneck_utilization`: `Optional[float]`
- `secondary_bottlenecks`: `List[str]`
- `constraint_states`: `Dict[str, str]` (`UNDERUTILIZED` $<60\%$, `ACTIVE` $60-90\%$, `NEAR_BINDING` $90-99\%$, `BINDING` $\ge 99\%$)
- `shadow_value_status`: `str` (`SOLVER_DUALS_ACTIVE`)
- `shadow_values`: `Dict[str, Optional[float]]` (measured in suitability-weighted land / resource unit)
- `resource_lever_ranking`: `List[Dict[str, Any]]`
- `explanation`: `str`

### Core Functions
- `identify_primary_bottleneck(resource_utilization_pct: Dict[str, Optional[float]]) -> Tuple[Optional[str], Optional[float], str]`: Detects top restrictive constraint.
- `analyze_shadow_values(optimization_result: FarmOptimizationResult) -> Tuple[str, Dict[str, Optional[float]], str]`: Extracts HiGHS `ineqlin_marginals`.
- `run_resource_sensitivity_analysis(farm_profile: FarmProfile, candidate_crops, top_n=5, delta_pcts=[10.0, 20.0]) -> Dict[str, Dict[str, Any]]`: Re-executes the LP solver with relaxed capacities to measure empirical deltas.

---

## 9. Adaptive Reserve Engine (`engine/adaptive_reserve.py`)

### Overview
Audits contingency resource reserve margins, evaluates operational parameter shift triggers, calculates plan stability via Total Variation Distance (TVD), and simulates mid-season recourse shocks.

### Classes & Data Models

#### `ReoptimizationTriggerConfig(BaseModel)`
- `water_change_pct`: `float = 10.0`
- `budget_change_pct`: `float = 20.0`
- `fertilizer_change_pct`: `float = 15.0`
- `land_change_pct`: `float = 10.0`
- `scenario_change_enabled`: `bool = True`

#### `AdaptiveReserveResult(BaseModel)`
- `reserve_summary`: `Dict[str, Dict[str, float]]`
- `critical_reserves`: `Dict[str, str]` (`EXHAUSTED` $\le 1\%$, `CRITICAL` $<10\%$, `LOW` $<25\%$, `HEALTHY` $\ge 25\%$)
- `trigger_status`: `str` (`PLAN_STABLE` or `REOPTIMIZATION_REQUIRED`)
- `trigger_conditions`: `List[str]`
- `stability_score`: `Optional[float]`
- `stability_status`: `str` (`HIGH_STABILITY` $\ge 0.85$, `MODERATE_STABILITY` $0.60-0.85$, `LOW_STABILITY` $<0.60$)
- `adaptive_recommendations`: `List[str]`
- `explanation`: `str`

### Core Functions
- `analyze_resource_reserves(optimization_result: FarmOptimizationResult) -> Dict[str, Dict[str, float]]`: Calculates percentage safety margins.
- `evaluate_reoptimization_triggers(current_profile: FarmProfile, observed_conditions=None, active_scenario=None, config=None) -> Tuple[str, List[str]]`: Checks parameter divergence against thresholds.
- `analyze_plan_stability(baseline_result: FarmOptimizationResult, scenario_results=None) -> Tuple[Optional[float], str, str]`: Computes Total Variation Distance stability:
  $$\text{Shift} = \frac{\sum_{c} |x_{c,\text{scenario}} - x_{c,\text{base}}|}{2 \cdot A_{\text{base}}}, \quad \text{Stability} = 1.0 - \text{Shift}$$
- `simulate_resource_change(farm_profile: FarmProfile, candidate_crops, top_n=5, resource_changes_pct=None) -> Dict[str, Any]`: Re-runs the LP solver under hypothetical shocks to evaluate recourse feasibility.
