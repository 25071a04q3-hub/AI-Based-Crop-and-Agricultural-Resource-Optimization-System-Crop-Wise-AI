"""
FarmTwin — Risk-Aware Adaptive Farm Decision Engine.
Jury-Ready Demonstration Dashboard & Decision Intelligence Platform.
"""
from typing import Optional, Dict, Any
import streamlit as st
import pandas as pd
from pydantic import ValidationError

from engine.profile import (
    FarmProfile,
    LandUnit,
    WaterUnit,
    Season,
    format_validation_errors,
)
from ui.presets import (
    DEMO_PRESETS,
    get_preset_profile,
    execute_full_decision_pipeline,
)
from ui.components.allocation_view import (
    render_executive_decision_summary,
    render_why_this_decision,
    render_farm_resource_balance,
)
from ui.components.crop_suitability_card import render_crop_suitability_results
from ui.components.what_if_simulator import render_what_if_simulator
from ui.components.bottleneck_analysis_card import render_bottleneck_analysis_card
from ui.components.adaptive_reserve_card import render_adaptive_reserve_card
from ui.components.portfolio_intelligence_card import render_portfolio_intelligence_card
from ui.components.scenario_simulator_card import render_scenario_simulator_card
from ui.components.optimizer_card import render_optimizer_card
from ui.components.resource_calculation_card import render_resource_calculation_card
from ui.components.yield_prediction_card import render_yield_prediction_card
from ui.components.farm_profile_card import render_farm_profile_card

