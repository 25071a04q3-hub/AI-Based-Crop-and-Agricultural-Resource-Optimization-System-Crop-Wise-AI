"""
AI-Based Crop & Agricultural Resource Optimization System  -  Streamlit dashboard
Run:  streamlit run app.py

Self-contained: needs only pandas, numpy, scikit-learn, scipy, streamlit, plotly, requests.
Data used here is SYNTHETIC (clearly labelled in the UI). Prices/costs are editable
defaults in the CROPS table below (or edit the table live in the sidebar expander).
"""
import warnings

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from scipy.optimize import linprog
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore", message="X has feature names")

st.set_page_config(page_title="Crop Optimizer", page_icon="🌾", layout="wide")

# ----------------------------------------------------------------------------
# 1. CROP KNOWLEDGE TABLE  (approximate defaults - EDITABLE)
#    env = (mean, sd) for N, P, K, temperature, humidity, ph, rainfall
#    water in m3/ha, N/P/K in kg/ha, cost in INR/ha, price in INR/quintal
# ----------------------------------------------------------------------------
FEATS = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]

CROPS = {
    "rice":      dict(water=12000, N=120, P=60, K=40, cost=45000, price=2200, vol=0.15, days=130, base=4.5,
                      env=[(80, 20), (48, 10), (40, 8), (24, 3), (82, 6), (6.4, .5), (230, 40)]),
    "maize":     dict(water=6000, N=120, P=60, K=40, cost=30000, price=2100, vol=0.20, days=110, base=5.5,
                      env=[(78, 18), (48, 10), (20, 6), (23, 3), (65, 8), (6.2, .5), (85, 20)]),
    "cotton":    dict(water=8000, N=100, P=50, K=50, cost=55000, price=6500, vol=0.25, days=170, base=2.2,
                      env=[(120, 20), (45, 10), (20, 6), (24, 3), (80, 7), (6.9, .6), (80, 20)]),
    "chickpea":  dict(water=3500, N=20, P=40, K=20, cost=22000, price=5400, vol=0.15, days=100, base=1.4,
                      env=[(40, 10), (68, 10), (80, 10), (19, 3), (30, 10), (7.3, .6), (80, 15)]),
    "pigeonpea": dict(water=5000, N=25, P=50, K=25, cost=25000, price=7000, vol=0.20, days=160, base=1.2,
                      env=[(20, 8), (68, 10), (20, 6), (28, 3), (50, 10), (5.8, .5), (150, 30)]),
    "groundnut": dict(water=5000, N=25, P=55, K=75, cost=38000, price=5800, vol=0.20, days=115, base=2.0,
                      env=[(30, 10), (55, 10), (35, 8), (27, 3), (60, 10), (6.3, .5), (100, 25)]),
    "mungbean":  dict(water=4000, N=20, P=40, K=20, cost=18000, price=7500, vol=0.20, days=70, base=0.9,
                      env=[(20, 8), (47, 10), (20, 6), (28, 2.5), (85, 5), (6.7, .5), (50, 15)]),
    "sorghum":   dict(water=4500, N=80, P=40, K=30, cost=20000, price=3200, vol=0.15, days=110, base=2.5,
                      env=[(75, 15), (40, 8), (25, 6), (27, 3), (55, 10), (6.7, .6), (70, 20)]),
    "sunflower": dict(water=5000, N=60, P=40, K=40, cost=28000, price=6800, vol=0.22, days=100, base=1.6,
                      env=[(60, 12), (45, 10), (40, 8), (25, 3), (60, 10), (6.6, .5), (65, 20)]),
    "soybean":   dict(water=5000, N=30, P=60, K=40, cost=28000, price=4600, vol=0.20, days=100, base=2.0,
                      env=[(40, 10), (60, 10), (40, 8), (26, 3), (70, 8), (6.4, .5), (110, 25)]),
}
CROP_NAMES = list(CROPS)

# ----------------------------------------------------------------------------
# 2. TRANSLATIONS
# ----------------------------------------------------------------------------
LANGS = {"English": "en", "తెలుగు": "te", "हिन्दी": "hi"}

