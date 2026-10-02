# FarmTwin — Adaptive Farm Decision Engine

[![Tests: Passing (172/172)](https://img.shields.io/badge/tests-172%20passed-brightgreen.svg)](#13-test-results)
[![Python: 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Streamlit: UI Operational](https://img.shields.io/badge/Streamlit-1.63.0-FF4B4B.svg)](https://streamlit.io/)
[![SciPy: HiGHS Simplex](https://img.shields.io/badge/solver-SciPy%20HiGHS-00599C.svg)](https://scipy.org/)

**FarmTwin** is an open-source, scientifically grounded agricultural decision support system designed to help farmers, agronomists, and agricultural researchers optimize crop selection and resource allocation under volatile climate conditions and resource constraints.

Unlike conventional crop recommendation tools that output single deterministic crop suggestions without considering farm land limits, water quotas, operational budgets, or soil sustainability, FarmTwin treats the farm as a dynamic, coupled agro-ecological system. It integrates machine learning suitability classification with continuous linear programming (LP), portfolio diversity analytics, dual-variable shadow pricing, and mid-season recourse buffers.

---

## 1. Project Title & Overview

### FarmTwin — Adaptive Farm Decision Engine
FarmTwin bridges the gap between machine learning predictions and actionable, constrained operational planning. 

Modern smallholder and commercial agriculture faces simultaneous pressures: erratic monsoon precipitation, declining groundwater tables, escalating fertilizer input costs, and market volatility. Single-crop recommendations often exacerbate these vulnerabilities by encouraging monoculture or demanding water volumes that exceed local borehole capacities.

FarmTwin solves this through an end-to-end 10-phase pipeline:
1. Validating strict physical farm boundaries (land holding, soil N-P-K, pH, climate forecasts, water volume, working capital).
2. Predicting crop suitability probabilities across 22 candidate crops using a Random Forest classifier.
3. Stress-testing crop viability across 7 environmental shock scenarios and Monte Carlo simulations.
4. Computing deterministic crop resource demands using agronomic field norms.
5. Optimizing land parceling via SciPy HiGHS simplex linear programming under concurrent land, water, budget, and nutrient influx constraints.
6. Quantifying crop portfolio diversity (Shannon Index $H'$) and soil nutrient balance.
7. Identifying binding resource bottlenecks and shadow values (dual variables $\lambda$) to reveal high-ROI investment levers.
8. Calculating adaptive safety reserves, mid-season shock triggers, and plan stability indices for dynamic farm management.

---

## 2. Key Features

- **Strict Schema Validation**: Immutable Pydantic-based `FarmProfile` enforcing agronomic unit consistency ($\text{ha}, \text{L}, \text{kg/ha}, \text{INR}$).
- **Multi-Crop Suitability AI**: Stratified Random Forest model outputting calibrated class probabilities and agronomic limiting factor diagnostics across 22 crops.
- **Future Scenario Stress Testing**: Deterministic perturbation simulator evaluating farm performance under Moderate Drought, Severe Drought, Heatwave, Excess Rainfall, Input Cost Spikes, and Water Cuts.
- **Resource Balance Sheet**: Deterministic vector-matrix engine evaluating per-crop and aggregate consumption of irrigation water, capital expenditure, and N-P-K nutrients.
- **Continuous LP Optimization**: SciPy HiGHS solver finding global optimal land parceling under simultaneous multi-resource constraints and monoculture risk bounds ($x_i \le 0.6 \cdot A_{\text{total}}$).
- **Portfolio & Rotation Intelligence**: Shannon Diversity Index calculation, soil nitrogen depletion/fixation diagnostics, and crop rotation advisories.
- **Bottleneck Analysis & Dual Pricing**: Automated categorization of resource regimes (Binding, Near-Binding, Active, Underutilized) and $+10\% / +20\%$ What-If sensitivity levers.
- **Adaptive Safety Buffers**: Dynamic reserve margin tracking, weather shock re-optimization triggers, and total variation plan stability scoring.
- **Scientific Honesty Safeguards**: Strict runtime gating preventing hallucinated crop yields, synthetic revenues, or uncalibrated currency shadow prices.

---

## 3. System Architecture

```text
                  +-----------------------------------------------+
                  |          Validated FarmProfile (Phase 2)      |
                  |  Land (ha), Soil (N,P,K,pH), Climate, Budget  |
                  +-----------------------------------------------+
                                          |
                                          v
                  +-----------------------------------------------+
                  |      AI Crop Suitability Engine (Phase 3)     |
                  |   Random Forest Classifier (22 Crop Models)   |
                  +-----------------------------------------------+
                         |                                 |
                         v                                 v
        +---------------------------------+  +-------------------------------+
        | Scenario Stress Engine (Phase 5)|  | Yield Safeguard Gate (Phase 4)|
        |  7 Climate Shocks + Monte Carlo |  |    [BLOCKED_NO_YIELD_MODEL]   |
        +---------------------------------+  +-------------------------------+
                         |                                 |
                         +----------------+----------------+
                                          |
                                          v
                  +-----------------------------------------------+
                  |     Resource Calculation Engine (Phase 6)     |
                  |      Per-Hectare Demands & Balance Sheet      |
                  +-----------------------------------------------+
                                          |
                                          v
                  +-----------------------------------------------+
                  |      Risk-Aware Farm Optimizer (Phase 7)      |
                  |   SciPy HiGHS Simplex LP (RESOURCE_ONLY Mode) |
                  +-----------------------------------------------+
                                          |
         +--------------------------------+-------------------------------+
         |                                |                               |
         v                                v                               v
+-----------------------+     +-----------------------+     +-----------------------+
| Portfolio & Soil      |     | Bottleneck & Shadow   |     | Adaptive Reserve &    |
| Intelligence (Phase 8)|     | Values (Phase 9)      |     | Mid-Season (Phase 10) |
| Shannon Diversity H'  |     | Binding Duals (lambda)|     | Safety Buffers        |
| Nutrient Depletion    |     | Sensitivity Levers    |     | Plan Stability Score  |
+-----------------------+     +-----------------------+     +-----------------------+
         |                                |                               |
         +--------------------------------+-------------------------------+
                                          |
                                          v
                  +-----------------------------------------------+
                  |    Interactive Streamlit Dashboard (ui/app.py)|
                  +-----------------------------------------------+
```

---

## 4. Technology Stack

- **Core Runtime**: Python 3.10 / 3.11 / 3.12 / 3.13 / 3.14
- **Data Validation & Schemas**: [Pydantic v2](https://docs.pydantic.dev/)
- **Machine Learning**: [scikit-learn](https://scikit-learn.org/) (Random Forest Ensemble)
- **Numerical & Optimization**: [SciPy](https://scipy.org/) (`scipy.optimize.linprog` with HiGHS simplex C++ engine), [NumPy](https://numpy.org/), [pandas](https://pandas.pydata.org/)
- **User Interface**: [Streamlit](https://streamlit.io/)
- **Test Suite**: [pytest](https://docs.pytest.org/) (172 automated unit & integration tests)

---

## 5. Installation

### Prerequisites
- Python 3.10+ installed
- Git

### Setup Instructions
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/farmtwin.git
   cd farmtwin
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   # On macOS/Linux:
   python3 -m venv venv
   source venv/bin/activate

   # On Windows (PowerShell):
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify Installation**:
   ```bash
   python -m pytest -q
   # Expected output: 172 passed
   ```

---

## 6. Usage

### Running the Dashboard
Launch the interactive web application locally:
```bash
streamlit run ui/app.py
```
Open your browser to `http://localhost:8501`.

### Programmatic Python API
You can also use FarmTwin as a pure Python library in automated workflows or research scripts:

```python
from engine.profile import FarmProfile, SoilType, Season, IrrigationSource
from engine.crop_suitability import CropSuitabilityEngine
from engine.optimizer import FarmOptimizer
from engine.portfolio_intelligence import PortfolioIntelligenceEngine
from engine.bottleneck_analysis import BottleneckAnalysisEngine
from engine.adaptive_reserve import AdaptiveReserveEngine

# 1. Define validated farm profile
profile = FarmProfile(
    land_acres=10.0,
    soil_type=SoilType.BLACK,
    soil_ph=7.2,
    nitrogen_kg_per_ha=120.0,
    phosphorus_kg_per_ha=45.0,
    potassium_kg_per_ha=60.0,
    annual_rainfall_mm=850.0,
    temperature_c=28.5,
    humidity_pct=65.0,
    water_availability_liters=25_000_000.0,
    budget_inr=350_000.0,
    irrigation_source=IrrigationSource.BOREWELL,
    season=Season.KHARIF
)

# 2. Predict crop suitability
suitability_engine = CropSuitabilityEngine()
suitable_crops = suitability_engine.get_top_suitable_crops(profile, top_n=5)

# 3. Solve optimal farm allocation
optimizer = FarmOptimizer()
opt_result = optimizer.optimize(profile, suitable_crops, max_crop_fraction=0.6)

# 4. Generate post-optimization decision intelligence
portfolio_engine = PortfolioIntelligenceEngine()
portfolio_metrics = portfolio_engine.analyze_portfolio(opt_result, profile)

bottleneck_engine = BottleneckAnalysisEngine()
bottlenecks = bottleneck_engine.analyze_bottlenecks(opt_result, profile)

reserve_engine = AdaptiveReserveEngine()
reserves = reserve_engine.evaluate_reserves(opt_result, profile)

print(f"Optimal Allocation Feasible: {opt_result.is_feasible}")
print(f"Shannon Diversity Index: {portfolio_metrics.shannon_diversity_index:.2f}")
print(f"Primary Bottleneck: {bottlenecks.primary_bottleneck}")
print(f"Plan Stability Index: {reserves.plan_stability_score * 100:.1f}%")
```

---

## 7. Dashboard Walkthrough & Screens

The FarmTwin Streamlit dashboard is organized into an intuitive sequential, reactive single-page workflow:

1. **Top Bar**: Fast demo profile loader (`📥 Load Demo Profile (FARM-001)`) with reference farm telemetry (Telangana, 2 ha, Kharif).
2. **Farm Profile Input Form**: Comprehensive on-page inputs for holding size (ha/acre), soil chemistry (N-P-K, pH), seasonal weather forecasts (temp, humidity, rainfall), irrigation water (liters/m³), fertilizer inventories, budget, labour, and risk preferences.
3. **Farm Profile Summary Card**: Validated parameters and JSON normalized units contract.
4. **Phase 3 Card (AI Crop Suitability)**: Ranked suitability bar charts with probability scores, confidence levels, and detailed agronomic limiting factors.
5. **Phase 4 Card (Probabilistic Yield)**: Scientific gating banner (`BLOCKED_NO_HISTORICAL_DATASET`) explaining yield model status.
6. **Phase 5 Card (Scenario Simulator)**: Stress-test evaluation across 7 climate and macroeconomic futures.
7. **Phase 6 Card (Resource Calculation)**: Input consumption breakdown and multi-resource balance sheet.
8. **Phase 7 Card (Resource Optimization)**: Optimal land parceling table, resource utilization metrics, and HiGHS simplex solver diagnostics.
9. **Phase 8 Card (Portfolio & Soil Health)**: Shannon Diversity Index ($H'$), soil nutrient pressure rating, and crop rotation audit.
10. **Phase 9 Card (Bottlenecks & Shadow Values)**: Binding constraint detection, HiGHS dual variables, and What-If $+10\% / +20\%$ sensitivity levers.
11. **Phase 10 Card (Adaptive Reserves & Recourse)**: Buffer safety gauges, mid-season re-optimization triggers, and Total Variation Distance plan stability metrics.

---

## 8. Mathematical Formulation of the Optimization Engine

FarmTwin formulates farm resource allocation as a continuous Linear Program (LP) solved via the SciPy HiGHS simplex solver:

$$\max_{\mathbf{x}} Z = \sum_{i \in C} s_i \cdot x_i$$

**Subject to:**
1. **Land Area Limit**: $\sum_{i \in C} x_i \le A_{\text{total}}$
2. **Irrigation Water Capacity**: $\sum_{i \in C} w_i \cdot x_i \le W_{\text{avail}}$
3. **Working Capital Budget**: $\sum_{i \in C} b_i \cdot x_i \le B_{\text{avail}}$
4. **Nutrient Influx Bounds**:
   - Nitrogen: $\sum_{i \in C} N_i \cdot x_i \le \bar{N} \cdot A_{\text{total}}$
   - Phosphorus: $\sum_{i \in C} P_i \cdot x_i \le \bar{P} \cdot A_{\text{total}}$
   - Potassium: $\sum_{i \in C} K_i \cdot x_i \le \bar{K} \cdot A_{\text{total}}$
5. **Monoculture Risk Ceiling**: $x_i \le f_{\max} \cdot A_{\text{total}} \quad (\forall i \in C, \text{ default } f_{\max} = 0.60)$
6. **Non-negativity**: $x_i \ge 0 \quad (\forall i \in C)$

Where $x_i$ is hectares allocated to crop $i$, $s_i$ is the AI suitability probability, $w_i$ is water demand per ha, $b_i$ is production cost per ha, and $N_i, P_i, K_i$ are nutrient uptake rates.

---

## 9. Decision Intelligence Modules

### Portfolio Intelligence (Phase 8)
- **Shannon Diversity Index ($H'$)**: $H' = -\sum_{i=1}^k p_i \ln(p_i)$. Evaluates whether the farm plan is overly concentrated in a single crop or ecologically diversified against pests and market collapse.
- **Soil Balance Ratios**: Identifies whether the crop mix exhausts soil nitrogen reserves or replenishes fertility via leguminous nitrogen fixation.

### Bottleneck Intelligence & Shadow Pricing (Phase 9)
- **Dual Variables ($\lambda_j = \frac{\partial Z^*}{\partial b_j}$)**: Extracts exact mathematical shadow prices from the HiGHS solver. Represents the marginal increase in suitability-weighted land usage achieved by expanding a binding resource by one unit.
- **Sensitivity Sweeps**: Automates $+10\%$ and $+20\%$ capacity relaxations to rank resources by their productive impact.

### Adaptive Reserve Intelligence (Phase 10)
- **Safety Buffers**: Tracks unallocated reserves across water and capital.
- **Recourse Plan Stability**: Evaluates how much of the original farm plan remains feasible when mid-season environmental shocks occur:
  $$\text{Stability} = 1.0 - \frac{1}{2} \sum_{i \in C} \left| p_i^{(0)} - p_i^{(1)} \right|$$

---

## 10. Scientific Honesty & Data Integrity

FarmTwin adheres strictly to academic and scientific honesty principles:

1. **No Fake Yields**: The repository does not fabricate historical crop yields. The quantile yield engine is safely gated (`BLOCKED_NO_YIELD_MODEL`) pending empirical micro-climate datasets.
2. **No Hallucinated Profits or Prices**: The optimizer operates in `RESOURCE_ONLY` mode, maximizing suitability-weighted land productivity rather than presenting unverified INR revenues.
3. **No Fabricated Shadow Prices**: Dual variables are expressed in authentic mathematical objective units ($\Delta \text{weighted ha} / \Delta \text{resource}$), not fictitious monetary values.
4. **No Fabricated Climate Probabilities**: Scenario simulations use explicit physical and cost perturbations rather than speculative probability distributions.

---

## 11. Test Results & Verification

FarmTwin maintains a complete automated test suite ensuring end-to-end reliability:

```bash
$ python -m pytest -q
....................................................................................
....................................................................................
172 passed in 18.50s
```

### Coverage by Component
- **Farm Profile (`tests/test_profile.py`)**: 16 tests passing
- **Crop Suitability (`tests/test_crop_suitability.py`)**: 18 tests passing
- **Yield Model Gating (`tests/test_yield_prediction.py`)**: 12 tests passing
- **Scenario Simulator (`tests/test_scenario_simulator.py`)**: 16 tests passing
- **Resource Calculator (`tests/test_resource_calculator.py`)**: 15 tests passing
- **HiGHS Optimizer (`tests/test_optimizer.py`)**: 22 tests passing
- **Portfolio Intelligence (`tests/test_portfolio_intelligence.py`)**: 18 tests passing
- **Bottleneck Analysis (`tests/test_bottleneck_analysis.py`)**: 24 tests passing
- **Adaptive Reserves (`tests/test_adaptive_reserve.py`)**: 20 tests passing
- **End-to-End Pipeline (`tests/test_pipeline_integration.py`)**: 11 tests passing

---

## 12. Project Documentation

Comprehensive technical documentation is available in the `docs/` directory:
- [**Project Architecture Specification**](docs/PROJECT_ARCHITECTURE.md): Complete system architectural breakdown.
- [**Module Reference & API Specification**](docs/MODULE_REFERENCE.md): Class, method, and schema reference.
- [**User & Operator Guide**](docs/USER_GUIDE.md): Operational guide for dashboard navigation and result interpretation.
- [**Technical & Mathematical Guide**](docs/TECHNICAL_GUIDE.md): Mathematical formulations, solver mechanics, and complexity analysis.
- [**Testing & Verification Guide**](docs/TESTING_GUIDE.md): Test suite structure, fixtures, and verification guidelines.
- [**Architecture Diagrams**](docs/architecture/):
  - [System Architecture](docs/architecture/system_architecture.md)
  - [Data Flow Diagram](docs/architecture/data_flow.md)
  - [Optimization Pipeline](docs/architecture/optimization_pipeline.md)
  - [Decision Intelligence Pipeline](docs/architecture/decision_intelligence_pipeline.md)
  - [Module Dependencies](docs/architecture/module_dependencies.md)
  - [Folder Structure](docs/architecture/folder_structure.md)

---

## 13. Limitations

1. **Gated Yield Forecasting**: Full economic profit optimization is temporarily inactive because calibrated historical yield datasets are not yet integrated into the repository.
2. **Static Crop Norms**: Crop water and nutrient requirements in `config/crops_profile.json` reflect regional baseline averages; micro-climatic variations may require local agronomic calibration.
3. **Continuous Land Allocation**: The LP solver assumes continuous land allocation ($x_i \in \mathbb{R}^+$). Real-world equipment may require minimum discrete parcel sizes (which would require Mixed-Integer Linear Programming / MILP).
4. **Independent Annual Cycles**: Multi-year soil organic matter dynamics and pest-host cycle modeling require multi-season historical field tracking.

---

## 14. Future Work

1. **Integration of Calibrated Historical Yield Datasets**: Train and validate Quantile Gradient Boosting regressors on localized district-level yield statistics.
2. **Economic Risk Optimization**: Activate Conditional Value-at-Risk (CVaR) revenue maximization once authentic yield and mandi spot price feeds are integrated.
3. **Mixed-Integer Parceling**: Implement discrete parcel size constraints using MILP branch-and-bound solvers.
4. **Multilingual Voice & SMS Interface**: Provide localized language synthesis (Hindi, Telugu, Tamil, Marathi) for smallholder farmers.

---

## 15. License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for complete terms.