# -----------------------------------------------------------------------------
# Streamlit App Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="FarmTwin — Adaptive Farm Decision Engine",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------------------------------------------------------
# Global Styling
# -----------------------------------------------------------------------------
st.markdown("""
<style>
.badge-active {
    background-color: #1b4d3e;
    color: #58d68d;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    display: inline-block;
    border: 1px solid #27ae60;
}
.badge-gated {
    background-color: #4a3b10;
    color: #f39c12;
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.78rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    display: inline-block;
    border: 1px solid #d68910;
}
.arch-step {
    background-color: #1a202c;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: center;
    font-size: 0.82rem;
    color: #e2e8f0;
    font-weight: 600;
}
.hero-card {
    background: linear-gradient(135deg, #101e2b 0%, #172d3e 100%);
    border: 1px solid #244b67;
    border-radius: 12px;
    padding: 18px 24px;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Feature 1: Jury-Friendly Header & Status Area
# -----------------------------------------------------------------------------
st.markdown("# 🌱 FARMTWIN")
st.markdown("### Adaptive Farm Decision Engine")
st.markdown("*From farm conditions to resource-aware, stress-tested decisions.*")

# Status badges
b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns(5)
with b_col1:
    st.markdown('<span class="badge-active">● AI SUITABILITY: ACTIVE</span>', unsafe_allow_html=True)
with b_col2:
    st.markdown('<span class="badge-active">● RESOURCE OPTIMIZER: ACTIVE</span>', unsafe_allow_html=True)
with b_col3:
    st.markdown('<span class="badge-active">● SCENARIO ENGINE: ACTIVE</span>', unsafe_allow_html=True)
with b_col4:
    st.markdown('<span class="badge-active">● ADAPTIVE RESERVE: ACTIVE</span>', unsafe_allow_html=True)
with b_col5:
    st.markdown('<span class="badge-gated">⊘ YIELD FORECAST: DATA GATED</span>', unsafe_allow_html=True)

st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Sidebar: Jury Controls & Navigation
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🎛️ Demo & Navigation Controls")
    jury_mode = st.toggle("⭐ Jury Demo Mode", value=True, help="Streamlines dashboard to executive decision intelligence flow.")

    st.markdown("---")
    st.markdown("#### ⚡ 1-Click Demonstration Presets")
    st.caption("Select a scenario to trigger the full decision engine instantly:")

    for preset_name in DEMO_PRESETS:
        btn_label = f"👉 {preset_name.split(' (')[0]}"
        if st.button(btn_label, use_container_width=True, help=DEMO_PRESETS[preset_name]["description"]):
            preset_prof = get_preset_profile(preset_name)
            st.session_state["submitted_profile"] = preset_prof
            st.session_state["profile_data"] = preset_prof.model_dump()
            st.session_state["pipeline_output"] = execute_full_decision_pipeline(preset_prof)
            st.session_state["active_preset"] = preset_name
            st.rerun()

    st.markdown("---")
    with st.expander("⏱️ 3-Minute Demo Cheat-Sheet", expanded=False):
        st.markdown("""
        **1. Step 1 (0:00 - 0:45)**:
        Click **Balanced Farm**. Point to *Decision Summary* & *AI Suitability*. Show how multi-crop allocation is solved.
        
        **2. Step 2 (0:45 - 1:30)**:
        Click **Water-Stressed Farm**. Show *Water* becoming the binding 100% constraint and adaptation to drought-hardy crops.
        
        **3. Step 3 (1:30 - 2:15)**:
        Scroll to **What-If Simulator**. Reduce water by -25%. Show reoptimization, plan stability metric, and acreage shift.
        
        **4. Step 4 (2:15 - 2:45)**:
        Review **Why Did FarmTwin Make This Decision?**. Point out mathematical explainability.
        
        **5. Step 5 (2:45 - 3:00)**:
        Show **Yield Forecasting — DATA GATED**. Explain scientific integrity: refusing to hallucinate yields without multi-year empirical datasets.
        """)

# Initialize default session state if empty
if "pipeline_output" not in st.session_state:
    default_p = get_preset_profile("Balanced Farm (Telangana)")
    st.session_state["submitted_profile"] = default_p
    st.session_state["profile_data"] = default_p.model_dump()
    st.session_state["pipeline_output"] = execute_full_decision_pipeline(default_p)
    st.session_state["active_preset"] = "Balanced Farm (Telangana)"

# -----------------------------------------------------------------------------
# Feature 2: Quick Demo Presets Top Bar
# -----------------------------------------------------------------------------
st.markdown("#### ⚡ Quick Demo Presets (Select to Test Decision Behavior)")
p_col1, p_col2, p_col3, p_col4 = st.columns(4)

with p_col1:
    if st.button("🌾 **Balanced Farm**\n\nTelangana (1.0 ha)", use_container_width=True):
        p = get_preset_profile("Balanced Farm (Telangana)")
        st.session_state["submitted_profile"] = p
        st.session_state["profile_data"] = p.model_dump()
        st.session_state["pipeline_output"] = execute_full_decision_pipeline(p)
        st.session_state["active_preset"] = "Balanced Farm (Telangana)"
        st.rerun()

with p_col2:
    if st.button("💧 **Water-Stressed Farm**\n\nRajasthan (2.0 ha)", use_container_width=True):
        p = get_preset_profile("Water-Stressed Farm (Rajasthan)")
        st.session_state["submitted_profile"] = p
        st.session_state["profile_data"] = p.model_dump()
        st.session_state["pipeline_output"] = execute_full_decision_pipeline(p)
        st.session_state["active_preset"] = "Water-Stressed Farm (Rajasthan)"
        st.rerun()

with p_col3:
    if st.button("🧪 **Fertilizer-Constrained**\n\nBihar (2.0 ha)", use_container_width=True):
        p = get_preset_profile("Fertilizer-Constrained Farm (Bihar)")
        st.session_state["submitted_profile"] = p
        st.session_state["profile_data"] = p.model_dump()
        st.session_state["pipeline_output"] = execute_full_decision_pipeline(p)
        st.session_state["active_preset"] = "Fertilizer-Constrained Farm (Bihar)"
        st.rerun()

with p_col4:
    if st.button("⚠️ **Capital-Constrained**\n\nMaharashtra (3.0 ha)", use_container_width=True):
        p = get_preset_profile("Capital-Constrained Farm (Maharashtra)")
        st.session_state["submitted_profile"] = p
        st.session_state["profile_data"] = p.model_dump()
        st.session_state["pipeline_output"] = execute_full_decision_pipeline(p)
        st.session_state["active_preset"] = "Capital-Constrained Farm (Maharashtra)"
        st.rerun()

active_name = st.session_state.get("active_preset", "Custom Farm")
st.info(f"📍 **Active Demo Profile**: **{active_name}** — {DEMO_PRESETS.get(active_name, {}).get('description', 'Custom farm parameters active.')}")

# -----------------------------------------------------------------------------
# Optional Custom Farm Profile Form (Collapsible)
# -----------------------------------------------------------------------------
with st.expander("✏️ Modify Custom Farm Parcel Parameters", expanded=False):
    defaults = st.session_state.get("profile_data", {})
    with st.form("custom_farm_form"):
        c1, c2, c3, c4 = st.columns(4)
        c_farm_id = c1.text_input("Farm ID", value=defaults.get("farm_id", "FARM-CUSTOM"))
        c_farmer = c2.text_input("Farmer Name", value=defaults.get("farmer_name", "Farmer"))
        c_state = c3.text_input("State", value=defaults.get("state", "Telangana"))
        c_district = c4.text_input("District", value=defaults.get("district", "Warangal"))

        c_land, c_unit, c_wat, c_wunit = st.columns(4)
        c_land_val = c_land.number_input("Land Area", min_value=0.1, value=float(defaults.get("land_area", 2.0)), step=0.5)
        c_land_unit = c_unit.selectbox("Land Unit", options=["hectare", "acre"], index=0)
        c_water_val = c_wat.number_input("Water (L)", min_value=1000.0, value=float(defaults.get("available_water", 10000000.0)), step=500000.0)
        c_water_unit = c_wunit.selectbox("Water Unit", options=["liter", "m3"], index=0)

        c_sn, c_sp, c_sk, c_ph = st.columns(4)
        c_soil_n = c_sn.number_input("Soil N (kg/ha)", value=float(defaults.get("nitrogen_n_kg_ha", 80.0)), step=5.0)
        c_soil_p = c_sp.number_input("Soil P (kg/ha)", value=float(defaults.get("phosphorus_p_kg_ha", 40.0)), step=5.0)
        c_soil_k = c_sk.number_input("Soil K (kg/ha)", value=float(defaults.get("potassium_k_kg_ha", 50.0)), step=5.0)
        c_soil_ph = c_ph.number_input("Soil pH", value=float(defaults.get("ph", 6.8)), step=0.1)

        c_fn, c_fp, c_fk, c_bud = st.columns(4)
        c_fert_n = c_fn.number_input("Fertilizer N (kg)", value=float(defaults.get("available_n_kg", 120.0)), step=10.0)
        c_fert_p = c_fp.number_input("Fertilizer P (kg)", value=float(defaults.get("available_p_kg", 60.0)), step=10.0)
        c_fert_k = c_fk.number_input("Fertilizer K (kg)", value=float(defaults.get("available_k_kg", 50.0)), step=10.0)
        c_budget = c_bud.number_input("Budget (₹)", value=float(defaults.get("available_budget_inr", 50000.0)), step=5000.0)

        c_tmp, c_hum, c_rain, c_seas = st.columns(4)
        c_temp = c_tmp.number_input("Temp (°C)", value=float(defaults.get("temperature_c", 28.0)), step=1.0)
        c_humid = c_hum.number_input("Humidity (%)", value=float(defaults.get("humidity_percent", 65.0)), step=5.0)
        c_rainfall = c_rain.number_input("Rainfall (mm)", value=float(defaults.get("rainfall_mm", 150.0)), step=10.0)
        c_season = c_seas.selectbox("Season", options=["kharif", "rabi", "zaid"], index=0)

        submit_custom = st.form_submit_button("🚀 Validate & Run Decision Pipeline", type="primary")

    if submit_custom:
        custom_payload = {
            "farm_id": c_farm_id,
            "farmer_name": c_farmer,
            "state": c_state,
            "district": c_district,
            "land_area": c_land_val,
            "land_unit": c_land_unit,
            "available_water": c_water_val,
            "water_unit": c_water_unit,
            "nitrogen_n_kg_ha": c_soil_n,
            "phosphorus_p_kg_ha": c_soil_p,
            "potassium_k_kg_ha": c_soil_k,
            "ph": c_soil_ph,
            "available_n_kg": c_fert_n,
            "available_p_kg": c_fert_p,
            "available_k_kg": c_fert_k,
            "available_budget_inr": c_budget,
            "available_labour_days": 100.0,
            "temperature_c": c_temp,
            "humidity_percent": c_humid,
            "rainfall_mm": c_rainfall,
            "season": c_season,
            "year": 2026,
            "risk_tolerance": 0.50,
            "is_demo": False,
        }
        try:
            custom_prof = FarmProfile(**custom_payload)
            st.session_state["submitted_profile"] = custom_prof
            st.session_state["profile_data"] = custom_prof.model_dump()
            st.session_state["pipeline_output"] = execute_full_decision_pipeline(custom_prof)
            st.session_state["active_preset"] = "Custom Farm Profile"
            st.success("✅ Custom profile validated! Decision pipeline executed.")
            st.rerun()
        except ValidationError as exc:
            st.error("Validation error in farm parameters:")
            for err in format_validation_errors(exc):
                st.write(f"• {err}")

# Retrieve active pipeline execution output
pipeline_out = st.session_state.get("pipeline_output")
profile: FarmProfile = st.session_state.get("submitted_profile")

if pipeline_out is not None and profile is not None:
    opt_res = pipeline_out["opt_result"]
    scen_res = pipeline_out["scenario_results"]
    suit_res = pipeline_out["suitability_results"]
    yield_res = pipeline_out["yield_result"]
    p_rep = pipeline_out["portfolio_report"]
    b_rep = pipeline_out["bottleneck_report"]
    a_rep = pipeline_out["adaptive_report"]

    # -------------------------------------------------------------------------
    # Feature 3: Executive Decision Summary
    # -------------------------------------------------------------------------
    st.markdown("---")
    render_executive_decision_summary(pipeline_out)

    # -------------------------------------------------------------------------
    # Feature 4: "Why This Decision?" Explainable Decision
    # -------------------------------------------------------------------------
    render_why_this_decision(pipeline_out)

    # -------------------------------------------------------------------------
    # Feature 5: AI Crop Suitability Visualization
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🌾 Top Suitable Crops (Phase 3 AI Evaluation)")
    st.caption("Machine learning ranking from 2,200-row agro-climatic Random Forest model.")

    top_crops_df = []
    for r in suit_res[:5]:
        top_crops_df.append({
            "Rank": f"#{r.rank}",
            "Crop": r.crop_name.capitalize(),
            "Suitability Score": f"{r.suitability_score * 100:.1f}%",
            "Category": r.suitability_level,
            "Limiting Factors": r.explanation,
        })
    st.table(pd.DataFrame(top_crops_df))

    # Native Streamlit Horizontal Bar Chart
    chart_data = pd.DataFrame({
        "Crop": [r.crop_name.capitalize() for r in suit_res[:5]],
        "Suitability Score (%)": [r.suitability_score * 100 for r in suit_res[:5]]
    }).set_index("Crop")
    st.bar_chart(chart_data)

    # -------------------------------------------------------------------------
    # Feature 6: Farm Resource Balance
    # -------------------------------------------------------------------------
    st.markdown("---")
    render_farm_resource_balance(pipeline_out)

    # -------------------------------------------------------------------------
    # Feature 7: Bottleneck Detector (Hero Feature - Phase 9)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🔍 What Is Limiting This Farm? (Bottleneck Intelligence)")
    st.caption("Diagnose binding resource ceilings, analyze dual shadow values, and evaluate high-leverage expansions.")

    bn_col1, bn_col2, bn_col3 = st.columns(3)
    with bn_col1:
        prim_name = b_rep.primary_bottleneck.replace("_", " ").title() if b_rep.primary_bottleneck else "None"
        st.metric(
            "Primary Bottleneck",
            prim_name,
            f"{b_rep.primary_bottleneck_utilization:.1f}% Capacity" if b_rep.primary_bottleneck_utilization else None,
            help="The single constraint ceiling directly capping further cultivated area."
        )
    with bn_col2:
        sec_str = ", ".join([s.replace("_", " ").title() for s in b_rep.secondary_bottlenecks[:2]]) or "None"
        st.metric("Secondary Constraints", sec_str)
    with bn_col3:
        st.metric("Shadow Multiplier Status", b_rep.shadow_value_status)

    # Constraint states table
    st.markdown("#### Constraint Utilization Regimes")
    regime_rows = []
    for r_k, r_state in b_rep.constraint_states.items():
        regime_rows.append({
            "Resource": r_k.replace("_", " ").title(),
            "Operating Regime": r_state,
            "Heuristic Status": "🔴 Binding Ceiling" if r_state == "BINDING" else (
                "🟠 Near Capacity" if r_state == "NEAR_BINDING" else (
                    "🔵 Safe Active" if r_state == "ACTIVE" else "🟢 Surplus Slack"
                )
            )
        })
    st.dataframe(pd.DataFrame(regime_rows), use_container_width=True)

    # Dual Shadow Multiplier Notice
    st.info(
        "💡 **Dual Shadow Value Interpretation**: Shadow values estimate how much additional suitability-weighted "
        "cultivated area could become available from additional resource capacity. "
        "Units are **suitability-weighted hectares per unit resource** (e.g. ha / 1000 L of water). "
        "They are **never** reported in fake currency (INR)."
    )

    # -------------------------------------------------------------------------
    # Feature 8: Stress Test Lab (Phase 5)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🌦️ Farm Stress Test Lab (Deterministic Stress Scenarios)")
    st.caption("Evaluate how the farm allocation and resource balance adapt across simulated climatic and market shocks.")

    scen_names = list(scen_res.keys())
    sel_scen = st.selectbox(
        "Select Stress Scenario to Compare with Baseline",
        options=scen_names,
        index=1 if len(scen_names) > 1 else 0,
        help="Deterministic stress test scenarios. Climate probabilities are intentionally not fabricated."
    )

    base_opt = scen_res.get("Baseline", opt_res)
    target_opt = scen_res.get(sel_scen, opt_res)

    st.markdown(f"#### Scenario Comparison: Baseline vs **{sel_scen}**")
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.metric(
            "Cultivated Land",
            f"{target_opt.total_land_used_ha:.2f} ha",
            f"{target_opt.total_land_used_ha - base_opt.total_land_used_ha:+.2f} ha"
        )
    with sc2:
        st.metric(
            "Suitability Objective",
            f"{target_opt.objective_value:.3f}" if target_opt.objective_value else "N/A",
            f"{(target_opt.objective_value or 0.0) - (base_opt.objective_value or 0.0):+.3f}"
        )
    with sc3:
        st.metric("Solver Feasibility", target_opt.status)
    with sc4:
        st.metric("Simulation Type", "Deterministic Stress Test")

    # Allocation comparison dataframe
    all_scen_crops = sorted(list(set(base_opt.crop_allocations_ha.keys()).union(target_opt.crop_allocations_ha.keys())))
    comp_rows = []
    for c in all_scen_crops:
        b_val = base_opt.crop_allocations_ha.get(c, 0.0)
        t_val = target_opt.crop_allocations_ha.get(c, 0.0)
        comp_rows.append({
            "Crop": c.capitalize(),
            "Baseline Allocation (ha)": f"{b_val:.3f}",
            f"{sel_scen} Allocation (ha)": f"{t_val:.3f}",
            "Delta (ha)": f"{t_val - b_val:+.3f}"
        })
    st.dataframe(pd.DataFrame(comp_rows), use_container_width=True)

    # -------------------------------------------------------------------------
    # Feature 9: Adaptive Reserve (Phase 10)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🛡️ Adaptive Farm Reserve (Buffer Health & Recourse)")
    st.caption("Contingency buffer auditing and operational trigger monitoring.")

    ar_col1, ar_col2 = st.columns([1, 1])
    with ar_col1:
        st.markdown("#### Unallocated Resource Reserve Buffers")
        buf_rows = []
        for r_k, r_vals in a_rep.reserve_summary.items():
            st_class = a_rep.critical_reserves.get(r_k, "HEALTHY")
            buf_rows.append({
                "Resource": r_k.replace("_", " ").title(),
                "Capacity": f"{r_vals.get('available', 0.0):,.1f}",
                "Used": f"{r_vals.get('used', 0.0):,.1f}",
                "Reserve (%)": f"{r_vals.get('reserve_pct', 0.0):.1f}%",
                "Buffer Status": st_class
            })
        st.dataframe(pd.DataFrame(buf_rows), use_container_width=True)

    with ar_col2:
        st.markdown("#### Adaptive Management Recommendations")
        st.info(f"**Trigger Status**: **{a_rep.trigger_status}**")
        for rec in a_rep.adaptive_recommendations:
            st.write(f"• {rec}")

    # -------------------------------------------------------------------------
    # Features 10 & 11: Interactive What-If Simulator & Plan Stability
    # -------------------------------------------------------------------------
    st.markdown("---")
    render_what_if_simulator(
        farm_profile=profile,
        candidate_crops=pipeline_out["top_candidates"],
        top_n=5
    )

    # -------------------------------------------------------------------------
    # Feature 12: Yield Forecast Honest Banner (Scientific Integrity)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 📈 Probabilistic Yield Forecasting — Research Status")
    st.caption("Quantile yield regression (P10 pessimistic, P50 median expected, P90 optimistic).")

    with st.container():
        st.markdown("""
        <div style="background-color: #24292e; border: 1px solid #444d56; border-radius: 8px; padding: 20px; margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <h4 style="margin: 0; color: #f1e05a;">⊘ YIELD FORECASTING: DATA GATED</h4>
                <span style="background-color: #d73a49; color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;">SCIENTIFIC GATE ENFORCED</span>
            </div>
            <p style="margin: 0; color: #c9d1d9; font-size: 0.9rem;">
                FarmTwin is architected for probabilistic <strong>P10 / P50 / P90 quantile yield regression</strong>.
                However, this module is <strong>intentionally gated</strong> because no authentic multi-year district agricultural yield dataset
                is physically integrated yet in <code>data/raw/historical_yield.csv</code>.
            </p>
        </div>
        """, unsafe_allow_html=True)

        y_c1, y_c2, y_c3, y_c4 = st.columns(4)
        with y_c1:
            st.metric("Target Crop", suit_res[0].crop_name.capitalize() if suit_res else "None")
        with y_c2:
            st.metric("P10 Lower Yield", "-- t/ha", help="Gated until multi-year yield data is verified")
        with y_c3:
            st.metric("P50 Expected Yield", "-- t/ha", help="Gated until multi-year yield data is verified")
        with y_c4:
            st.metric("P90 Upper Yield", "-- t/ha", help="Gated until multi-year yield data is verified")

        st.caption("🔬 **Why gated?** In accordance with the Data Honesty Rule, FarmTwin strictly forbids hallucinating synthetic yields, profits, or revenues.")

    # -------------------------------------------------------------------------
    # Feature 13: Crop Portfolio & Soil Rotation Intelligence (Phase 8)
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🌾 Crop Portfolio & Soil Intelligence")
    st.caption("Ecological diversity and soil nutrient consumption.")

    port_col1, port_col2, port_col3 = st.columns(3)
    with port_col1:
        st.metric(
            "Shannon Diversity Index (H')",
            f"{p_rep.shannon_diversity_index:.3f}",
            p_rep.diversity_status
        )
    with port_col2:
        st.metric("Nutrient Pressure Index", f"{p_rep.soil_nutrient_pressure_index:.2f}")
    with port_col3:
        st.metric("Crop Rotation Status", "DATA_UNAVAILABLE", help="Empty rotation matrix preserved honestly.")

    # -------------------------------------------------------------------------
    # Feature 14: System Architecture Diagram
    # -------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🏗️ FarmTwin Decision Architecture Pipeline")
    st.caption("Complete, verifiable 9-stage decision flow implemented in the codebase:")

    st.markdown("""
    <div style="display: flex; flex-wrap: wrap; gap: 8px; justify-content: space-between; margin-top: 10px; margin-bottom: 20px;">
        <div class="arch-step">1. Farm Profile<br><small>Physical & Soil Inputs</small></div>
        <div class="arch-step">2. Validation<br><small>Unit Normalization</small></div>
        <div class="arch-step">3. AI Suitability<br><small>Random Forest</small></div>
        <div class="arch-step">4. Resource Balance<br><small>Physical Inventory</small></div>
        <div class="arch-step">5. HiGHS Solver<br><small>Continuous LP</small></div>
        <div class="arch-step">6. Stress Test<br><small>7 Scenarios</small></div>
        <div class="arch-step">7. Bottleneck<br><small>Dual Shadow Analysis</small></div>
        <div class="arch-step">8. Adaptive Reserve<br><small>Buffer Monitoring</small></div>
        <div class="arch-step">9. Actionable Decision<br><small>Farmer Recommendation</small></div>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # Feature 15: Detailed Engineering Diagnostics (Only when Jury Mode is OFF)
    # -------------------------------------------------------------------------
    if not jury_mode:
        st.markdown("---")
        st.markdown("### 🛠️ Low-Level Engineering Telemetry & Diagnostics")
        st.caption("Available when 'Jury Demo Mode' is disabled for technical audit.")

        with st.expander("Normalized Farm Profile JSON Contract", expanded=False):
            st.json(profile.to_normalized())

        with st.expander("SciPy HiGHS LP Solver Diagnostics", expanded=False):
            st.write(f"Solver Status: `{opt_res.status}`")
            st.write(f"Optimization Mode: `{opt_res.optimization_mode}`")
            st.write(f"HiGHS Dual Marginals: `{opt_res.dual_values}`")
            st.write(f"Resource Usage Breakdown: `{opt_res.resource_usage}`")

        with st.expander("AI Suitability Random Forest Metrics", expanded=False):
            st.json(pipeline_out.get("suitability_metrics", {}))

st.markdown("""
---
<div style="text-align: center; color: #718096; font-size: 0.85rem;">
    FarmTwin — Adaptive Farm Decision Engine | Verified Phases 1–10 Functional Prototype | Scientific Data Honesty Enforced
</div>
""", unsafe_allow_html=True)