T = {
    "en": dict(
        title="🌾 AI Crop & Resource Optimizer", sub="Decide what to grow and how much - using your soil, weather and limited resources.",
        synth="⚠️ Demo uses SYNTHETIC training data. Prices and costs are approximate and editable.",
        lang="Language", preset="Demo farmer presets", soil="Soil", weather="Weather", res="Your resources",
        fetch="Fetch local forecast (Open-Meteo)", fetch_ok="Forecast loaded (rainfall is a rough seasonal estimate).",
        fetch_fail="Could not reach the weather service - using manual values.",
        unit="Land unit", land="Available land", water="Water available (m³)", fN="Nitrogen available (kg)",
        fP="Phosphorus available (kg)", fK="Potash available (kg)", budget="Budget (₹)", risk="Risk preference (0 = go for max, 1 = play safe)",
        topk="Crops to consider", maxsh="Max share of land per crop", minsh="Min share of land per crop", useall="Must use all land",
        soilN="Soil N", soilP="Soil P", soilK="Soil K", ph="Soil pH", temp="Temperature (°C)", hum="Humidity (%)", rain="Rainfall (mm)",
        lat="Latitude", lon="Longitude",
        rec="Recommended crops", conf="confidence", plan="Plan to view",
        c_yield="Expected production", c_cost="Estimated cost", c_profit="Expected profit", c_wsave="Water saved vs traditional",
        c_fsave="Fertilizer saved vs traditional", why="Why these crops?",
        good="Good match", warn="Watch out", partial="Conditions are only partly suitable.",
        why_t="{crop}: {good}. Expected yield {y:.1f} t/ha (range {lo:.1f}-{hi:.1f}).", warn_t=" Far from ideal: {bad}.",
        alloc="Land allocation", strat="Strategy comparison", yrange="Yield range (t/ha)", usage="Resource use vs availability",
        whatif="What-if analysis", w_drop="Water drops by (%)", p_drop="Market price drops by (%)",
        s_trad="Traditional equal split", s_ymax="Yield-maximizing", s_pmax="Profit-maximizing (LP)", s_risk="Risk-aware", s_wsave="Water-saving",
        production="Production (t)", revenue="Revenue (₹)", costc="Cost (₹)", profit="Net profit (₹)", waterc="Water used (m³)", fertc="Fertilizer used (kg)",
        budgetc="Budget used (₹)", wsp="Water saving %", fsp="Fertilizer saving %", pgain="Profit gain %",
        area="Area (ha)", crop="Crop", infeasible="No feasible plan with these limits.", relax="Try relaxing",
        r_land="land", r_water="water", r_N="nitrogen", r_P="phosphorus", r_K="potash", r_budget="budget",
        r_diversification="min/max share per crop", r_useall="'must use all land'",
        dl_csv="⬇️ Download plan (CSV)", dl_txt="⬇️ Download summary (TXT)", perf="Model performance", scen="Scenario",
        base="Base", both="Both", edit="Edit crop prices / costs",
    ),
    "te": dict(
        title="🌾 AI పంట & వనరుల ఆప్టిమైజర్", sub="మీ నేల, వాతావరణం, పరిమిత వనరులను బట్టి ఏ పంట ఎంత వేయాలో నిర్ణయించండి.",
        synth="⚠️ డెమోలో కృత్రిమ (SYNTHETIC) డేటా వాడారు. ధరలు, ఖర్చులు సుమారు విలువలు, మార్చుకోవచ్చు.",
        lang="భాష", preset="డెమో రైతు ఉదాహరణలు", soil="నేల", weather="వాతావరణం", res="మీ వనరులు",
        fetch="స్థానిక వాతావరణ అంచనా తీసుకోండి", fetch_ok="అంచనా వచ్చింది (వర్షపాతం సుమారు అంచనా).",
        fetch_fail="వాతావరణ సేవ అందలేదు - మీరు ఇచ్చిన విలువలే వాడుతున్నాం.",
        unit="భూమి కొలత", land="అందుబాటులో ఉన్న భూమి", water="అందుబాటులో నీరు (m³)", fN="నత్రజని అందుబాటు (కేజీ)",
        fP="భాస్వరం అందుబాటు (కేజీ)", fK="పొటాష్ అందుబాటు (కేజీ)", budget="బడ్జెట్ (₹)", risk="రిస్క్ ఎంపిక (0 = గరిష్ఠ లాభం, 1 = భద్రత)",
        topk="పరిశీలించే పంటలు", maxsh="ఒక్క పంటకు గరిష్ఠ భూమి వాటా", minsh="ఒక్క పంటకు కనిష్ఠ భూమి వాటా", useall="మొత్తం భూమి వాడాలి",
        soilN="నేల N", soilP="నేల P", soilK="నేల K", ph="నేల pH", temp="ఉష్ణోగ్రత (°C)", hum="తేమ (%)", rain="వర్షపాతం (మి.మీ)",
        lat="అక్షాంశం", lon="రేఖాంశం",
        rec="సిఫార్సు చేసిన పంటలు", conf="నమ్మకం", plan="చూడాల్సిన ప్లాన్",
        c_yield="అంచనా ఉత్పత్తి", c_cost="అంచనా ఖర్చు", c_profit="అంచనా లాభం", c_wsave="సంప్రదాయ పద్ధతికంటే నీటి ఆదా",
        c_fsave="సంప్రదాయ పద్ధతికంటే ఎరువుల ఆదా", why="ఈ పంటలు ఎందుకు?",
        good="బాగా సరిపోయేవి", warn="జాగ్రత్త", partial="పరిస్థితులు కొంతవరకే అనుకూలం.",
        why_t="{crop}: {good}. అంచనా దిగుబడి {y:.1f} టన్/హె (పరిధి {lo:.1f}-{hi:.1f}).", warn_t=" ఆదర్శానికి దూరం: {bad}.",
        alloc="భూమి కేటాయింపు", strat="వ్యూహాల పోలిక", yrange="దిగుబడి పరిధి (టన్/హె)", usage="వనరుల వినియోగం vs అందుబాటు",
        whatif="ఒకవేళ ఇలా జరిగితే?", w_drop="నీరు తగ్గే శాతం", p_drop="మార్కెట్ ధర తగ్గే శాతం",
        s_trad="సంప్రదాయ సమాన విభజన", s_ymax="గరిష్ఠ దిగుబడి", s_pmax="గరిష్ఠ లాభం (LP)", s_risk="రిస్క్ తగ్గింపు", s_wsave="నీటి పొదుపు",
        production="ఉత్పత్తి (టన్)", revenue="ఆదాయం (₹)", costc="ఖర్చు (₹)", profit="నికర లాభం (₹)", waterc="వాడిన నీరు (m³)", fertc="వాడిన ఎరువు (కేజీ)",
        budgetc="వాడిన బడ్జెట్ (₹)", wsp="నీటి ఆదా %", fsp="ఎరువుల ఆదా %", pgain="లాభ పెరుగుదల %",
        area="విస్తీర్ణం (హె)", crop="పంట", infeasible="ఈ పరిమితులతో సాధ్యమయ్యే ప్లాన్ లేదు.", relax="వీటిని సడలించి చూడండి",
        r_land="భూమి", r_water="నీరు", r_N="నత్రజని", r_P="భాస్వరం", r_K="పొటాష్", r_budget="బడ్జెట్",
        r_diversification="పంటకు కనిష్ఠ/గరిష్ఠ వాటా", r_useall="'మొత్తం భూమి వాడాలి'",
        dl_csv="⬇️ ప్లాన్ డౌన్‌లోడ్ (CSV)", dl_txt="⬇️ సారాంశం డౌన్‌లోడ్ (TXT)", perf="మోడల్ పనితీరు", scen="సందర్భం",
        base="ప్రస్తుతం", both="రెండూ", edit="పంట ధరలు / ఖర్చులు మార్చండి",
    ),
    "hi": dict(
        title="🌾 AI फसल एवं संसाधन अनुकूलक", sub="अपनी मिट्टी, मौसम और सीमित संसाधनों के आधार पर तय करें कि क्या और कितना उगाएँ।",
        synth="⚠️ डेमो में कृत्रिम (SYNTHETIC) डेटा उपयोग हुआ है। कीमतें और लागत अनुमानित हैं, बदली जा सकती हैं।",
        lang="भाषा", preset="डेमो किसान उदाहरण", soil="मिट्टी", weather="मौसम", res="आपके संसाधन",
        fetch="स्थानीय मौसम पूर्वानुमान लाएँ", fetch_ok="पूर्वानुमान मिल गया (वर्षा मोटा अनुमान है)।",
        fetch_fail="मौसम सेवा से संपर्क नहीं हुआ - आपके दिए मान उपयोग हो रहे हैं।",
        unit="भूमि इकाई", land="उपलब्ध भूमि", water="उपलब्ध पानी (m³)", fN="उपलब्ध नाइट्रोजन (किग्रा)",
        fP="उपलब्ध फास्फोरस (किग्रा)", fK="उपलब्ध पोटाश (किग्रा)", budget="बजट (₹)", risk="जोखिम पसंद (0 = अधिकतम, 1 = सुरक्षित)",
        topk="विचार की जाने वाली फसलें", maxsh="प्रति फसल अधिकतम भूमि हिस्सा", minsh="प्रति फसल न्यूनतम भूमि हिस्सा", useall="पूरी भूमि उपयोग करें",
        soilN="मिट्टी N", soilP="मिट्टी P", soilK="मिट्टी K", ph="मिट्टी pH", temp="तापमान (°C)", hum="आर्द्रता (%)", rain="वर्षा (मिमी)",
        lat="अक्षांश", lon="देशांतर",
        rec="अनुशंसित फसलें", conf="विश्वास", plan="देखने के लिए योजना",
        c_yield="अपेक्षित उत्पादन", c_cost="अनुमानित लागत", c_profit="अपेक्षित लाभ", c_wsave="पारंपरिक तरीके से पानी की बचत",
        c_fsave="पारंपरिक तरीके से उर्वरक की बचत", why="ये फसलें क्यों?",
        good="अच्छा मेल", warn="ध्यान दें", partial="परिस्थितियाँ केवल आंशिक रूप से अनुकूल हैं।",
        why_t="{crop}: {good}। अपेक्षित उपज {y:.1f} टन/हे (सीमा {lo:.1f}-{hi:.1f})।", warn_t=" आदर्श से दूर: {bad}।",
        alloc="भूमि आवंटन", strat="रणनीति तुलना", yrange="उपज सीमा (टन/हे)", usage="संसाधन उपयोग बनाम उपलब्धता",
        whatif="अगर ऐसा हुआ तो?", w_drop="पानी घटने का प्रतिशत", p_drop="बाज़ार भाव घटने का प्रतिशत",
        s_trad="पारंपरिक समान बँटवारा", s_ymax="अधिकतम उपज", s_pmax="अधिकतम लाभ (LP)", s_risk="जोखिम-सजग", s_wsave="जल-बचत",
        production="उत्पादन (टन)", revenue="आय (₹)", costc="लागत (₹)", profit="शुद्ध लाभ (₹)", waterc="उपयोग हुआ पानी (m³)", fertc="उपयोग हुआ उर्वरक (किग्रा)",
        budgetc="उपयोग हुआ बजट (₹)", wsp="पानी बचत %", fsp="उर्वरक बचत %", pgain="लाभ वृद्धि %",
        area="क्षेत्रफल (हे)", crop="फसल", infeasible="इन सीमाओं में कोई संभव योजना नहीं।", relax="इन्हें ढीला करके देखें",
        r_land="भूमि", r_water="पानी", r_N="नाइट्रोजन", r_P="फास्फोरस", r_K="पोटाश", r_budget="बजट",
        r_diversification="प्रति फसल न्यूनतम/अधिकतम हिस्सा", r_useall="'पूरी भूमि उपयोग करें'",
        dl_csv="⬇️ योजना डाउनलोड (CSV)", dl_txt="⬇️ सारांश डाउनलोड (TXT)", perf="मॉडल प्रदर्शन", scen="परिदृश्य",
        base="वर्तमान", both="दोनों", edit="फसल भाव / लागत बदलें",
    ),
}

