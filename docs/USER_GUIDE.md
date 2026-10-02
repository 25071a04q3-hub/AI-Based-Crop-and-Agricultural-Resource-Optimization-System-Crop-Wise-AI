# FarmTwin — User & Operator Guide

Welcome to the **FarmTwin — Adaptive Farm Decision Engine** operational guide. This handbook explains how to configure farm profiles, interpret AI suitability rankings, evaluate resource-constrained optimal farm plans, and apply decision intelligence insights in practice.

---

## 1. Quick Start

### Launching the Dashboard
Ensure your Python environment is activated and dependencies are installed:
```bash
streamlit run ui/app.py
```
Open your browser to `http://localhost:8501`.

---

## 2. Navigating the Interface

The application is structured as a **single, reactive scrollable dashboard**:
1. **Top Control Bar**: Includes the `📥 Load Demo Profile (FARM-001)` button to quickly populate representative farm telemetry (Telangana, 2 ha, Kharif).
2. **Farm Profile Input Form**: Complete input sections directly on the page covering:
   - **Farm Identity & Location**: Farm ID, Farmer Name, State, District, Latitude, Longitude.
   - **Operational Land**: Land Area and Unit selector (`hectare` or `acre`).
   - **Soil Chemistry**: Available Nitrogen (N), Phosphorus (P), Potassium (K) in kg/ha, and soil pH ($0.0 - 14.0$).
   - **Weather / Observed Climate**: Ambient temperature (°C), relative humidity (%), and expected seasonal rainfall (mm).
   - **Water & Fertilizer Resources**: Irrigation water volume and unit (`liter` or `m3`), plus available N, P, K fertilizer inventories in kg.
   - **Economics, Labour & Strategy**: Working capital budget (₹ INR), available labour (person-days), cropping season (Kharif, Rabi, Zaid), planning year, and a risk preference slider ($0.0 - 1.0$).
3. **Sequential Phase Cards**: Upon validating the profile and clicking `🔮 Analyze Crop Suitability`, the analytical pipeline renders sequentially down the page:
   - **Farm Profile Summary**: Validated parameters and normalized units contract.
   - **Phase 3: AI Crop Suitability Analysis**: Bar charts of top suitable crops and limiting factors.
   - **Phase 4: Probabilistic Crop Yield Prediction**: Gated quantile yield distribution status and diagnostic disclaimers.
   - **Phase 5: Future Scenario Simulator & Farm Stress Testing**: Interactive climate and macroeconomic shock testing across 7 futures.
   - **Phase 6: Resource Requirement & Balance Engine**: Per-hectare input consumption breakdown and multi-resource balance sheet.
   - **Phase 7: Risk-Aware Farm Optimization Engine**: Optimal land parceling table, feasibility indicators, and capacity utilization.
   - **Phase 8: Crop Portfolio & Soil Rotation Intelligence**: Shannon Diversity Index ($H'$), soil nutrient pressure rating, and crop rotation audit.
   - **Phase 9: Bottleneck Analysis & Shadow Value Intelligence**: Constraint regime classification, HiGHS dual variables, and What-If $+10\% / +20\%$ sensitivity levers.
   - **Phase 10: Adaptive Reserve & Mid-Season Re-Optimization**: Contingency buffer margin gauges, parameter shift trigger alerts, and Total Variation Distance plan stability metrics.

---

## 3. Step-by-Step Workflow

### Step 1: Input & Validate Farm Profile
1. Enter your farm dimensions, soil laboratory test results, weather forecasts, and available resource inventories.
2. Click **"✅ Validate & Save Farm Profile"**. If any parameter violates physical bounds, clean validation messages pinpoint the required correction.

### Step 2: Review Crop Suitability AI
1. Click **"🔮 Analyze Crop Suitability"**.
2. The Random Forest model predicts probabilities across 22 crops, displaying ranked bars and prototype tiers (`Highly Suitable`, `Suitable`, `Moderately Suitable`, `Low Suitability`).
3. For suboptimal crops, inspect the **Limiting Factors** explaining specific soil or climate mismatches.

### Step 3: Run Resource Optimization
1. In the **Phase 7: Risk-Aware Farm Optimization Engine** card, select the optimization mode (defaults to `RESOURCE_ONLY`).
2. The SciPy HiGHS simplex solver computes optimal land parcel allocations ($x_i \ge 0$) respecting land, water, budget, and nutrient capacity limits.
3. Review the allocation summary table detailing hectares, acres, percentage land share, and resource consumption.

### Step 4: Inspect Decision Intelligence Cards
1. **Portfolio Diversity & Soil Health (Phase 8)**:
   - Evaluates the Shannon Diversity Index ($H' = -\sum p_i \ln p_i$).
   - Flags soil nutrient pressure as `LOW_PRESSURE`, `MODERATE_PRESSURE`, or `HIGH_PRESSURE`.
   - Reports crop rotation metadata as `DATA_UNAVAILABLE` to maintain complete scientific honesty.
2. **Bottlenecks & Shadow Values (Phase 9)**:
   - Identifies which resource forms the primary binding bottleneck ($\ge 99\%$ utilization).
   - Displays authentic HiGHS dual multipliers ($\lambda_j$) in suitability-weighted land gain per resource unit.
   - Evaluates What-If sensitivity levers showing land gains from $+10\%$ or $+20\%$ capacity relaxations.
3. **Adaptive Reserves & Mid-Season Recourse (Phase 10)**:
   - Audits unallocated contingency margins (`EXHAUSTED`, `CRITICAL`, `LOW`, `HEALTHY`).
   - Flags whether mid-season parameter shifts trip re-optimization triggers.
   - Computes plan stability under scenario stress using Total Variation Distance.

---

## 4. Understanding Scientific Disclaimers

### Why are Yield and Revenue Predictions Gated?
FarmTwin strictly complies with academic and scientific honesty principles. In the current release, a verified historical yield dataset calibrated for localized micro-climates is not bundled. Rather than fabricating synthetic crop yields, market prices, or net profit calculations, the engine:
1. Operates in `RESOURCE_ONLY` optimization mode (maximizing suitability-weighted land productivity).
2. Explicitly flags yield modules as `BLOCKED_NO_HISTORICAL_DATASET`.
3. Displays dual variables in objective units ($\Delta\text{suitability-weighted ha} / \Delta\text{resource}$) rather than hallucinated currency.

---

## 5. Frequently Asked Questions (FAQ)

**Q: Does FarmTwin require an internet connection?**  
A: No. All machine learning models, optimization routines, and decision rules run $100\%$ locally on your device.

**Q: What should I do if the solver reports an "Infeasible" plan?**  
A: Infeasibility typically occurs when your available working capital or irrigation water is insufficient to cultivate even the minimum viable land increment. Increase your seasonal budget or water allocation in the input form and re-run.

**Q: Why does Crop Rotation show "DATA_UNAVAILABLE"?**  
A: Because the repository configuration currently lacks populated botanical family and multi-season succession rules. In compliance with data honesty standards, FarmTwin refuses to invent fake rotation cycles.
