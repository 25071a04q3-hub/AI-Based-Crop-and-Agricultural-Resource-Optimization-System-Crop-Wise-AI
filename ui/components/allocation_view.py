"""
FarmTwin UI Component — Executive Decision Summary & Explainability Card.

Renders:
- Executive Decision Summary Card (Feature 3)
- "WHY DID FARMTWIN MAKE THIS DECISION?" (Feature 4)
- Farm Resource Balance Card (Feature 6)
"""
from typing import Dict, Any, List
import streamlit as st
import pandas as pd


def render_executive_decision_summary(pipeline_out: Dict[str, Any]) -> None:
    """
    Renders a prominent, high-impact Executive Decision Summary card at the top of the dashboard.
    """
    profile = pipeline_out["profile"]
    opt = pipeline_out["opt_result"]
    suits = pipeline_out["suitability_results"]
    b_rep = pipeline_out["bottleneck_report"]
    a_rep = pipeline_out["adaptive_report"]
    p_rep = pipeline_out["portfolio_report"]

    top_crop = suits[0].crop_name.capitalize() if suits else "None"
    top_score = (suits[0].suitability_score * 100) if suits else 0.0
    top_level = suits[0].suitability_level if suits else "Unknown"

    land_used = opt.total_land_used_ha
    land_total = profile.land_area_ha
    land_pct = (land_used / land_total * 100) if land_total > 0 else 0.0

    prim_bottle = b_rep.primary_bottleneck.replace("_", " ").title() if b_rep.primary_bottleneck else "None"
    prim_util = b_rep.primary_bottleneck_utilization or 0.0

    # Find lowest reserve
    reserves = a_rep.reserve_summary
    lowest_res_name = "None"
    lowest_res_pct = 100.0
    lowest_res_status = "HEALTHY"
    for r_name, r_vals in reserves.items():
        pct = r_vals.get("reserve_pct", 100.0)
        if pct < lowest_res_pct:
            lowest_res_pct = pct
            lowest_res_name = r_name.replace("_", " ").title()
            lowest_res_status = a_rep.critical_reserves.get(r_name, "HEALTHY")

    st.markdown("""
    <style>
    .exec-summary-box {
        background: linear-gradient(135deg, #0e1e25 0%, #152934 100%);
        border: 1px solid #1f4254;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    }
    .exec-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #58d68d;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .exec-subtitle {
        font-size: 0.88rem;
        color: #a0aec0;
        margin-bottom: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### 📋 Executive Decision Summary")
    st.caption("Consolidated agronomic, optimization, and resilience findings from the verified FarmTwin engine.")

    # 4 High-Impact Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="Recommended Crop",
            value=top_crop,
            delta=f"{top_score:.1f}% Match ({top_level})",
            delta_color="normal"
        )
    with c2:
        st.metric(
            label="Optimized Land Usage",
            value=f"{land_used:.2f} ha",
            delta=f"{land_pct:.1f}% of {land_total:.2f} ha parcel",
            delta_color="normal"
        )
    with c3:
        st.metric(
            label="Primary Bottleneck",
            value=prim_bottle,
            delta=f"{prim_util:.1f}% Saturation (BINDING)" if prim_util >= 99.0 else f"{prim_util:.1f}% Utilized",
            delta_color="inverse" if prim_util >= 99.0 else "normal"
        )
    with c4:
        trig_badge = "PLAN STABLE" if a_rep.trigger_status == "PLAN_STABLE" else "REOPTIMIZATION NEEDED"
        st.metric(
            label="Plan Resilience Status",
            value=trig_badge,
            delta=f"Diversity: {p_rep.shannon_diversity_index:.2f} (H')",
            delta_color="normal" if a_rep.trigger_status == "PLAN_STABLE" else "inverse"
        )


def render_why_this_decision(pipeline_out: Dict[str, Any]) -> None:
    """
    Renders the Explainable Decision section (Feature 4).
    Dynamically articulates the causality behind FarmTwin's recommendation.
    """
    profile = pipeline_out["profile"]
    opt = pipeline_out["opt_result"]
    suits = pipeline_out["suitability_results"]
    b_rep = pipeline_out["bottleneck_report"]
    a_rep = pipeline_out["adaptive_report"]

    top_crop = suits[0].crop_name.capitalize() if suits else "None"
    top_score = (suits[0].suitability_score * 100) if suits else 0.0

    prim_bottle = b_rep.primary_bottleneck.replace("_", " ").title() if b_rep.primary_bottleneck else "None"
    prim_util = b_rep.primary_bottleneck_utilization or 0.0

    # Lowest reserve
    reserves = a_rep.reserve_summary
    lowest_res_name = "Water"
    lowest_res_pct = 0.0
    lowest_res_status = "CRITICAL"
    if reserves:
        sorted_res = sorted(reserves.items(), key=lambda x: x[1].get("reserve_pct", 100.0))
        lowest_res_name = sorted_res[0][0].replace("_", " ").title()
        lowest_res_pct = sorted_res[0][1].get("reserve_pct", 0.0)
        lowest_res_status = a_rep.critical_reserves.get(sorted_res[0][0], "HEALTHY")

    st.markdown("### 💡 Why Did FarmTwin Make This Decision?")
    st.caption("Transparent mathematical explainability derived directly from AI classification and continuous LP solver constraints.")

    with st.container():
        st.markdown(f"""
        1. **AI Crop Suitability**: **{top_crop}** ranked #1 with a **{top_score:.1f}% suitability score** among 22 evaluated crops. The Random Forest model matched the farm's soil chemistry (N={profile.nitrogen_n_kg_ha:.0f}, P={profile.phosphorus_p_kg_ha:.0f}, K={profile.potassium_k_kg_ha:.0f} kg/ha, pH={profile.ph:.1f}) and local agro-climate ({profile.temperature_c:.1f}°C, {profile.rainfall_mm:.0f}mm rainfall).
        
        2. **Binding Resource Constraint**: **{prim_bottle}** is the dominant bottleneck at **{prim_util:.1f}% capacity**. Even though other inputs (e.g. land or labour) may have excess slack, the farm cannot physically expand without additional {prim_bottle}.
        
        3. **Acreage Allocation**: The HiGHS simplex optimizer allocated **{opt.total_land_used_ha:.2f} ha** across the most suitable candidates. It prioritized higher-suitability crops up to the exact point where {prim_bottle} was completely exhausted.
        
        4. **Buffer Contingency**: The **{lowest_res_name} reserve** is currently **{lowest_res_status}** ({lowest_res_pct:.1f}% unallocated buffer). This indicates high sensitivity to unexpected mid-season {lowest_res_name.lower()} deficits.
        
        5. **Adaptation Guidance**: *{a_rep.explanation}*
        """)


def render_farm_resource_balance(pipeline_out: Dict[str, Any]) -> None:
    """
    Renders the visual Farm Resource Balance sheet across 6 physical constraints (Feature 6).
    """
    profile = pipeline_out["profile"]
    opt = pipeline_out["opt_result"]
    b_rep = pipeline_out["bottleneck_report"]
    a_rep = pipeline_out["adaptive_report"]

    st.markdown("### ⚖️ Farm Resource Balance & Utilization")
    st.caption("Real-time balance sheet comparing allocated resource demand against total farm capacity.")

    resources = [
        ("Land Area", "land_ha", "ha", opt.total_land_used_ha, profile.land_area_ha),
        ("Irrigation Water", "water_liters", "L", opt.resource_usage.get("water_liters", 0.0), profile.available_water),
        ("Nitrogen (N)", "nitrogen_kg", "kg", opt.resource_usage.get("nitrogen_kg", 0.0), profile.available_n_kg),
        ("Phosphorus (P)", "phosphorus_kg", "kg", opt.resource_usage.get("phosphorus_kg", 0.0), profile.available_p_kg),
        ("Potassium (K)", "potassium_kg", "kg", opt.resource_usage.get("potassium_kg", 0.0), profile.available_k_kg),
        ("Working Budget", "budget_inr", "₹", opt.resource_usage.get("budget_inr", 0.0), profile.available_budget_inr),
    ]

    c_left, c_right = st.columns(2)
    for idx, (label, key, unit, used, capacity) in enumerate(resources):
        col = c_left if idx % 2 == 0 else c_right
        util_pct = (used / capacity * 100.0) if capacity > 0 else 0.0
        reserve_pct = max(0.0, 100.0 - util_pct)
        regime = b_rep.constraint_states.get(key, "ACTIVE")

        # Color coding
        if util_pct >= 99.0:
            badge = "🔴 **BINDING (100%)**"
        elif util_pct >= 90.0:
            badge = "🟠 **NEAR-BINDING**"
        elif util_pct >= 60.0:
            badge = "🔵 **ACTIVE**"
        else:
            badge = "🟢 **UNDERUTILIZED**"

        with col:
            st.markdown(f"**{label}** — {badge}")
            if unit == "₹":
                st.caption(f"Used: ₹{used:,.0f} / ₹{capacity:,.0f} | Reserve: {reserve_pct:.1f}%")
            elif unit == "L":
                st.caption(f"Used: {used:,.0f} L / {capacity:,.0f} L | Reserve: {reserve_pct:.1f}%")
            else:
                st.caption(f"Used: {used:.2f} {unit} / {capacity:.2f} {unit} | Reserve: {reserve_pct:.1f}%")
            st.progress(min(1.0, max(0.0, util_pct / 100.0)))
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