CROP_LOCAL = {
    "te": dict(rice="వరి", maize="మొక్కజొన్న", cotton="పత్తి", chickpea="శనగ", pigeonpea="కంది", groundnut="వేరుశనగ",
               mungbean="పెసర", sorghum="జొన్న", sunflower="పొద్దుతిరుగుడు", soybean="సోయాబీన్"),
    "hi": dict(rice="चावल", maize="मक्का", cotton="कपास", chickpea="चना", pigeonpea="अरहर", groundnut="मूंगफली",
               mungbean="मूंग", sorghum="ज्वार", sunflower="सूरजमुखी", soybean="सोयाबीन"),
}
FEAT_LOCAL = {
    "en": dict(N="Nitrogen", P="Phosphorus", K="Potash", temperature="temperature", humidity="humidity", ph="soil pH", rainfall="rainfall"),
    "te": dict(N="నత్రజని", P="భాస్వరం", K="పొటాష్", temperature="ఉష్ణోగ్రత", humidity="తేమ", ph="నేల pH", rainfall="వర్షపాతం"),
    "hi": dict(N="नाइट्रोजन", P="फास्फोरस", K="पोटाश", temperature="तापमान", humidity="आर्द्रता", ph="मिट्टी pH", rainfall="वर्षा"),
}

