import numpy as np
from scipy.optimize import linprog
from data import revenue_per_ha, water_mm_to_m3_per_ha, load_crop_knowledge

def solve_crop_allocation(
    candidate_crops: list,
    predicted_yields: dict,
    total_land_ha: float,
    max_water_m3: float,
    max_n_kg: float,
    max_p_kg: float,
    max_k_kg: float,
    max_budget_inr: float,
    min_share: float = 0.05,
    max_share: float = 0.60,
    forced_crop: str = None,
    forced_area_ha: float = 0.0,
    strategy: str = "profit_lp",
    water_saving_mode: bool = False,
    risk_aversion: float = 0.0
):
    """
    Linear Programming Crop Resource Allocator using scipy.optimize.linprog.
    
    Decision Variables:
    -------------------
    x_i = area allocated to candidate crop i (in hectares)
    """
    knowledge = load_crop_knowledge()
    n = len(candidate_crops)
    if n == 0:
        return None, "No candidate crops provided."

    # Objective Function Setup (Scipy minimizes, so negate for maximization)
    c = []
    water_reqs = []
    n_reqs = []
    p_reqs = []
    k_reqs = []
    costs = []

    for crop in candidate_crops:
        prof = knowledge.get(crop, {})
        
        # Yield selection based on risk choice
        if strategy == "risk_aware" or risk_aversion > 0.5:
            yd = predicted_yields[crop]['low'] # Pessimistic yield
            price = prof.get('price_per_quintal', 2000) * (1.0 - prof.get('price_volatility', 0.1) * risk_aversion)
        elif strategy == "yield_max":
            yd = predicted_yields[crop]['high']
            price = prof.get('price_per_quintal', 2000)
        else:
            yd = predicted_yields[crop]['expected']
            price = prof.get('price_per_quintal', 2000)

        cost = prof.get('cost_per_ha', 25000)
        w_mm = prof.get('water_req_mm', 500)
        
        if water_saving_mode:
            # Add penalty to water consumption in objective
            water_penalty = 5.0 # INR per m3 effective penalty
        else:
            water_penalty = 0.0

        rev = revenue_per_ha(yd, price)
        net_margin_per_ha = rev - cost - (water_mm_to_m3_per_ha(w_mm) * water_penalty)

        if strategy == "yield_max":
            c.append(-yd) # Maximize yield
        else:
            c.append(-net_margin_per_ha) # Maximize net margin

        water_reqs.append(water_mm_to_m3_per_ha(w_mm))
        n_reqs.append(prof.get('n_req_kg_ha', 80))
        p_reqs.append(prof.get('p_req_kg_ha', 40))
        k_reqs.append(prof.get('k_req_kg_ha', 40))
        costs.append(cost)

    # Inequality constraints: A_ub * x <= b_ub
    A_ub = [
        [1.0] * n,          # Land constraint
        water_reqs,         # Water constraint
        n_reqs,             # N fertilizer constraint
        p_reqs,             # P fertilizer constraint
        k_reqs,             # K fertilizer constraint
        costs               # Budget constraint
    ]
    b_ub = [
        total_land_ha,
        max_water_m3,
        max_n_kg,
        max_p_kg,
        max_k_kg,
        max_budget_inr
    ]

    # Bounds per decision variable
    bounds = []
    for crop in candidate_crops:
        lb = total_land_ha * min_share
        ub = total_land_ha * max_share
        if crop == forced_crop and forced_area_ha > 0:
            lb = max(lb, min(forced_area_ha, total_land_ha))
            ub = max(lb, ub)
        bounds.append((lb, ub))

    res = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

    if not res.success:
        # Infeasibility diagnostics
        suggestion = "Infeasible constraints encountered. "
        if max_water_m3 < sum(water_reqs) / n * total_land_ha * min_share:
            suggestion += "Consider increasing available Water supply."
        elif max_budget_inr < sum(costs) / n * total_land_ha * min_share:
            suggestion += "Consider increasing total Budget."
        else:
            suggestion += "Try lowering the minimum share per crop or forced crop area."
        return None, suggestion

    allocations = dict(zip(candidate_crops, res.x))
    
    # Calculate detailed summary
    tot_yield = sum(allocations[c] * predicted_yields[c]['expected'] for c in candidate_crops)
    tot_cost = sum(allocations[c] * knowledge[c]['cost_per_ha'] for c in candidate_crops)
    tot_rev = sum(
        allocations[c] * revenue_per_ha(predicted_yields[c]['expected'], knowledge[c]['price_per_quintal'])
        for c in candidate_crops
    )
    tot_water = sum(allocations[c] * water_mm_to_m3_per_ha(knowledge[c]['water_req_mm']) for c in candidate_crops)
    tot_n = sum(allocations[c] * knowledge[c]['n_req_kg_ha'] for c in candidate_crops)
    tot_p = sum(allocations[c] * knowledge[c]['p_req_kg_ha'] for c in candidate_crops)
    tot_k = sum(allocations[c] * knowledge[c]['k_req_kg_ha'] for c in candidate_crops)

    return {
        'allocations': allocations,
        'total_yield_t': tot_yield,
        'total_revenue_inr': tot_rev,
        'total_cost_inr': tot_cost,
        'net_profit_inr': tot_rev - tot_cost,
        'water_used_m3': tot_water,
        'n_used_kg': tot_n,
        'p_used_kg': tot_p,
        'k_used_kg': tot_k,
        'fertilizer_used_kg': tot_n + tot_p + tot_k
    }, "Success"

