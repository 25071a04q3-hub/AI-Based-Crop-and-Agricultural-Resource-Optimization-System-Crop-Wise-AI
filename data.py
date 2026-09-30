import os
import json
import numpy as np
import pandas as pd

# ==========================================
# STRICT UNIT CONVERSION CONSTANTS & FUNCTIONS
# ==========================================
TONNE_TO_QUINTAL = 10.0  # 1 tonne = 10 quintals
MM_TO_M3_PER_HA = 10.0   # 1 mm water depth over 1 ha = 10 m³

def revenue_per_ha(yield_t_per_ha: float, price_per_quintal: float) -> float:
    """
    Calculates gross revenue per hectare in INR.
    Yield is in tonnes/ha, price in INR/quintal.
    Revenue = yield (t/ha) * 10 (quintals/t) * price (INR/quintal)
    """
    return yield_t_per_ha * TONNE_TO_QUINTAL * price_per_quintal

def water_mm_to_m3_per_ha(water_mm: float) -> float:
    """Converts water requirement from mm depth over 1 ha to m³/ha."""
    return water_mm * MM_TO_M3_PER_HA

# Data Paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CROP_RECOMMENDATION_PATH = os.path.join(DATA_DIR, "crop_recommendation.csv")
YIELD_DATA_PATH = os.path.join(DATA_DIR, "yield_data.csv")
CROPS_JSON_PATH = os.path.join(os.path.dirname(__file__), "crops.json")

# Default 22 crops from Kaggle dataset with realistic bounds
CROP_SPECS = {
    'rice': {'N': (60, 120), 'P': (35, 60), 'K': (35, 45), 'temp': (20, 27), 'hum': (80, 90), 'ph': (6.0, 7.8), 'rain': (180, 300)},
    'maize': {'N': (60, 100), 'P': (35, 60), 'K': (15, 25), 'temp': (18, 27), 'hum': (55, 75), 'ph': (5.5, 7.0), 'rain': (60, 110)},
    'chickpea': {'N': (20, 50), 'P': (55, 80), 'K': (75, 85), 'temp': (17, 21), 'hum': (14, 20), 'ph': (6.0, 8.8), 'rain': (65, 95)},
    'kidneybeans': {'N': (15, 40), 'P': (55, 80), 'K': (15, 25), 'temp': (15, 24), 'hum': (18, 25), 'ph': (5.5, 5.8), 'rain': (60, 150)},
    'pigeonpeas': {'N': (15, 40), 'P': (55, 80), 'K': (15, 25), 'temp': (27, 37), 'hum': (30, 65), 'ph': (4.5, 7.5), 'rain': (90, 190)},
    'mothbeans': {'N': (0, 40), 'P': (35, 60), 'K': (15, 25), 'temp': (24, 32), 'hum': (40, 65), 'ph': (3.5, 10.0), 'rain': (30, 75)},
    'mungbean': {'N': (0, 40), 'P': (35, 60), 'K': (15, 25), 'temp': (27, 30), 'hum': (80, 90), 'ph': (6.2, 7.2), 'rain': (35, 60)},
    'blackgram': {'N': (40, 60), 'P': (55, 80), 'K': (15, 25), 'temp': (25, 35), 'hum': (60, 70), 'ph': (6.5, 7.8), 'rain': (60, 75)},
    'lentil': {'N': (10, 30), 'P': (55, 80), 'K': (15, 25), 'temp': (18, 30), 'hum': (60, 70), 'ph': (5.9, 7.8), 'rain': (35, 55)},
    'pomegranate': {'N': (10, 40), 'P': (10, 30), 'K': (35, 45), 'temp': (18, 25), 'hum': (85, 95), 'ph': (5.5, 7.2), 'rain': (100, 110)},
    'banana': {'N': (80, 120), 'P': (70, 95), 'K': (45, 55), 'temp': (25, 30), 'hum': (75, 85), 'ph': (5.5, 6.5), 'rain': (90, 120)},
    'mango': {'N': (0, 40), 'P': (15, 40), 'K': (25, 35), 'temp': (27, 36), 'hum': (45, 55), 'ph': (4.5, 7.0), 'rain': (85, 100)},
    'grapes': {'N': (20, 40), 'P': (120, 145), 'K': (195, 205), 'temp': (8, 42), 'hum': (80, 85), 'ph': (5.5, 6.5), 'rain': (65, 75)},
    'watermelon': {'N': (80, 120), 'P': (5, 30), 'K': (45, 55), 'temp': (24, 27), 'hum': (80, 90), 'ph': (6.0, 7.0), 'rain': (40, 60)},
    'muskmelon': {'N': (80, 120), 'P': (5, 30), 'K': (45, 55), 'temp': (27, 30), 'hum': (90, 95), 'ph': (6.0, 6.8), 'rain': (20, 30)},
    'apple': {'N': (20, 40), 'P': (120, 145), 'K': (195, 205), 'temp': (21, 24), 'hum': (90, 95), 'ph': (5.5, 6.5), 'rain': (100, 125)},
    'orange': {'N': (15, 40), 'P': (5, 30), 'K': (5, 15), 'temp': (10, 35), 'hum': (90, 95), 'ph': (6.0, 7.5), 'rain': (100, 120)},
    'papaya': {'N': (30, 70), 'P': (45, 70), 'K': (45, 55), 'temp': (23, 44), 'hum': (90, 95), 'ph': (6.0, 7.0), 'rain': (40, 250)},
    'coconut': {'N': (15, 40), 'P': (5, 30), 'K': (25, 35), 'temp': (25, 28), 'hum': (90, 98), 'ph': (5.5, 6.5), 'rain': (130, 220)},
    'cotton': {'N': (100, 140), 'P': (35, 60), 'K': (15, 25), 'temp': (22, 26), 'hum': (75, 85), 'ph': (6.0, 8.0), 'rain': (60, 90)},
    'jute': {'N': (60, 100), 'P': (35, 60), 'K': (35, 45), 'temp': (23, 26), 'hum': (70, 80), 'ph': (6.0, 7.5), 'rain': (150, 200)},
    'coffee': {'N': (80, 120), 'P': (15, 40), 'K': (25, 35), 'temp': (23, 28), 'hum': (50, 70), 'ph': (6.0, 7.5), 'rain': (115, 190)}
}