# ----------------------------------------------------------------------------
# 3. SESSION DEFAULTS + PRESETS
# ----------------------------------------------------------------------------
DEFAULTS = dict(lang_label="English", soilN=60.0, soilP=45.0, soilK=40.0, ph=6.6, temp=27.0, hum=65.0, rain=100.0,
                lat=17.38, lon=78.48, unit="hectares", land=2.0, water=15000.0, fN=300.0, fP=150.0, fK=120.0,
                budget=120000.0, risk=0.5, topk=4, maxsh=0.6, minsh=0.05, useall=False, plan="pmax")
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

PRESETS = {
    "Small farmer - 2 ha, Telangana, water-scarce year": dict(
        soilN=50.0, soilP=45.0, soilK=40.0, ph=6.8, temp=28.0, hum=60.0, rain=90.0, unit="hectares", land=2.0,
        water=12000.0, fN=250.0, fP=150.0, fK=120.0, budget=100000.0, risk=0.6),
    "Medium farmer - 5 ha, Andhra Pradesh, canal water": dict(
        soilN=80.0, soilP=50.0, soilK=45.0, ph=6.5, temp=27.0, hum=75.0, rain=150.0, unit="hectares", land=5.0,
        water=60000.0, fN=700.0, fP=350.0, fK=250.0, budget=300000.0, risk=0.4),
    "Dryland farmer - 3 ha, low rainfall": dict(
        soilN=40.0, soilP=55.0, soilK=30.0, ph=7.2, temp=26.0, hum=50.0, rain=70.0, unit="hectares", land=3.0,
        water=8000.0, fN=300.0, fP=200.0, fK=100.0, budget=150000.0, risk=0.7),
}


def apply_preset():
    for k, v in PRESETS[st.session_state["preset_sel"]].items():
        st.session_state[k] = v


def fetch_weather():
    try:
        r = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params=dict(latitude=st.session_state["lat"], longitude=st.session_state["lon"],
                        daily="temperature_2m_mean,precipitation_sum,relative_humidity_2m_mean",
                        forecast_days=16, timezone="auto"), timeout=8)
        r.raise_for_status()
        d = r.json()["daily"]
        st.session_state["temp"] = round(float(np.nanmean(d["temperature_2m_mean"])), 1)
        st.session_state["hum"] = round(float(np.nanmean(d["relative_humidity_2m_mean"])), 1)
        st.session_state["rain"] = round(float(np.nansum(d["precipitation_sum"])) * 5, 1)  # rough seasonal estimate
        st.session_state["weather_msg"] = "ok"
    except Exception:
        st.session_state["weather_msg"] = "fail"


