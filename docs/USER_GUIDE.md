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

The application is structured into a streamlined two-column workspace:
1. **Left Sidebar (Farm Configuration)**: Input your farm's physical dimensions, soil laboratory test results, water infrastructure, seasonal weather forecasts, and working capital.
2. **Main Dashboard (Decision Workspace)**: Contains tabs for:
   - **Farm Overview**: Quick summary of inputs, boundary checks, and total holding dimensions.
   - **Crop Suitability AI**: Agronomic suitability probabilities across candidate crops.
   - **Resource Optimization**: Feasible land allocation plans calculated via continuous Linear Programming.
   - **Portfolio & Rotation Intelligence**: Agronomic diversity ($H'$), soil nutrient balance, and crop rotation advisories.
   - **Bottleneck & Shadow Values**: Identification of binding constraints and $+10\% / +20\%$ What-If resource expansion levers.
   - **Adaptive Reserve & Mid-Season Recourse**: Safety buffers, mid-season shock triggers, and plan stability metrics.

---

## 3. Step-by-Step Workflow

### Step 1: Input Farm Profile
1. **Land & Location**: Enter your land holding in acres (automatically converted to hectares) and select your cultivation season (Kharif, Rabi, Zaid).
2. **Soil Chemistry**: Enter laboratory-tested Nitrogen ($N$), Phosphorus ($P$), Potassium ($K$) in kg/ha, and soil pH ($3.5 - 10.0$).
3. **Weather Forecast**: Enter anticipated seasonal rainfall (mm), ambient temperature (°C), and relative humidity (%).
4. **Resources & Infrastructure**: Specify your seasonal irrigation water volume (in Liters) and seasonal working capital budget (in ₹ INR).
5. Click **"Save & Validate Farm Profile"**. If any parameter violates physical or agronomic bounds, an explicit validation error will guide your correction.

### Step 2: Review Crop Suitability AI
- The machine learning classifier evaluates your soil and climatic parameters against 22 crop models.
- Crops are displayed in rank order with their normalized probability score ($0\% - 100\%$).
- If a crop has an agronomic mismatch (e.g., rainfall too low or pH too alkaline), the card highlights specific **Limiting Factors** explaining why the crop is suboptimal.

### Step 3: Run Farm Plan Optimization
- In the **Resource Optimization** tab, click **"Solve Optimal Farm Plan"**.
- The solver analyzes your top suitable crops against five concurrent resource boundaries:
  - Total Land Area (ha)
  - Seasonal Irrigation Water (Liters)
  - Seasonal Operating Budget (₹ INR)
  - Soil Nitrogen, Phosphorus, Potassium capacity limits
  - Monoculture risk limit (default maximum $60\%$ to any single crop)
- The resulting allocation table specifies:
  - Exact hectares and acres allocated to each viable crop.
  - Land share percentages.
  - Total resource consumption versus available inventory.
  - Feasibility status and solver diagnostic flags.

### Step 4: Inspect Decision Intelligence

#### Portfolio & Soil Health Tab
- **Shannon Diversity Index ($H'$)**:
  - $H' = 0$: Monoculture (high agronomic vulnerability).
  - $0 < H' < 1.0$: Moderate diversification.
  - $H' \ge 1.0$: High ecological diversification and pest resistance.
- **Soil Balance Indicator**: Identifies whether the crop mix will draw heavily on soil nutrients or replenish nitrogen via leguminous crops (e.g., chickpea, lentil).

#### Bottleneck & Shadow Values Tab
- **Binding Constraints**: Highlighted in red. These resources reached $100\%$ capacity and actively cap your farm's productivity.
- **Resource Regimes**:
  - *Binding*: Expanding this resource directly increases your productive capacity.
  - *Near-Binding ($90-99\%$)*: Warning zone; minor shocks will exhaust this resource.
  - *Active ($50-89\%$)*: Balanced operational capacity.
  - *Underutilized ($<50\%$)*: Surplus capacity; consider reallocating funds.
- **What-If Sensitivity Levers**: Demonstrates the simulated impact on land utilization if you expand your binding resource by $+10\%$ or $+20\%$.

#### Adaptive Reserve & Mid-Season Recourse Tab
- **Safety Buffers**: Shows the unallocated percentage remaining across water, budget, and nutrients.
- **Mid-Season Triggers**: Flags whether sudden mid-season shocks (e.g., a $25\%$ monsoon deficit) exceed safe buffer thresholds.
- **Plan Stability Index**: Measures how much of your original planting plan remains intact if you are forced to re-optimize mid-season.

---

## 4. Understanding Scientific Disclaimers

### Why are Yield and Revenue Predictions Gated?
FarmTwin strictly complies with academic and scientific honesty principles. In the current release, a verified historical yield dataset calibrated for localized micro-climates is not bundled. Rather than fabricating synthetic crop yields, market prices, or net profit calculations, the engine:
1. Operates in `RESOURCE_ONLY` optimization mode (maximizing suitability-weighted land productivity).
2. Explicitly flags yield modules as `BLOCKED_NO_YIELD_MODEL`.
3. Displays dual variables in objective units ($\Delta\text{suitability-weighted ha} / \Delta\text{resource}$) rather than hallucinated currency.

---

## 5. Frequently Asked Questions (FAQ)

**Q: Can I allocate 100% of my land to one high-value crop?**  
A: No. By default, the optimizer enforces a diversification ceiling (maximum $60\%$ land share to any single crop) to prevent monoculture disease outbreaks and systemic soil depletion.

**Q: What should I do if the solver reports an "Infeasible" plan?**  
A: Infeasibility typically occurs when your available working capital or irrigation water is insufficient to cultivate even the minimum viable land increment. Increase your seasonal budget or water allocation in the sidebar and re-run.

**Q: Does FarmTwin require an internet connection?**  
A: No. All machine learning models, optimization routines, and decision rules run $100\%$ locally on your device.
