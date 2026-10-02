import warnings
warnings.filterwarnings("ignore", message="X has feature names")
import os
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score

from data import load_crop_recommendation_data, load_yield_data

MODEL_DIR = os.path.join(os.path.dirname(__file__), "saved_models")
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "crop_classifier.joblib")
YIELD_REGRESSOR_PATH = os.path.join(MODEL_DIR, "yield_regressor.joblib")

FEATURES = ['N', 'P', 'K', 'temperature', 'humidity', 'ph', 'rainfall']

def train_and_save_models():
    """Trains classification and regression models and saves them to disk."""
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # 1. Train Crop Suitability Classifier
    df_cls = load_crop_recommendation_data()
    X_cls = df_cls[FEATURES]
    y_cls = df_cls['label']
    
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_cls, y_cls, test_size=0.2, random_state=42, stratify=y_cls
    )
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    clf.fit(X_train_c, y_train_c)
    
    preds_c = clf.predict(X_test_c)
    acc = accuracy_score(y_test_c, preds_c)
    f1 = f1_score(y_test_c, preds_c, average='weighted')
    
    # 2. Train Yield Regressor
    df_yld = load_yield_data()
    # One-hot encode crop name for yield prediction
    df_yld_encoded = pd.get_dummies(df_yld, columns=['crop'], drop_first=False)
    
    X_reg = df_yld_encoded.drop(columns=['yield_t_per_ha'])
    y_reg = df_yld_encoded['yield_t_per_ha']
    
    X_train_r, X_test_r, y_train_r, y_test_r = train_test_split(
        X_reg, y_reg, test_size=0.2, random_state=42
    )
    reg = GradientBoostingRegressor(n_estimators=120, random_state=42)
    reg.fit(X_train_r, y_train_r)
    
    preds_r = reg.predict(X_test_r)
    mae = mean_absolute_error(y_test_r, preds_r)
    r2 = r2_score(y_test_r, preds_r)
    
    metrics = {
        'cls_accuracy': acc,
        'cls_f1': f1,
        'reg_mae': mae,
        'reg_r2': r2,
        'feature_importances': dict(zip(FEATURES, clf.feature_importances_))
    }
    
    joblib.dump((clf, metrics), CLASSIFIER_PATH)
    joblib.dump((reg, X_reg.columns.tolist()), YIELD_REGRESSOR_PATH)
    return metrics

def load_or_train_models():
    """Loads models if they exist, otherwise triggers training."""
    if not (os.path.exists(CLASSIFIER_PATH) and os.path.exists(YIELD_REGRESSOR_PATH)):
        train_and_save_models()
    clf, metrics = joblib.load(CLASSIFIER_PATH)
    reg, reg_columns = joblib.load(YIELD_REGRESSOR_PATH)
    return clf, metrics, reg, reg_columns

def predict_crop_suitability(input_dict: dict, top_k=5):
    """Predicts top-K suitable crops with probability scores."""
    clf, metrics, _, _ = load_or_train_models()
    input_df = pd.DataFrame([input_dict])[FEATURES]
    
    probs = clf.predict_proba(input_df)[0]
    classes = clf.classes_
    
    top_indices = np.argsort(probs)[::-1][:top_k]
    recommendations = [
        {'crop': classes[i], 'probability': float(probs[i])}
        for i in top_indices
    ]
    return recommendations, metrics

def predict_crop_yield(crop_name: str, input_dict: dict):
    """
    Predicts expected crop yield (t/ha) along with ensemble spread (low / expected / high).
    """
    _, _, reg, reg_columns = load_or_train_models()
    
    data = {col: 0.0 for col in reg_columns}
    for f in FEATURES:
        if f in input_dict:
            data[f] = float(input_dict[f])
            
    crop_col = f"crop_{crop_name}"
    if crop_col in data:
        data[crop_col] = 1.0
        
    input_df = pd.DataFrame([data])[reg_columns]
    expected_yield = float(reg.predict(input_df)[0])
    
    # Estimate quantile/uncertainty spread using individual stage estimators
    stage_preds = [est[0].predict(input_df)[0] for est in reg.estimators_]
    std_dev = np.std(stage_preds) if len(stage_preds) > 0 else expected_yield * 0.1
    
    low_yield = max(0.1, expected_yield - 1.28 * std_dev) # 10th percentile approx
    high_yield = expected_yield + 1.28 * std_dev          # 90th percentile approx
    
    return {
        'expected': round(expected_yield, 2),
        'low': round(low_yield, 2),
        'high': round(high_yield, 2)
    }