# ----------------------------------------------------------------------------
# 4. MODELS (synthetic data, trained once and cached)
# ----------------------------------------------------------------------------
def _sample_env(rng, crop, n, spread):
    cols = []
    for (m, s) in CROPS[crop]["env"]:
        cols.append(rng.normal(m, s * spread, n))
    X = np.column_stack(cols)
    X[:, :3] = np.clip(X[:, :3], 0, None)
    X[:, 4] = np.clip(X[:, 4], 5, 100)
    X[:, 5] = np.clip(X[:, 5], 4, 9.5)
    X[:, 6] = np.clip(X[:, 6], 10, None)
    return X


def _fitness(crop, X):
    z = np.column_stack([(X[:, i] - m) / s for i, (m, s) in enumerate(CROPS[crop]["env"])])
    return np.exp(-0.5 * 0.25 * (z ** 2).mean(axis=1))


@st.cache_resource(show_spinner="Training models on first run...")
def load_models():
    rng = np.random.default_rng(42)
    Xc, yc, Xy, yy = [], [], [], []
    for code, crop in enumerate(CROP_NAMES):
        Xc.append(_sample_env(rng, crop, 500, 1.0)); yc += [crop] * 500
        X = _sample_env(rng, crop, 500, 1.8)
        fit = _fitness(crop, X)
        y = CROPS[crop]["base"] * (0.35 + 0.75 * fit) * rng.lognormal(0, 0.07, len(X))
        Xy.append(np.column_stack([X, np.full(len(X), code)])); yy.append(y)
    Xc = np.vstack(Xc); yc = np.array(yc); Xy = np.vstack(Xy); yy = np.concatenate(yy)

    Xa, Xb, ya, yb = train_test_split(Xc, yc, test_size=0.2, random_state=1, stratify=yc)
    rf = RandomForestClassifier(n_estimators=150, random_state=1, n_jobs=-1).fit(Xa, ya)
    pred = rf.predict(Xb)

    Ya, Yb, za, zb = train_test_split(Xy, yy, test_size=0.2, random_state=1)
    g_mean = GradientBoostingRegressor(n_estimators=150, max_depth=3, random_state=1).fit(Ya, za)
    g_lo = GradientBoostingRegressor(loss="quantile", alpha=0.15, n_estimators=100, max_depth=3, random_state=1).fit(Ya, za)
    g_hi = GradientBoostingRegressor(loss="quantile", alpha=0.85, n_estimators=100, max_depth=3, random_state=1).fit(Ya, za)
    zp = g_mean.predict(Yb)
    return dict(
        rf=rf, g_mean=g_mean, g_lo=g_lo, g_hi=g_hi,
        metrics=dict(acc=accuracy_score(yb, pred), f1=f1_score(yb, pred, average="macro"),
                     mae=mean_absolute_error(zb, zp), r2=r2_score(zb, zp)),
        importance=dict(zip(FEATS, rf.feature_importances_)))


def predict_crops(models, x, k):
    """x = [N,P,K,temp,hum,ph,rain]. Returns DataFrame of top-k crops with yield range."""
    proba = models["rf"].predict_proba(np.array([x]))[0]
    order = np.argsort(proba)[::-1][:k]
    rows = []
    for i in order:
        crop = models["rf"].classes_[i]
        xin = np.array([list(x) + [CROP_NAMES.index(crop)]])
        ym = float(models["g_mean"].predict(xin)[0])
        lo = min(float(models["g_lo"].predict(xin)[0]), ym)
        hi = max(float(models["g_hi"].predict(xin)[0]), ym)
        c = CROPS[crop]
        rows.append(dict(crop=crop, prob=float(proba[i]), y_exp=max(ym, .05), y_low=max(lo, .03), y_high=max(hi, .06),
                         price=c["price"], vol=c["vol"], cost=c["cost"], water=c["water"], N=c["N"], P=c["P"], K=c["K"]))
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------
# 5. OPTIMIZER
# ----------------------------------------------------------------------------
def run_lp(df, cvec, lim, minsh, maxsh, use_all):
    n = len(df)
    keys = ["land", "water", "N", "P", "K", "budget"]
    rows = dict(land=np.ones(n), water=df.water.values, N=df.N.values, P=df.P.values, K=df.K.values, budget=df.cost.values)
    A = np.array([rows[k] for k in keys])
    b = np.array([lim[k] for k in keys], float)
    bounds = [(minsh * lim["land"], maxsh * lim["land"])] * n
    Aeq = [np.ones(n)] if use_all else None
    beq = [lim["land"]] if use_all else None
    return linprog(-np.asarray(cvec, float), A_ub=A, b_ub=b, A_eq=Aeq, b_eq=beq, bounds=bounds, method="highs")


def diagnose(df, cvec, lim, minsh, maxsh, use_all):
    """Which single relaxation makes the problem feasible?"""
    fixes = []
    for k in lim:
        l2 = dict(lim); l2[k] *= 1000
        if run_lp(df, cvec, l2, minsh, maxsh, use_all).status == 0:
            fixes.append(k)
    if run_lp(df, cvec, lim, 0.0, 1.0, use_all).status == 0:
        fixes.append("diversification")
    if use_all and run_lp(df, cvec, lim, minsh, maxsh, False).status == 0:
        fixes.append("useall")
    return fixes