def run_strategy_benchmarks(
    candidate_crops: list,
    predicted_yields: dict,
    total_land_ha: float,
    max_water_m3: float,
    max_n_kg: float,
    max_p_kg: float,
    max_k_kg: float,
    max_budget_inr: float,
    risk_aversion: float = 0.2
):
    """Compares 4 strategies side by side + water saving variant."""
    results = {}
    knowledge = load_crop_knowledge()
    n = len(candidate_crops)

    # 1. Traditional Equal Split
    eq_alloc = {c: total_land_ha / n for c in candidate_crops}
    eq_yield = sum(eq_alloc[c] * predicted_yields[c]['expected'] for c in candidate_crops)
    eq_cost = sum(eq_alloc[c] * knowledge[c]['cost_per_ha'] for c in candidate_crops)
    eq_rev = sum(eq_alloc[c] * revenue_per_ha(predicted_yields[c]['expected'], knowledge[c]['price_per_quintal']) for c in candidate_crops)
    eq_water = sum(eq_alloc[c] * water_mm_to_m3_per_ha(knowledge[c]['water_req_mm']) for c in candidate_crops)
    eq_fert = sum(eq_alloc[c] * (knowledge[c]['n_req_kg_ha'] + knowledge[c]['p_req_kg_ha'] + knowledge[c]['k_req_kg_ha']) for c in candidate_crops)

    results['Traditional Equal Split'] = {
        'allocations': eq_alloc,
        'total_yield_t': eq_yield,
        'total_revenue_inr': eq_rev,
        'total_cost_inr': eq_cost,
        'net_profit_inr': eq_rev - eq_cost,
        'water_used_m3': eq_water,
        'fertilizer_used_kg': eq_fert,
        'profit_gain_pct': 0.0,
        'water_saved_pct': 0.0
    }

    # Helper lambda to package standard runs
    def get_run(strat, w_save=False, risk=0.0):
        res, msg = solve_crop_allocation(
            candidate_crops, predicted_yields, total_land_ha, max_water_m3,
            max_n_kg, max_p_kg, max_k_kg, max_budget_inr,
            strategy=strat, water_saving_mode=w_save, risk_aversion=risk
        )
        if res is None:
            return results['Traditional Equal Split']
        res['profit_gain_pct'] = ((res['net_profit_inr'] - results['Traditional Equal Split']['net_profit_inr']) /
                                  max(1, abs(results['Traditional Equal Split']['net_profit_inr']))) * 100
        res['water_saved_pct'] = ((results['Traditional Equal Split']['water_used_m3'] - res['water_used_m3']) /
                                  max(1, results['Traditional Equal Split']['water_used_m3'])) * 100
        return res

    results['Yield Maximizing'] = get_run('yield_max')
    results['Profit Maximizing (LP)'] = get_run('profit_lp')
    results['Risk-Aware / Robust'] = get_run('risk_aware', risk=risk_aversion)
    results['Water-Saving Mode'] = get_run('profit_lp', w_save=True)

    return results