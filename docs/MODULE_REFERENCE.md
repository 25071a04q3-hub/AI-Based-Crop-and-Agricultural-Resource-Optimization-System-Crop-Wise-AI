# FarmTwin — Module Reference & API Specification

This document provides a comprehensive API reference and interface specification for all core modules within the **FarmTwin — Adaptive Farm Decision Engine** (`engine/`).

---

## 1. Farm Profile Engine (`engine/profile.py`)

### Overview
Validates and encapsulates all farm-level agronomic, meteorological, soil, and resource parameters into an immutable, type-enforced Pydantic data model.

### Classes & Data Models

#### `SoilType(str, Enum)`
Enumeration of supported soil classifications:
- `CLAY`, `SANDY`, `LOAMY`, `BLACK`, `RED`, `ALLUVIAL`

#### `Season(str, Enum)`
Agricultural cropping seasons in India:
- `KHARIF` (Monsoon / Autumn)
- `RABI` (Winter / Spring)
- `ZAID` (Summer)

#### `IrrigationSource(str, Enum)`
Primary farm water access infrastructure:
- `CANAL`, `BOREWELL`, `DRIP`, `SPRINKLER`, `RAINFED`

#### `FarmProfile(BaseModel)`
The canonical validated farm data schema.

| Field | Type | Unit | Range / Constraints | Description |
| :--- | :--- | :--- | :--- | :--- |
| `land_acres` | `float` | acres | $> 0, \le 10,000$ | Total cultivated holding size in acres. |
| `land_hectares` | `float` | ha | Computed property | $1\text{ acre} \approx 0.404686\text{ ha}$. |
| `soil_type` | `SoilType` | - | Valid Enum | Soil texture and type. |
| `soil_ph` | `float` | pH | $3.5 \le \text{pH} \le 10.0$ | Soil acidity/alkalinity measure. |
| `nitrogen_kg_per_ha` | `float` | kg/ha | $\ge 0, \le 500$ | Available soil nitrogen concentration. |
| `phosphorus_kg_per_ha` | `float` | kg/ha | $\ge 0, \le 300$ | Available soil phosphorus concentration. |
| `potassium_kg_per_ha` | `float` | kg/ha | $\ge 0, \le 500$ | Available soil potassium concentration. |
| `annual_rainfall_mm` | `float` | mm | $\ge 0, \le 5,000$ | Expected annual precipitation. |
| `temperature_c` | `float` | °C | $-10.0 \le T \le 55.0$ | Mean ambient temperature during season. |
| `humidity_pct` | `float` | % | $0.0 \le H \le 100.0$ | Relative atmospheric humidity. |
| `water_availability_liters`| `float` | Liters | $\ge 0$ | Total seasonal irrigation capacity. |
| `budget_inr` | `float` | INR (₹) | $\ge 0$ | Total seasonal working capital. |
| `irrigation_source` | `IrrigationSource` | - | Valid Enum | Irrigation delivery mechanism. |
| `season` | `Season` | - | Valid Enum | Target cultivation season. |

---

## 2. Crop Suitability Engine (`engine/crop_suitability.py`)

### Overview
Evaluates the agronomic suitability of 22 candidate crops given soil chemistry (N, P, K, pH) and climatic factors (temperature, humidity, rainfall) using a pre-trained scikit-learn `RandomForestClassifier`.

### Classes & Data Models

#### `CropSuitabilityResult(BaseModel)`
- `crop_name`: `str` — Name of the crop (e.g., `rice`, `maize`, `cotton`).
- `suitability_score`: `float` — Normalized probability $[0.0, 1.0]$.
- `is_suitable`: `bool` — Threshold flag ($\ge 0.15$ suitability).
- `limiting_factors`: `List[str]` — Agronomic mismatches (e.g., `"Rainfall deficient for optimal growth"`).