def plan_metrics(df, x):
    x = np.asarray(x, float)
    rev = float((x * df.y_exp * 10 * df.price).sum())
    cost = float((x * df.cost).sum())
    return dict(area=float(x.sum()), production=float((x * df.y_exp).sum()), revenue=rev, cost=cost, profit=rev - cost,
                water=float((x * df.water).sum()), N=float((x * df.N).sum()), P=float((x * df.P).sum()),
                K=float((x * df.K).sum()), fert=float((x * (df.N + df.P + df.K)).sum()))


def build_strategies(df, lim, minsh, maxsh, use_all, risk):
    n = len(df)
    profit_v = df.y_exp * 10 * df.price - df.cost
    out = {}
    # 1) traditional equal split, scaled down if it would break a resource limit
    x = np.full(n, lim["land"] / n)
    use = dict(water=(x * df.water).sum(), N=(x * df.N).sum(), P=(x * df.P).sum(), K=(x * df.K).sum(), budget=(x * df.cost).sum())
    s = min(1.0, *[lim[k] / max(u, 1e-9) for k, u in use.items()])
    out["trad"] = x * s
    # 2) yield max, 3) profit max
    for key, cv in (("ymax", df.y_exp.values), ("pmax", profit_v.values)):
        r = run_lp(df, cv, lim, minsh, maxsh, use_all)
        out[key] = r.x if r.status == 0 else None
    # 4) risk-aware: pessimistic yield blended by risk preference + price-volatility haircut
    y_eff = df.y_exp - risk * (df.y_exp - df.y_low)
    p_eff = df.price * (1 - risk * df.vol)
    r = run_lp(df, (y_eff * 10 * p_eff - df.cost).values, lim, minsh, maxsh, use_all)
    out["risk"] = r.x if r.status == 0 else None
    # 5) water-saving: profit max with only 75% of the water
    l2 = dict(lim); l2["water"] *= 0.75
    r = run_lp(df, profit_v.values, l2, minsh, maxsh, use_all)
    out["wsave"] = r.x if r.status == 0 else None
    return out, profit_v


def what_if(df, lim, minsh, maxsh, use_all, dw, dp):
    l2 = dict(lim); l2["water"] *= (1 - dw)
    d2 = df.copy(); d2["price"] = d2.price * (1 - dp)
    r = run_lp(d2, (d2.y_exp * 10 * d2.price - d2.cost).values, l2, minsh, maxsh, use_all)
    return plan_metrics(d2, r.x) if r.status == 0 else None


def explain(crop, x, y_exp, y_lo, y_hi, lang):
    tr = T[lang]
    z = [(x[i] - m) / s for i, (m, s) in enumerate(CROPS[crop]["env"])]
    fn = FEAT_LOCAL[lang]
    good = [fn[f] for f, zz in zip(FEATS, z) if abs(zz) <= 1.2]
    bad = [fn[f] for f, zz in zip(FEATS, z) if abs(zz) > 2.0]
    name = crop_label(crop, lang)
    msg = tr["why_t"].format(crop=name, good=", ".join(good) if good else tr["partial"], y=y_exp, lo=y_lo, hi=y_hi)
    if bad:
        msg += tr["warn_t"].format(bad=", ".join(bad))
    return msg


def crop_label(c, lang):
    return c.capitalize() if lang == "en" else CROP_LOCAL[lang][c]


def fmt(v):
    return f"{v:,.0f}"


# ----------------------------------------------------------------------------
# 6. UI
# ----------------------------------------------------------------------------
lang = LANGS[st.sidebar.radio("Language / భాష / भाषा", list(LANGS), key="lang_label", horizontal=True)]
tr = T[lang]

st.title(tr["title"])
st.caption(tr["sub"])
st.warning(tr["synth"])

with st.sidebar:
    st.selectbox(tr["preset"], list(PRESETS), key="preset_sel", on_change=apply_preset, index=None, placeholder="—")
    st.subheader("🌱 " + tr["soil"])
    c1, c2, c3 = st.columns(3)
    c1.number_input(tr["soilN"], 0.0, 300.0, key="soilN", step=5.0)
    c2.number_input(tr["soilP"], 0.0, 300.0, key="soilP", step=5.0)
    c3.number_input(tr["soilK"], 0.0, 300.0, key="soilK", step=5.0)
    st.number_input(tr["ph"], 4.0, 9.5, key="ph", step=0.1)

    st.subheader("⛅ " + tr["weather"])
    c1, c2 = st.columns(2)
    c1.number_input(tr["lat"], -90.0, 90.0, key="lat", step=0.1, format="%.2f")
    c2.number_input(tr["lon"], -180.0, 180.0, key="lon", step=0.1, format="%.2f")
    st.button(tr["fetch"], on_click=fetch_weather)
    if st.session_state.get("weather_msg") == "ok":
        st.success(tr["fetch_ok"])
    elif st.session_state.get("weather_msg") == "fail":
        st.info(tr["fetch_fail"])
    st.number_input(tr["temp"], 5.0, 45.0, key="temp", step=0.5)
    st.number_input(tr["hum"], 5.0, 100.0, key="hum", step=1.0)
    st.number_input(tr["rain"], 10.0, 500.0, key="rain", step=5.0)

    st.subheader("🚜 " + tr["res"])
    st.radio(tr["unit"], ["hectares", "acres"], key="unit", horizontal=True)
    st.number_input(tr["land"], 0.1, 1000.0, key="land", step=0.5)
    st.number_input(tr["water"], 0.0, 5_000_000.0, key="water", step=1000.0)
    st.number_input(tr["fN"], 0.0, 100_000.0, key="fN", step=50.0)
    st.number_input(tr["fP"], 0.0, 100_000.0, key="fP", step=50.0)
    st.number_input(tr["fK"], 0.0, 100_000.0, key="fK", step=50.0)
    st.number_input(tr["budget"], 0.0, 100_000_000.0, key="budget", step=10000.0)
    st.slider(tr["risk"], 0.0, 1.0, key="risk", step=0.05)
    st.slider(tr["topk"], 2, 6, key="topk")
    st.slider(tr["maxsh"], 0.3, 1.0, key="maxsh", step=0.05)
    st.slider(tr["minsh"], 0.0, 0.2, key="minsh", step=0.01)
    st.checkbox(tr["useall"], key="useall")

    with st.expander("✏️ " + tr["edit"]):
        edit_df = pd.DataFrame({c: dict(price=v["price"], cost=v["cost"]) for c, v in CROPS.items()}).T
        edited = st.data_editor(edit_df, key="crop_editor")
        for c in CROP_NAMES:
            CROPS[c]["price"] = float(edited.loc[c, "price"])
            CROPS[c]["cost"] = float(edited.loc[c, "cost"])

