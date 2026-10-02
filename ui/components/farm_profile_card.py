"""
FarmTwin UI Component — Farm Profile Card.

Renders validated farm profile summary cards and unit normalization comparisons.
"""
from typing import Any
import streamlit as st
from engine.profile import FarmProfile, LandUnit, WaterUnit


def render_farm_profile_card(profile: FarmProfile) -> None:
    """
    Renders a structured, farmer-friendly summary of the validated Farm Profile.
    Highlights unit normalization (e.g. acres -> hectares, m³ -> liters).
    """
    st.markdown("### 📋 Validated Farm Profile Summary")
    
    if profile.is_demo:
        st.warning("⚠️ **DEMO / TEST PROFILE**: Values shown below are synthetic test data and do not represent a real farm.")

    # 1. Identity & Location Banner
    col_id, col_loc, col_strat = st.columns(3)
    with col_id:
        st.metric("Farm Identifier", profile.farm_id)
        if profile.farmer_name:
            st.caption(f"Operator: **{profile.farmer_name}**")
        else:
            st.caption("Operator: Not specified")

    with col_loc:
        loc_str = f"{profile.district or '—'}, {profile.state or '—'}"
        st.metric("Location", loc_str)
        if profile.latitude is not None and profile.longitude is not None:
            st.caption(f"Coords: {profile.latitude:.4f}°, {profile.longitude:.4f}°")
        else:
            st.caption("Coords: Not provided")

    with col_strat:
        st.metric("Season & Horizon", f"{profile.season.value.capitalize()} {profile.year}")
        st.caption(f"Risk Preference: **{profile.risk_tolerance * 100:.0f}%** tolerance")

    st.markdown("---")

    # 2. Key Resource Metrics with Unit Normalization
    col_land, col_water, col_budget, col_labour = st.columns(4)

    with col_land:
        st.markdown("#### 🌾 Land")
        st.metric("Normalized Land", f"{profile.land_area_ha:,.3f} ha")
        if profile.land_unit == LandUnit.ACRE:
            st.info(f"**Entered:** {profile.original_land_area:,.2f} acres\n\n**Normalized:** {profile.land_area_ha:,.3f} hectares")
        else:
            st.caption(f"Entered as: {profile.original_land_area:,.2f} hectares")

    with col_water:
        st.markdown("#### 💧 Water")
        st.metric("Normalized Water", f"{profile.water_liters:,.0f} L")
        if profile.water_unit == WaterUnit.M3:
            st.info(f"**Entered:** {profile.original_water_amount:,.1f} m³\n\n**Normalized:** {profile.water_liters:,.0f} liters")
        else:
            st.caption(f"Entered as: {profile.original_water_amount:,.0f} liters")

    with col_budget:
        st.markdown("#### 💰 Budget")
        st.metric("Working Capital", f"₹{profile.available_budget_inr:,.0f}")
        st.caption("Internal currency: INR")

    with col_labour:
        st.markdown("#### 👥 Labour")
        st.metric("Available Labour", f"{profile.available_labour_days:,.0f} days")
        st.caption("Total person-days")

    st.markdown("---")

    # 3. Soil & Weather Status
    col_soil, col_weather = st.columns(2)

    with col_soil:
        st.markdown("#### 🧪 Soil Nutrient State")
        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Nitrogen (N)", f"{profile.nitrogen_n_kg_ha:.1f} kg/ha")
        s2.metric("Phosphorus (P)", f"{profile.phosphorus_p_kg_ha:.1f} kg/ha")
        s3.metric("Potassium (K)", f"{profile.potassium_k_kg_ha:.1f} kg/ha")
        s4.metric("pH Level", f"{profile.ph:.1f}")

        st.caption(
            f"Fertilizer inventory available: N: {profile.available_n_kg:.0f} kg | "
            f"P: {profile.available_p_kg:.0f} kg | K: {profile.available_k_kg:.0f} kg"
        )

    with col_weather:
        st.markdown("#### ⛅ Observed Environment")
        w1, w2, w3 = st.columns(3)
        w1.metric("Temperature", f"{profile.temperature_c:.1f} °C")
        w2.metric("Humidity", f"{profile.humidity_percent:.0f} %")
        w3.metric("Rainfall", f"{profile.rainfall_mm:.1f} mm")
        st.caption("Baseline observed climate conditions for profile")
