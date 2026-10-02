# FarmTwin — Technical & Mathematical Specification Guide

This guide details the mathematical foundations, optimization formulations, algorithm implementations, and computational complexity of the **FarmTwin — Adaptive Farm Decision Engine**.

---

## 1. Mathematical Formulation of the Optimization Engine

### 1.1 Objective Function
FarmTwin formulates farm resource allocation as a continuous Linear Program (LP). In the verified `RESOURCE_ONLY` operational mode, the objective maximizes the total agronomic suitability-weighted cultivated area across candidate crops $C = \{1, \dots, n\}$:

$$\max_{\mathbf{x}} Z = \sum_{i \in C} s_i \cdot x_i$$

Where:
- $x_i \ge 0$: Land area allocated to crop $i$ in hectares ($\text{ha}$).
- $s_i \in (0, 1]$: Agronomic suitability probability score computed by the Random Forest classifier.
- $Z$: Suitability-weighted cultivated land area ($\text{ha}$).

### 1.2 System Constraints

#### Constraint 1: Total Land Holding
Cultivated land cannot exceed the total available farm holding $A_{\text{total}}$:
$$\sum_{i \in C} x_i \le A_{\text{total}}$$

#### Constraint 2: Irrigation Water Capacity
Seasonal crop water requirements cannot exceed available irrigation capacity $W_{\text{avail}}$ (Liters):
$$\sum_{i \in C} w_i \cdot x_i \le W_{\text{avail}}$$
Where $w_i$ is the water demand norm in $\text{L/ha}$ for crop $i$.

#### Constraint 3: Working Capital Budget
Cultivation expenditures across all crops cannot exceed available seasonal capital $B_{\text{avail}}$ (INR):
$$\sum_{i \in C} b_i \cdot x_i \le B_{\text{avail}}$$
Where $b_i$ is the operating cost norm in $\text{INR/ha}$ for crop $i$.

#### Constraints 4–6: Soil Nutrient Influx Bounds
Aggregate nutrient removal/application across crops cannot exceed total soil nutrient capital:
$$\sum_{i \in C} N_i \cdot x_i \le \bar{N} \cdot A_{\text{total}}$$
$$\sum_{i \in C} P_i \cdot x_i \le \bar{P} \cdot A_{\text{total}}$$
$$\sum_{i \in C} K_i \cdot x_i \le \bar{K} \cdot A_{\text{total}}$$
Where $N_i, P_i, K_i$ are crop nutrient uptake rates ($\text{kg/ha}$), and $\bar{N}, \bar{P}, \bar{K}$ are soil test levels.

#### Constraint 7: Monoculture Risk Ceiling
To enforce agronomic biodiversity and prevent pest build-up, no single crop may exceed a fraction $f_{\max} \in (0, 1]$ (default $0.60$) of total land:
$$x_i \le f_{\max} \cdot A_{\text{total}}, \quad \forall i \in C$$

#### Non-negativity:
$$x_i \ge 0, \quad \forall i \in C$$

---

## 2. Solver Mechanics & Duality

### 2.1 HiGHS Simplex Solver
FarmTwin interfaces with SciPy's high-performance C++ solver `scipy.optimize.linprog(..., method='highs')`.

Matrix standard form:
$$\min_{\mathbf{x}} (-\mathbf{s}^T \mathbf{x}) \quad \text{s.t.} \quad \mathbf{A} \mathbf{x} \le \mathbf{b}, \quad \mathbf{0} \le \mathbf{x} \le \mathbf{u}$$

### 2.2 Dual Variables (Shadow Prices)
For each constraint $j \in \{1, \dots, m\}$ with capacity $b_j$, the dual variable $\lambda_j$ satisfies:
$$\lambda_j = \frac{\partial Z^*}{\partial b_j}$$

- If constraint $j$ is slack (unbound, capacity surplus), complementary slackness dictates $\lambda_j = 0$.
- If constraint $j$ is binding (tight), $\lambda_j > 0$ represents the marginal increase in suitability-weighted land productivity per unit increase in resource $b_j$.
- **Scientific Honesty Compliance**: Units of $\lambda_j$ are strictly expressed as $\Delta \text{weighted ha} / \Delta \text{unit}$ (e.g., $\text{ha} / 10^5\text{ L}$ or $\text{ha} / \text{₹}10^4$).

---

## 3. Decision Intelligence Mathematics

### 3.1 Shannon Diversity Index ($H'$)
Used in Phase 8 (Portfolio Intelligence) to quantify crop diversification:
$$H' = -\sum_{i=1}^k p_i \ln(p_i)$$
Where:
- $k$ is the number of crops with non-zero allocation ($x_i > 0$).
- $p_i = \frac{x_i}{\sum_{j=1}^k x_j}$ is the land share of crop $i$.

Interpretation:
- $H' = 0$: Complete monoculture.
- $H' \ge 1.0$: High agronomic resilience against crop-specific climate or pathogen shocks.

### 3.2 Resilience Ratio
The area-weighted suitability of the realized allocation:
$$R = \frac{\sum_{i \in C} s_i \cdot x_i}{\sum_{i \in C} x_i}$$
Reflects whether the optimizer preserved high-suitability crops despite binding resource constraints.

### 3.3 Plan Stability Metric under Mid-Season Shock
When an unexpected mid-season shock triggers a re-optimization, let $\mathbf{p}^{(0)}$ be the baseline crop distribution and $\mathbf{p}^{(1)}$ be the post-shock recourse distribution. Plan stability is computed via Total Variation Distance:

$$\text{Stability} = 1.0 - \frac{1}{2} \sum_{i \in C} \left| p_i^{(0)} - p_i^{(1)} \right|$$

Properties:
- $\text{Stability} = 1.0$: Allocation unchanged; maximum operational continuity.
- $\text{Stability} = 0.0$: Total structural reallocation required.

---

## 4. Computational Complexity

| Module | Primary Algorithm | Time Complexity | Typical Latency |
| :--- | :--- | :--- | :--- |
| `profile.py` | Pydantic runtime schema validation | $O(1)$ | $< 1\text{ ms}$ |
| `crop_suitability.py` | Random Forest inference (100 estimators) | $O(T \cdot d)$ | $\approx 10\text{ ms}$ |
| `scenario_simulator.py` | 7 stress scenarios $\times$ RF inference | $O(K \cdot T \cdot d)$ | $\approx 45\text{ ms}$ |
| `resource_calculator.py`| Vector-matrix dot product | $O(|C|)$ | $< 1\text{ ms}$ |
| `optimizer.py` | HiGHS dual simplex LP solver | $O(m^2 n)$ | $\approx 5\text{ ms}$ |
| `portfolio_intelligence.py` | Shannon entropy & soil balance | $O(|C|)$ | $< 1\text{ ms}$ |
| `bottleneck_analysis.py` | Dual extraction & 2 sensitivity re-runs | $O(2 \cdot m^2 n)$ | $\approx 12\text{ ms}$ |
| `adaptive_reserve.py` | Buffer metrics & recourse LP check | $O(m^2 n)$ | $\approx 8\text{ ms}$ |

The complete 10-phase pipeline executes in **under 100 milliseconds**, enabling instantaneous interactive updates in the Streamlit user interface.