S = st.session_state
models = load_models()
land_ha = S["land"] * (0.4047 if S["unit"] == "acres" else 1.0)
x_in = [S["soilN"], S["soilP"], S["soilK"], S["temp"], S["hum"], S["ph"], S["rain"]]
lim = dict(land=land_ha, water=S["water"], N=S["fN"], P=S["fP"], K=S["fK"], budget=S["budget"])

# ---- Recommended crops -----------------------------------------------------
df = predict_crops(models, x_in, S["topk"])
st.header("✅ " + tr["rec"])
cols = st.columns(len(df))
for col, (_, r) in zip(cols, df.iterrows()):
    col.metric(crop_label(r.crop, lang), f"{r.prob * 100:.0f}% {tr['conf']}", f"{r.y_exp:.1f} t/ha")
with st.expander("💡 " + tr["why"], expanded=True):
    for _, r in df.iterrows():
        st.write("• " + explain(r.crop, x_in, r.y_exp, r.y_low, r.y_high, lang))

# ---- Optimization ----------------------------------------------------------
plans, profit_v = build_strategies(df, lim, S["minsh"], S["maxsh"], S["useall"], S["risk"])
if plans["pmax"] is None:
    st.error("❌ " + tr["infeasible"])
    fixes = diagnose(df, profit_v.values, lim, S["minsh"], S["maxsh"], S["useall"])
    if fixes:
        st.info(tr["relax"] + ": " + ", ".join(tr["r_" + f] for f in fixes))
    st.stop()

STRAT_KEYS = ["trad", "ymax", "pmax", "risk", "wsave"]
LABEL = {k: tr["s_" + k] for k in STRAT_KEYS}
M = {k: plan_metrics(df, plans[k]) for k in STRAT_KEYS if plans[k] is not None}
trad = M["trad"]


def pct_save(a, b):
    return 100 * (a - b) / a if a > 0 else 0.0


rows = []
for k, m in M.items():
    rows.append({"key": k, "Strategy": LABEL[k], tr["production"]: m["production"], tr["revenue"]: m["revenue"], tr["costc"]: m["cost"],
                 tr["profit"]: m["profit"], tr["waterc"]: m["water"], tr["fertc"]: m["fert"], tr["budgetc"]: m["cost"],
                 tr["pgain"]: 100 * (m["profit"] - trad["profit"]) / abs(trad["profit"]) if trad["profit"] else 0.0,
                 tr["wsp"]: pct_save(trad["water"], m["water"]), tr["fsp"]: pct_save(trad["fert"], m["fert"])})
cmp_df = pd.DataFrame(rows)

st.header("📊 " + tr["strat"])
avail = [k for k in STRAT_KEYS if k in M]
sel = st.radio(tr["plan"], avail, index=avail.index("pmax"), format_func=lambda k: LABEL[k], horizontal=True, key="plan")
m = M[sel]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric(tr["c_yield"], f"{m['production']:.1f} t")
c2.metric(tr["c_cost"], f"₹{fmt(m['cost'])}")
c3.metric(tr["c_profit"], f"₹{fmt(m['profit'])}", f"{cmp_df.set_index('key').loc[sel, tr['pgain']]:+.0f}%")
c4.metric(tr["c_wsave"], f"{pct_save(trad['water'], m['water']):.0f}%")
c5.metric(tr["c_fsave"], f"{pct_save(trad['fert'], m['fert']):.0f}%")

left, right = st.columns(2)
alloc = pd.DataFrame({tr["crop"]: [crop_label(c, lang) for c in df.crop], tr["area"]: plans[sel]})
alloc = alloc[alloc[tr["area"]] > 1e-6]
with left:
    st.subheader(tr["alloc"])
    fig = px.pie(alloc, names=tr["crop"], values=tr["area"], hole=0.4)
    st.plotly_chart(fig, width="stretch")