#### `CropSuitabilityEngine`
- `__init__(model_path: Optional[str] = None)`: Initializes the classifier from `models/crop_suitability_rf.joblib` or trains a fallback on `data/Crop_recommendation.csv`.
- `predict_suitability(profile: FarmProfile) -> List[CropSuitabilityResult]`: Computes class probabilities across all 22 crops, sorts by descending probability score, and generates explanatory diagnostics.
- `get_top_suitable_crops(profile: FarmProfile, top_n: int = 5) -> List[CropSuitabilityResult]`: Returns the top $N$ viable candidate crops.

---

## 3. Probabilistic Yield Engine (`engine/yield_prediction.py`)

### Overview
Defines the quantile-based yield forecasting interface ($P_{10}, P_{50}, P_{90}$). Enforces rigorous data honesty safeguards when historical empirical yield datasets are absent.

### Classes & Data Models

#### `YieldPredictionStatus(str, Enum)`
- `BLOCKED_NO_YIELD_MODEL`: Explicit marker indicating historical production data is absent; synthetic fabrication is strictly prohibited.
- `TRAINED_AND_AVAILABLE`: Operational quantile GBDT model ready for inference.

#### `ProbabilisticYieldEstimate(BaseModel)`
- `crop_name`: `str`
- `status`: `YieldPredictionStatus`
- `p10_yield_tonnes_per_ha`: `Optional[float]` — Conservative 10th percentile yield.
- `p50_yield_tonnes_per_ha`: `Optional[float]` — Median expected yield.
- `p90_yield_tonnes_per_ha`: `Optional[float]` — Optimistic 90th percentile yield.
- `uncertainty_iqr`: `Optional[float]` — Spread ($P_{90} - P_{10}$).
- `warning_message`: `Optional[str]` — Explanation of model availability.

#### `ProbabilisticYieldEngine`
- `predict_yield(crop_name: str, profile: FarmProfile) -> ProbabilisticYieldEstimate`: Checks model availability. If no authentic dataset is registered, returns a safe status with explicit disclaimers rather than hallucinated yield numbers.

---

## 4. Scenario Simulation Engine (`engine/scenario_simulator.py`)

### Overview
Executes environmental stress tests against the farm profile across 7 baseline stress futures and Monte Carlo stochastic runs.

### Classes & Data Models

#### `StressScenarioType(str, Enum)`
- `BASELINE`: Historical average conditions.
- `DROUGHT_MODERATE`: $-25\%$ rainfall, $+1.5^\circ\text{C}$ temperature.
- `DROUGHT_SEVERE`: $-50\%$ rainfall, $+3.0^\circ\text{C}$ temperature, $-30\%$ water storage.
- `HEATWAVE`: $+4.0^\circ\text{C}$ temperature, $-15\%$ humidity.
- `EXCESS_RAINFALL`: $+40\%$ rainfall, $+10\%$ humidity.
- `INPUT_COST_SPIKE`: $+20\%$ fertilizer costs, $+15\%$ operational budget pressure.
- `WATER_CUT`: $-40\%$ canal/groundwater irrigation availability.

#### `SimulatedScenario(BaseModel)`
- `scenario_id`: `str`
- `scenario_type`: `StressScenarioType`
- `perturbed_profile`: `FarmProfile`
- `suitability_results`: `List[CropSuitabilityResult]`
- `impact_summary`: `Dict[str, Any]`

#### `ScenarioSimulator`
- `run_stress_scenarios(base_profile: FarmProfile, scenarios: Optional[List[StressScenarioType]] = None) -> List[SimulatedScenario]`: Simulates specific environmental shocks and calculates crop resilience shifts.
- `run_monte_carlo(base_profile: FarmProfile, n_simulations: int = 100) -> Dict[str, Any]`: Computes distribution parameters across normal perturbations.

---

## 5. Resource Calculation Engine (`engine/resource_calculator.py`)

### Overview
Evaluates crop-specific per-hectare requirements against farm inventory using agronomic crop norms (`config/crops_profile.json`).