TYPICAL_YIELDS = {
    'rice': 4.5, 'maize': 5.0, 'chickpea': 1.8, 'kidneybeans': 1.5, 'pigeonpeas': 1.2,
    'mothbeans': 0.8, 'mungbean': 1.0, 'blackgram': 1.1, 'lentil': 1.3, 'pomegranate': 12.0,
    'banana': 35.0, 'mango': 10.0, 'grapes': 20.0, 'watermelon': 25.0, 'muskmelon': 18.0,
    'apple': 15.0, 'orange': 14.0, 'papaya': 40.0, 'coconut': 11.0, 'cotton': 2.5,
    'jute': 2.8, 'coffee': 1.2
}

def generate_synthetic_crop_data(samples_per_crop=100) -> pd.DataFrame:
    """Generates synthetic dataset for crop classification matching Kaggle schema."""
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = []
    np.random.seed(42)
    for crop, bounds in CROP_SPECS.items():
        for _ in range(samples_per_crop):
            rows.append({
                'N': np.random.uniform(*bounds['N']),
                'P': np.random.uniform(*bounds['P']),
                'K': np.random.uniform(*bounds['K']),
                'temperature': np.random.uniform(*bounds['temp']),
                'humidity': np.random.uniform(*bounds['hum']),
                'ph': np.random.uniform(*bounds['ph']),
                'rainfall': np.random.uniform(*bounds['rain']),
                'label': crop
            })
    df = pd.DataFrame(rows)
    df.to_csv(CROP_RECOMMENDATION_PATH, index=False)
    return df

def generate_synthetic_yield_data(samples_per_crop=150) -> pd.DataFrame:
    """Generates synthetic yield data driven by soil + weather conditions with realistic response."""
    os.makedirs(DATA_DIR, exist_ok=True)
    rows = []
    np.random.seed(101)
    for crop, bounds in CROP_SPECS.items():
        base_yield = TYPICAL_YIELDS[crop]
        for _ in range(samples_per_crop):
            n = np.random.uniform(bounds['N'][0] * 0.7, bounds['N'][1] * 1.3)
            p = np.random.uniform(bounds['P'][0] * 0.7, bounds['P'][1] * 1.3)
            k = np.random.uniform(bounds['K'][0] * 0.7, bounds['K'][1] * 1.3)
            temp = np.random.uniform(bounds['temp'][0] - 3, bounds['temp'][1] + 3)
            hum = np.random.uniform(bounds['hum'][0] - 10, bounds['hum'][1] + 10)
            ph = np.random.uniform(bounds['ph'][0] - 0.5, bounds['ph'][1] + 0.5)
            rain = np.random.uniform(bounds['rain'][0] * 0.6, bounds['rain'][1] * 1.4)
            
            # Simple quadratic response penalty away from ideal midpoints
            ideal_temp = np.mean(bounds['temp'])
            ideal_rain = np.mean(bounds['rain'])
            temp_penalty = max(0, 1 - 0.02 * ((temp - ideal_temp) ** 2))
            rain_penalty = max(0, 1 - 0.0005 * ((rain - ideal_rain) ** 2))
            
            yield_val = base_yield * temp_penalty * rain_penalty * np.random.normal(1.0, 0.08)
            yield_val = max(0.1, yield_val) # non-negative yield
            
            rows.append({
                'crop': crop,
                'N': n, 'P': p, 'K': k,
                'temperature': temp, 'humidity': hum, 'ph': ph, 'rainfall': rain,
                'yield_t_per_ha': round(yield_val, 2)
            })
    df = pd.DataFrame(rows)
    df.to_csv(YIELD_DATA_PATH, index=False)
    return df

def load_crop_recommendation_data() -> pd.DataFrame:
    """Loads crop recommendation dataset or creates synthetic data if absent."""
    if os.path.exists(CROP_RECOMMENDATION_PATH):
        return pd.read_csv(CROP_RECOMMENDATION_PATH)
    return generate_synthetic_crop_data()

def load_yield_data() -> pd.DataFrame:
    """Loads yield dataset or creates synthetic data if absent."""
    if os.path.exists(YIELD_DATA_PATH):
        return pd.read_csv(YIELD_DATA_PATH)
    return generate_synthetic_yield_data()

def load_crop_knowledge() -> dict:
    """Loads crop profiles JSON (prices, costs, water/fertilizer reqs)."""
    if os.path.exists(CROPS_JSON_PATH):
        with open(CROPS_JSON_PATH, "r") as f:
            return json.load(f)
    raise FileNotFoundError(f"Missing crop knowledge file at {CROPS_JSON_PATH}")

def save_crop_knowledge(knowledge_data: dict) -> None:
    """Saves updated crop knowledge profiles to JSON."""
    with open(CROPS_JSON_PATH, "w") as f:
        json.dump(knowledge_data, f, indent=2)