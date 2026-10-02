"""
FarmTwin — Risk-Aware Adaptive Farm Decision Engine.
Phase 2: Farm Profile & Input Validation Dashboard.
"""
from typing import Optional
import streamlit as st
from pydantic import ValidationError

from engine.profile import (
    FarmProfile,
    LandUnit,
    WaterUnit,
    Season,
    get_demo_farm_profile,
    format_validation_errors,
)
from engine.crop_suitability import (
    predict_crop_suitability,
    get_or_train_suitability_model,
)
from engine.yield_prediction import predict_yield
from ui.components.farm_profile_card import render_farm_profile_card
from ui.components.crop_suitability_card import render_crop_suitability_results
from ui.components.yield_prediction_card import render_yield_prediction_card
from ui.components.scenario_simulator_card import render_scenario_simulator_card
from ui.components.resource_calculation_card import render_resource_calculation_card
from ui.components.optimizer_card import render_optimizer_card
from ui.components.portfolio_intelligence_card import render_portfolio_intelligence_card
from ui.components.bottleneck_analysis_card import render_bottleneck_analysis_card
from ui.components.adaptive_reserve_card import render_adaptive_reserve_card

st.set_page_config(
    page_title="FarmTwin — Farm Profile & Validation",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 FarmTwin")
st.subheader("Risk-Aware Adaptive Farm Decision Engine — Farm Profile")
st.caption("Phase 2: Validated Single Source of Truth for Farm Parcels and Operational Resources")

# -----------------------------------------------------------------------------
# Demo Profile Loader
# -----------------------------------------------------------------------------
if "profile_data" not in st.session_state:
    st.session_state["profile_data"] = {}

col_btn1, col_btn2 = st.columns([2, 8])
with col_btn1:
    if st.button("📥 Load Demo Profile (FARM-001)"):
        demo = get_demo_farm_profile()
        st.session_state["profile_data"] = demo.model_dump()
        st.session_state["submitted_profile"] = demo
        st.rerun()

with col_btn2:
    if st.session_state["profile_data"].get("is_demo"):
        st.info("ℹ️ Currently displaying DEMO profile (Telangana, 2 ha, Kharif).")

# Fetch default values from session state if available
defaults = st.session_state.get("profile_data", {})

# -----------------------------------------------------------------------------
# Farm Profile Input Form
# -----------------------------------------------------------------------------
with st.form("farm_profile_form"):
    st.markdown("### 1. Farm Identity & Location")
    c1, c2, c3, c4 = st.columns(4)
    farm_id = c1.text_input(
        "Farm ID *",
        value=defaults.get("farm_id", "FARM-001"),
        help="Unique parcel identifier"
    )
    farmer_name = c2.text_input(
        "Farmer / Operator Name",
        value=defaults.get("farmer_name", "Demo Farmer"),
        help="Optional non-sensitive identification"
    )
    state = c3.text_input(
        "State",
        value=defaults.get("state", "Telangana")
    )
    district = c4.text_input(
        "District",
        value=defaults.get("district", "Hyderabad")
    )

    c_lat, c_lon, _ = st.columns([2, 2, 4])
    latitude = c_lat.number_input(
        "Latitude (°)",
        min_value=-90.0,
        max_value=90.0,
        value=float(defaults.get("latitude", 17.3850)),
        step=0.0001,
        format="%.4f"
    )
    longitude = c_lon.number_input(
        "Longitude (°)",
        min_value=-180.0,
        max_value=180.0,
        value=float(defaults.get("longitude", 78.4867)),
        step=0.0001,
        format="%.4f"
    )

    st.markdown("### 2. Operational Land")
    c_land_val, c_land_unit = st.columns([3, 2])
    land_area = c_land_val.number_input(
        "Total Available Land Area *",
        min_value=0.0,
        value=float(defaults.get("land_area", 2.0)),
        step=0.5,
        format="%.2f",
        help="Must be greater than 0"
    )
    land_unit_idx = 1 if defaults.get("land_unit") in (LandUnit.ACRE, "acre") else 0
    land_unit = c_land_unit.selectbox(
        "Land Unit",
        options=["hectare", "acre"],
        index=land_unit_idx,
        help="1 hectare = 2.47105 acres | 1 acre = 0.404686 hectare"
    )

    st.markdown("### 3. Soil Nutrient Analysis")
    c_sn, c_sp, c_sk, c_ph = st.columns(4)
    soil_n = c_sn.number_input(
        "Nitrogen (N) kg/ha",
        min_value=0.0,
        value=float(defaults.get("nitrogen_n_kg_ha", 80.0)),
        step=5.0
    )
    soil_p = c_sp.number_input(
        "Phosphorus (P) kg/ha",
        min_value=0.0,
        value=float(defaults.get("phosphorus_p_kg_ha", 40.0)),
        step=5.0
    )
    soil_k = c_sk.number_input(
        "Potassium (K) kg/ha",
        min_value=0.0,
        value=float(defaults.get("potassium_k_kg_ha", 50.0)),
        step=5.0
    )
    soil_ph = c_ph.number_input(
        "Soil pH",
        min_value=0.0,
        max_value=14.0,
        value=float(defaults.get("ph", 6.8)),
        step=0.1
    )

    st.markdown("### 4. Observed Climate / Environment")
    c_temp, c_hum, c_rain = st.columns(3)
    temperature = c_temp.number_input(
        "Temperature (°C)",
        min_value=-20.0,
        max_value=60.0,
        value=float(defaults.get("temperature_c", 28.0)),
        step=0.5
    )
    humidity = c_hum.number_input(
        "Relative Humidity (%)",
        min_value=0.0,
        max_value=100.0,
        value=float(defaults.get("humidity_percent", 65.0)),
        step=1.0
    )
    rainfall = c_rain.number_input(
        "Seasonal Rainfall (mm)",
        min_value=0.0,
        value=float(defaults.get("rainfall_mm", 100.0)),
        step=5.0
    )

    st.markdown("### 5. Water & Fertilizer Resource Inventories")
    c_wat_val, c_wat_unit = st.columns([3, 2])
    available_water = c_wat_val.number_input(
        "Usable Irrigation Water",
        min_value=0.0,
        value=float(defaults.get("available_water", 100000.0)),
        step=5000.0
    )
    water_unit_idx = 1 if defaults.get("water_unit") in (WaterUnit.M3, "m3") else 0
    water_unit = c_wat_unit.selectbox(
        "Water Unit",
        options=["liter", "m3"],
        index=water_unit_idx,
        help="1 m³ = 1,000 liters"
    )

    c_fn, c_fp, c_fk = st.columns(3)
    fert_n = c_fn.number_input(
        "Available N Fertilizer (kg)",
        min_value=0.0,
        value=float(defaults.get("available_n_kg", 160.0)),
        step=10.0
    )
    fert_p = c_fp.number_input(
        "Available P Fertilizer (kg)",
        min_value=0.0,
        value=float(defaults.get("available_p_kg", 80.0)),
        step=10.0
    )
    fert_k = c_fk.number_input(
        "Available K Fertilizer (kg)",
        min_value=0.0,
        value=float(defaults.get("available_k_kg", 100.0)),
        step=10.0
    )

    st.markdown("### 6. Economics, Labour & Strategy")
    c_bud, c_lab, c_seas, c_yr = st.columns(4)
    budget = c_bud.number_input(
        "Working Capital Budget (₹)",
        min_value=0.0,
        value=float(defaults.get("available_budget_inr", 100000.0)),
        step=5000.0
    )
    labour_days = c_lab.number_input(
        "Available Labour (person-days)",
        min_value=0.0,
        value=float(defaults.get("available_labour_days", 100.0)),
        step=5.0
    )
    season_options = ["kharif", "rabi", "zaid"]
    default_season = defaults.get("season", "kharif")
    season_idx = season_options.index(default_season.value if isinstance(default_season, Season) else str(default_season).lower())
    season = c_seas.selectbox("Season", options=season_options, index=season_idx)
    year = int(c_yr.number_input("Year", min_value=2000, max_value=2100, value=int(defaults.get("year", 2026)), step=1))

    risk_tolerance = st.slider(
        "Risk Preference (0.0 = High Aversion to Ruin, 1.0 = High Risk Tolerance)",
        min_value=0.0,
        max_value=1.0,
        value=float(defaults.get("risk_tolerance", 0.5)),
        step=0.05
    )

    submit_button = st.form_submit_button("✅ Validate & Save Farm Profile", type="primary")

# -----------------------------------------------------------------------------
# Form Processing & Validation Handling
# -----------------------------------------------------------------------------
if submit_button:
    raw_payload = {
        "farm_id": farm_id,
        "farmer_name": farmer_name,
        "state": state,
        "district": district,
        "latitude": latitude,
        "longitude": longitude,
        "land_area": land_area,
        "land_unit": land_unit,
        "nitrogen_n_kg_ha": soil_n,
        "phosphorus_p_kg_ha": soil_p,
        "potassium_k_kg_ha": soil_k,
        "ph": soil_ph,
        "temperature_c": temperature,
        "humidity_percent": humidity,
        "rainfall_mm": rainfall,
        "available_water": available_water,
        "water_unit": water_unit,
        "available_n_kg": fert_n,
        "available_p_kg": fert_p,
        "available_k_kg": fert_k,
        "available_budget_inr": budget,
        "available_labour_days": labour_days,
        "season": season,
        "year": year,
        "risk_tolerance": risk_tolerance,
        "is_demo": False,
    }

    try:
        profile = FarmProfile(**raw_payload)
        st.session_state["submitted_profile"] = profile
        st.session_state["profile_data"] = profile.model_dump()
        st.session_state["validation_errors"] = []
    except ValidationError as exc:
        st.session_state["submitted_profile"] = None
        st.session_state["validation_errors"] = format_validation_errors(exc)

# -----------------------------------------------------------------------------
# Display Validation Results
# -----------------------------------------------------------------------------
errors = st.session_state.get("validation_errors", [])
if errors:
    st.error("❌ **Validation Failed:** Please resolve the following issues:")
    for err in errors:
        st.write(f"• {err}")

profile: Optional[FarmProfile] = st.session_state.get("submitted_profile")
if profile is not None:
    st.success("✅ **Farm Profile Valid** — Operational parameters validated and normalized.")
    render_farm_profile_card(profile)

    with st.expander("🔍 View Normalized Data Contract (JSON)", expanded=False):
        st.json(profile.to_normalized())

    # -------------------------------------------------------------------------
    # Phase 3: AI Crop Suitability Prediction Section
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("## 🌾 Phase 3: AI Crop Suitability Analysis")
    st.caption("Evaluate which candidate crops match this farm parcel's soil chemistry and climatic conditions.")

    c_top, c_act = st.columns([3, 7])
    top_n = c_top.slider("Number of Top Suitable Crops to Display", min_value=3, max_value=10, value=5)
    analyze_btn = c_act.button("🔮 Analyze Crop Suitability", type="primary")

    if analyze_btn or "suitability_results" in st.session_state:
        if analyze_btn:
            with st.spinner("Executing Random Forest crop suitability evaluation..."):
                model, model_metrics = get_or_train_suitability_model()
                suitability_results = predict_crop_suitability(profile, model=model)
                st.session_state["suitability_results"] = suitability_results
                st.session_state["suitability_metrics"] = model_metrics

        if "suitability_results" in st.session_state:
            render_crop_suitability_results(
                results=st.session_state["suitability_results"],
                model_metrics=st.session_state.get("suitability_metrics", {}),
                top_n=top_n
            )

            # -----------------------------------------------------------------
            # Phase 4: Probabilistic Crop Yield Prediction Section
            # -----------------------------------------------------------------
            st.markdown("---")
            st.markdown("## 📈 Phase 4: Probabilistic Crop Yield Prediction")
            st.caption("Estimate lower (P10), median expected (P50), and upper (P90) yield distributions under farm conditions.")

            suit_list = st.session_state["suitability_results"]
            crop_options = [r.crop_name for r in suit_list]

            c_crop_sel, c_info = st.columns([4, 6])
            selected_crop = c_crop_sel.selectbox(
                "Select Suitable Crop for Yield Estimation",
                options=crop_options,
                format_func=lambda x: x.capitalize(),
                help="Select from crops evaluated by AI Crop Suitability (Phase 3)"
            )

            # Retrieve suitability result for context/warning
            matching_suit = next((r for r in suit_list if r.crop_name == selected_crop), None)

            yield_result = predict_yield(profile=profile, crop_name=selected_crop)
            render_yield_prediction_card(yield_result=yield_result, suitability_result=matching_suit)

            # -----------------------------------------------------------------
            # Phase 5: Future Scenario Simulator Section
            # -----------------------------------------------------------------
            st.markdown("---")
            st.markdown("## 🔮 Phase 5: Future Scenario Simulator & Farm Stress Testing")
            st.caption("Stress-test the farm profile across single or multiple climate and macroeconomic futures.")

            render_scenario_simulator_card(profile=profile, selected_crop=selected_crop)

            # -----------------------------------------------------------------
            # Phase 6: Resource Calculation Engine Section
            # -----------------------------------------------------------------
            st.markdown("---")
            st.markdown("## ⚖️ Phase 6: Resource Requirement & Balance Engine")
            st.caption("Deterministic resource demand accounting and farm inventory feasibility evaluation.")

            render_resource_calculation_card(profile=profile, default_crop=selected_crop)

            # -----------------------------------------------------------------
            # Phase 7: Risk-Aware Farm Optimization Engine Section
            # -----------------------------------------------------------------
            st.markdown("---")
            st.markdown("## 🎯 Phase 7: Risk-Aware Farm Optimization Engine")
            st.caption("Continuous linear programming allocation of farm land and scarce resources.")

            render_optimizer_card(profile=profile, candidate_crops=st.session_state.get("suitability_results"))

            # -----------------------------------------------------------------
            # Phase 8: Crop Portfolio & Soil Rotation Intelligence Section
            # -----------------------------------------------------------------
            st.markdown("---")
            st.markdown("## 🌾 Phase 8: Crop Portfolio & Soil Rotation Intelligence")
            st.caption("Evaluate portfolio diversity, soil sustainability, and scenario stress resilience.")

            render_portfolio_intelligence_card(
                optimization_result=st.session_state.get("phase7_result"),
                scenario_results=st.session_state.get("phase7_scenarios"),
            )

            # -----------------------------------------------------------------
            # Phase 9: Bottleneck Analysis & Shadow Value Intelligence Section
            # -----------------------------------------------------------------
            st.markdown("---")
            st.markdown("## 🔍 Phase 9: Bottleneck Analysis & Shadow Value Intelligence")
            st.caption("Diagnose binding resource ceilings, analyze dual shadow values, and evaluate What-If resource levers.")

            render_bottleneck_analysis_card(
                optimization_result=st.session_state.get("phase7_result"),
                farm_profile=profile,
                candidate_crops=st.session_state.get("suitability_results"),
            )

            # -----------------------------------------------------------------
            # Phase 10: Adaptive Reserve & Mid-Season Re-Optimization Section
            # -----------------------------------------------------------------
            st.markdown("---")
            st.markdown("## 🛡️ Phase 10: Adaptive Reserve & Mid-Season Re-Optimization")
            st.caption("Contingency buffer auditing, re-optimization trigger boundaries, and mid-season recourse simulation.")

            render_adaptive_reserve_card(
                optimization_result=st.session_state.get("phase7_result"),
                farm_profile=profile,
                candidate_crops=st.session_state.get("suitability_results"),
                scenario_results=st.session_state.get("phase7_scenarios"),
            )

st.markdown("""
---
*FarmTwin decision pipeline: Crop Suitability (Phase 3), Probabilistic Yield (Phase 4), Future Scenario Simulator (Phase 5), Resource Balance (Phase 6), Risk-Aware Optimizer (Phase 7), Portfolio & Soil Intelligence (Phase 8), Bottleneck Analysis (Phase 9), and Adaptive Reserve & Re-Optimization (Phase 10) enabled.*
""")