with right:
    st.subheader(tr["strat"] + " - " + tr["profit"])
    fig = px.bar(cmp_df, x="Strategy", y=tr["profit"], color="Strategy", text_auto=".3s")
    fig.update_layout(showlegend=False, xaxis_title=None)
    st.plotly_chart(fig, width="stretch")

left, right = st.columns(2)
with left:
    st.subheader(tr["yrange"])
    fig = go.Figure(go.Bar(x=[crop_label(c, lang) for c in df.crop], y=df.y_exp,
                           error_y=dict(type="data", symmetric=False, array=df.y_high - df.y_exp, arrayminus=df.y_exp - df.y_low)))
    fig.update_layout(yaxis_title="t/ha")
    st.plotly_chart(fig, width="stretch")
with right:
    st.subheader(tr["usage"])
    used = dict(land=m["area"], water=m["water"], N=m["N"], P=m["P"], K=m["K"], budget=m["cost"])
    usage = pd.DataFrame({"res": [tr["r_" + k] for k in lim], "pct": [100 * used[k] / lim[k] if lim[k] > 0 else 0 for k in lim]})
    fig = px.bar(usage, x="pct", y="res", orientation="h", text_auto=".0f")
    fig.add_vline(x=100, line_dash="dash", line_color="red")
    fig.update_layout(xaxis_title="% of available", yaxis_title=None, xaxis_range=[0, 110])
    st.plotly_chart(fig, width="stretch")

st.dataframe(cmp_df.drop(columns="key").set_index("Strategy").style.format("{:,.1f}"), width="stretch")

# ---- What-if ---------------------------------------------------------------
st.header("🔮 " + tr["whatif"])
w1, w2 = st.columns(2)
dw = w1.slider(tr["w_drop"], 0, 60, 20) / 100
dp = w2.slider(tr["p_drop"], 0, 60, 15) / 100
scen = {tr["base"]: (0, 0), f"{tr['water'].split(' (')[0]} -{dw:.0%}": (dw, 0), f"{tr['p_drop'].split(' (')[0]} -{dp:.0%}": (0, dp), tr["both"]: (dw, dp)}
wi = []
for name, (a, b) in scen.items():
    r = what_if(df, lim, S["minsh"], S["maxsh"], S["useall"], a, b)
    wi.append({tr["scen"]: name, tr["profit"]: r["profit"] if r else np.nan, tr["waterc"]: r["water"] if r else np.nan,
               tr["production"]: r["production"] if r else np.nan})
wi_df = pd.DataFrame(wi)
st.plotly_chart(px.bar(wi_df, x=tr["scen"], y=tr["profit"], text_auto=".3s"), width="stretch")
st.dataframe(wi_df.set_index(tr["scen"]).style.format("{:,.1f}"), width="stretch")

# ---- Downloads -------------------------------------------------------------
st.header("📥 " + tr["dl_csv"].replace("⬇️ ", ""))
plan_df = df[["crop", "prob", "y_exp", "y_low", "y_high", "price", "cost", "water"]].copy()
plan_df["area_ha"] = plans[sel]
plan_df["strategy"] = sel
csv = plan_df.to_csv(index=False).encode("utf-8-sig")
summary = "\n".join([
    "CROP & RESOURCE OPTIMIZATION PLAN (synthetic-data demo)", f"Strategy: {LABEL[sel]}", f"Land: {land_ha:.2f} ha",
    *[f"- {crop_label(c, 'en')}: {a:.2f} ha" for c, a in zip(df.crop, plans[sel]) if a > 1e-6],
    f"Production: {m['production']:.1f} t", f"Revenue: Rs {fmt(m['revenue'])}", f"Cost: Rs {fmt(m['cost'])}", f"Net profit: Rs {fmt(m['profit'])}",
    f"Water used: {fmt(m['water'])} m3 ({pct_save(trad['water'], m['water']):.0f}% saved vs traditional)",
    f"Fertilizer used: {fmt(m['fert'])} kg ({pct_save(trad['fert'], m['fert']):.0f}% saved vs traditional)",
    "Note: prices/costs are approximate defaults; yields come from a model trained on synthetic data."])
d1, d2 = st.columns(2)
d1.download_button(tr["dl_csv"], csv, "my_crop_plan.csv", "text/csv")
d2.download_button(tr["dl_txt"], summary.encode("utf-8"), "my_crop_plan.txt", "text/plain")

with st.expander("🧪 " + tr["perf"]):
    mt = models["metrics"]
    a, b, c, d = st.columns(4)
    a.metric("Accuracy", f"{mt['acc']:.2f}"); b.metric("F1 (macro)", f"{mt['f1']:.2f}")
    c.metric("Yield MAE (t/ha)", f"{mt['mae']:.2f}"); d.metric("Yield R²", f"{mt['r2']:.2f}")
    imp = pd.DataFrame({"feature": list(models["importance"]), "importance": list(models["importance"].values())})
    st.plotly_chart(px.bar(imp.sort_values("importance"), x="importance", y="feature", orientation="h"), width="stretch")