### Classes & Data Models

#### `CropResourceRequirement(BaseModel)`
- `crop_name`: `str`
- `water_liters_per_ha`: `float`
- `nitrogen_kg_per_ha`: `float`
- `phosphorus_kg_per_ha`: `float`
- `potassium_kg_per_ha`: `float`
- `cost_inr_per_ha`: `float`

#### `ResourceDemandSheet(BaseModel)`
- `crop_demands`: `Dict[str, CropResourceRequirement]`
- `total_water_liters_requested`: `float`
- `total_budget_inr_requested`: `float`
- `is_within_profile_limits`: `bool`

#### `ResourceCalculator`
- `get_crop_requirements(crop_name: str) -> CropResourceRequirement`: Queries crop profile norms.
- `calculate_allocation_demands(allocations_ha: Dict[str, float]) -> ResourceDemandSheet`: Computes aggregate resource demands for a given allocation plan.

---

## 6. Risk-Aware Farm Optimizer (`engine/optimizer.py`)

### Overview
Continuous Linear Programming (LP) engine solved via SciPy `scipy.optimize.linprog(method='highs')`. Solves optimal land parceling under land, water, budget, and nutrient capacity constraints.

### Mathematical Formulation
$$\max_{\mathbf{x}} \sum_{i \in C} s_i \cdot x_i$$
$$\text{Subject to:}$$
$$\sum_{i \in C} x_i \le A_{\text{total}} \quad (\text{Total Land Area})$$
$$\sum_{i \in C} w_i \cdot x_i \le W_{\text{avail}} \quad (\text{Seasonal Water Capacity})$$
$$\sum_{i \in C} b_i \cdot x_i \le B_{\text{avail}} \quad (\text{Working Capital Budget})$$
$$\sum_{i \in C} N_i \cdot x_i \le \bar{N} \cdot A_{\text{total}} \quad (\text{Nitrogen Influx Limit})$$
$$\sum_{i \in C} P_i \cdot x_i \le \bar{P} \cdot A_{\text{total}} \quad (\text{Phosphorus Influx Limit})$$
$$\sum_{i \in C} K_i \cdot x_i \le \bar{K} \cdot A_{\text{total}} \quad (\text{Potassium Influx Limit})$$
$$0 \le x_i \le A_{\text{total}} \cdot f_{\max}, \quad \forall i \in C \quad (\text{Crop Monoculture Limit})$$

### Classes & Data Models

#### `OptimizationMode(str, Enum)`
- `RESOURCE_ONLY`: Maximizes agronomic suitability-weighted land usage under physical constraints (active mode).
- `ECONOMIC_RISK`: Yield/revenue optimization (safely disabled pending authentic yield data).

#### `CropAllocation(BaseModel)`
- `crop_name`: `str`
- `allocated_hectares`: `float`
- `allocated_acres`: `float`
- `land_share_pct`: `float`
- `suitability_score`: `float`

#### `OptimizationResult(BaseModel)`
- `is_feasible`: `bool`
- `solver_status`: `str`
- `optimization_mode`: `OptimizationMode`
- `objective_value`: `float`
- `allocations`: `List[CropAllocation]`
- `unallocated_hectares`: `float`
- `resource_utilization`: `Dict[str, Dict[str, float]]`
- `binding_constraints`: `List[str]`
- `dual_values`: `Dict[str, float]`
- `warning_messages`: `List[str]`

#### `FarmOptimizer`
- `optimize(profile: FarmProfile, candidate_crops: List[CropSuitabilityResult], max_crop_fraction: float = 0.6) -> OptimizationResult`: Sets up and executes the SciPy HiGHS simplex solver.

---

## 7. Portfolio Intelligence Engine (`engine/portfolio_intelligence.py`)

### Overview
Analyzes agronomic diversification, nutrient stress indicators, and crop rotation validity.

