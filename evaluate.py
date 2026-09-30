import warnings
warnings.filterwarnings("ignore", message="X has feature names")
import numpy as np
import pandas as pd
from models import load_or_train_models, predict_crop_suitability, predict_crop_yield
from optimizer import run_strategy_benchmarks

def run_benchmark_evaluations(num_trials=200):
    """
    Evaluates optimizer over N random farm scenarios to compute average net profit gain
    and water savings compared to traditional equal splitting.
    """
    print(f"Running benchmark evaluation over {num_trials} random farm scenarios...")
    
    # Ensure models are trained
    load_or_train_models()
    
    np.random.seed(42)
    profit_gains_pct = []
    water_savings_pct = []
    
    for _ in range(num_trials):
        # Generate random realistic farm scenario
        input_dict = {
            'N': np.random.uniform(20, 120),
            'P': np.random.uniform(15, 80),
            'K': np.random.uniform(15, 80),
            'temperature': np.random.uniform(18, 35),
            'humidity': np.random.uniform(40, 90),
            'ph': np.random.uniform(5.5, 7.5),
            'rainfall': np.random.uniform(50, 250)
        }
        
        land_ha = np.random.uniform(1.0, 10.0)
        water_m3 = land_ha * np.random.uniform(3000, 8000)
        max_n = land_ha * np.random.uniform(80, 150)
        max_p = land_ha * np.random.uniform(40, 80)
        max_k = land_ha * np.random.uniform(40, 80)
        budget_inr = land_ha * np.random.uniform(30000, 70000)
        
        top_crops, _ = predict_crop_suitability(input_dict, top_k=5)
        candidate_list = [item['crop'] for item in top_crops]
        
        predicted_yields = {c: predict_crop_yield(c, input_dict) for c in candidate_list}
        
        benchmarks = run_strategy_benchmarks(
            candidate_list, predicted_yields, land_ha, water_m3,
            max_n, max_p, max_k, budget_inr, risk_aversion=0.2
        )
        
        trad_profit = benchmarks['Traditional Equal Split']['net_profit_inr']
        opt_profit = benchmarks['Profit Maximizing (LP)']['net_profit_inr']
        
        trad_water = benchmarks['Traditional Equal Split']['water_used_m3']
        opt_water = benchmarks['Profit Maximizing (LP)']['water_used_m3']
        
        if trad_profit > 0:
            pg = ((opt_profit - trad_profit) / trad_profit) * 100
            profit_gains_pct.append(pg)
            
        if trad_water > 0:
            ws = ((trad_water - opt_water) / trad_water) * 100
            water_savings_pct.append(ws)

    print("\n================ BENCHMARK RESULTS ================")
    print(f"Evaluated Scenarios : {num_trials}")
    print(f"Average Profit Gain : +{np.mean(profit_gains_pct):.2f}% vs Equal Split")
    print(f"Average Water Saved : {np.mean(water_savings_pct):.2f}% vs Equal Split")
    print("===================================================\n")

if __name__ == "__main__":
    run_benchmark_evaluations(200)