### Key Metrics
1. **Shannon Diversity Index ($H'$)**:
   $$H' = -\sum_{i=1}^k p_i \ln(p_i)$$
   Where $p_i = \frac{x_i}{\sum x_j}$. Measures biodiversity and crop dispersion.
2. **Resilience Ratio**:
   $$\text{Resilience} = \frac{\sum_{i} x_i \cdot s_i}{\sum_{i} x_i}$$
3. **Soil Balance Indicators**: Net nitrogen balance categorized as Depleting, Balanced, or Replenishing (via leguminous fixation).

### Classes & Data Models

#### `PortfolioMetrics(BaseModel)`
- `shannon_diversity_index`: `float`
- `crop_count`: `int`
- `resilience_ratio`: `float`
- `soil_nitrogen_pressure`: `str`
- `rotation_advisory`: `Dict[str, Any]`

#### `PortfolioIntelligenceEngine`
- `analyze_portfolio(optimization_result: OptimizationResult, profile: FarmProfile) -> PortfolioMetrics`: Produces comprehensive portfolio diagnostics.

---

## 8. Bottleneck Analysis Engine (`engine/bottleneck_analysis.py`)

### Overview
Extracts and translates HiGHS mathematical dual variables ($\lambda_j$) and constraint slacks into farmer-accessible sensitivity insights.

### Constraint Regimes
- **Binding** ($100\%$ utilization, positive dual variable $\lambda_j > 0$): Critical system bottleneck.
- **Near-Binding** ($90\% \le \text{utilization} < 100\%$): Approaching capacity limit.
- **Active** ($50\% \le \text{utilization} < 90\%$): Healthy operational headroom.
- **Underutilized** ($< 50\%$ utilization): Abundant slack resource.

### Classes & Data Models

#### `BottleneckReport(BaseModel)`
- `primary_bottleneck`: `Optional[str]`
- `binding_resources`: `List[str]`
- `resource_regimes`: `Dict[str, str]`
- `dual_values`: `Dict[str, float]`
- `sensitivity_levers`: `List[Dict[str, Any]]`
- `plain_language_advice`: `List[str]`

#### `BottleneckAnalysisEngine`
- `analyze_bottlenecks(optimization_result: OptimizationResult, profile: FarmProfile) -> BottleneckReport`: Performs shadow pricing extraction and What-If relaxation sweeps ($+10\%, +20\%$).

---

## 9. Adaptive Reserve Engine (`engine/adaptive_reserve.py`)

### Overview
Computes unallocated resource buffers, defines mid-season re-optimization triggers, and evaluates plan stability under unexpected shocks.

### Key Capabilities
1. **Reserve Margins**:
   - $\text{Reserve \%} = 100\% - \text{Utilization \%}$
   - Classified as: `EXHAUSTED` ($0\%$), `CRITICAL` ($<5\%$), `LOW` ($5-15\%$), `HEALTHY` ($\ge 15\%$).
2. **Re-optimization Triggers**:
   - Flags an advisory if seasonal rainfall deviates $>25\%$, budget deviates $>15\%$, or water drops below planned allocation.
3. **Plan Stability Metric**:
   $$\text{Stability} = 1.0 - \frac{1}{2} \sum_{i} \left| p_i^{\text{original}} - p_i^{\text{perturbed}} \right|$$
   Bounded in $[0.0, 1.0]$, measuring the fraction of land that remains undisturbed after shock recourse.

### Classes & Data Models

#### `AdaptiveReserveReport(BaseModel)`
- `reserve_margins`: `Dict[str, float]`
- `reserve_health`: `Dict[str, str]`
- `reoptimization_triggered`: `bool`
- `trigger_reasons`: `List[str]`
- `plan_stability_score`: `float`
- `guidance_notes`: `List[str]`

#### `AdaptiveReserveEngine`
- `evaluate_reserves(optimization_result: OptimizationResult, profile: FarmProfile) -> AdaptiveReserveReport`: Evaluates safety buffers and dynamic mid-season re-optimization triggers.
