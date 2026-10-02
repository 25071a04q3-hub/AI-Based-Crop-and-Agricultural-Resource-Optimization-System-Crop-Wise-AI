"""
FarmTwin UI Component — Adaptive Reserve & Mid-Season Re-Optimization Card (Phase 10).

Displays:
- Reserve Summary Table (Available, Used, Remaining Reserve, Reserve %)
- Critical Reserve Status (EXHAUSTED, CRITICAL, LOW, HEALTHY)
- Re-Optimization Triggers & Sensitivity Thresholds
- Plan Stability across stress scenarios (HIGH, MODERATE, LOW STABILITY)
- Interactive Mid-Season Shock Simulation (e.g. Water -20%, Budget -15%)
- Actionable Adaptive Management Recommendations
- Plain-Language Farmer Explanation
"""
from typing import Optional, Dict, Any
import streamlit as st
import pandas as pd

from engine.profile import FarmProfile
from engine.optimizer import FarmOptimizationResult
from engine.adaptive_reserve import (
    generate_adaptive_report,
    simulate_resource_change,
    AdaptiveReserveResult,
    ReoptimizationTriggerConfig,
)


def render_adaptive_reserve_card(
    optimization_result: Optional[FarmOptimizationResult] = None,
    farm_profile: Optional[FarmProfile] = None,
    candidate_crops: Optional[Any] = None,
    scenario_results: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Renders Phase 10 Adaptive Farm Management & Re-Optimization card in Streamlit.
    """
    st.markdown("### 🛡️ Phase 10: Adaptive Reserve & Mid-Season Re-Optimization")
    st.caption("Contingency buffer auditing, re-optimization trigger boundaries, and mid-season recourse simulation.")

    st.info(
        "💡 **Adaptive Planning Layer**: Evaluates how much resource reserve buffer remains unused "
        "to protect against mid-season volatility. Identifies operational trigger boundaries that require "
        "re-optimization, audits allocation stability under climate stress, and enables interactive "
        "mid-season recourse simulation. **No fake economic or yield forecasts are generated.**"
    )

    if optimization_result is None or not optimization_result.feasibility:
        st.warning("⚠️ Run the Phase 7 Optimizer above with a feasible farm plan to evaluate adaptive reserve intelligence.")
        return

    scens = scenario_results
    if scens is None and "phase7_scenarios" in st.session_state:
        scens = st.session_state["phase7_scenarios"]

    cands = candidate_crops
    if cands is None and "suitability_results" in st.session_state:
        cands = st.session_state["suitability_results"]

    # Generate Adaptive Report
    report: AdaptiveReserveResult = generate_adaptive_report(
        optimization_result=optimization_result,
        farm_profile=farm_profile,
        candidate_crops=cands,
        scenario_results=scens,
    )

    # 1. Summary Metrics
    st.markdown("#### 1. Adaptive Management Status")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "Trigger Status",
            report.trigger_status.replace("_", " "),
            help="Status indicating whether current farm conditions require re-running optimization."
        )
    with col2:
        st.metric(
            "Plan Stability",
            report.stability_status.replace("_", " "),
            help="Degree to which crop allocations remain robust across stress scenarios."
        )
    with col3:
        exhausted_cnt = sum(1 for s in report.critical_reserves.values() if s == "EXHAUSTED")
        st.metric(
            "Exhausted Reserves",
            f"{exhausted_cnt} Resource{'s' if exhausted_cnt != 1 else ''}",
            help="Resources with 0% remaining buffer margin."
        )
    with col4:
        healthy_cnt = sum(1 for s in report.critical_reserves.values() if s == "HEALTHY")
        st.metric(
            "Healthy Reserves",
            f"{healthy_cnt} Resource{'s' if healthy_cnt != 1 else ''}",
            help="Resources with ≥25% remaining contingency buffer."
        )

    # 2. Reserve Summary Table
    st.markdown("#### 2. Resource Reserve Buffers & Critical Health")
    st.caption("Thresholds: ≤0.1% Exhausted (No Margin), <10% Critical, <25% Low, ≥25% Healthy.")

    friendly_names = {
        "land_ha": ("Operational Land", "ha"),
        "water_liters": ("Irrigation Water", "L"),
        "nitrogen_kg": ("Nitrogen (N)", "kg"),
        "phosphorus_kg": ("Phosphorus (P)", "kg"),
        "potassium_kg": ("Potassium (K)", "kg"),
        "budget_inr": ("Operating Budget", "₹"),
    }

    state_badges = {
        "EXHAUSTED": "🛑 EXHAUSTED (0% Margin)",
        "CRITICAL": "⚠️ CRITICAL (<10%)",
        "LOW": "🟡 LOW (<25%)",
        "HEALTHY": "🟢 HEALTHY (≥25%)",
    }

    reserve_rows = []
    for res_key, (name, unit) in friendly_names.items():
        data = report.reserve_summary.get(res_key, {})
        crit = report.critical_reserves.get(res_key, "UNKNOWN")
        avail = data.get("available", 0.0)
        used = data.get("used", 0.0)
        rem = data.get("reserve", 0.0)
        pct = data.get("reserve_pct", 0.0)

        reserve_rows.append({
            "Resource": name,
            "Total Available": f"{avail:,.1f} {unit}",
            "Used by Plan": f"{used:,.1f} {unit}",
            "Contingency Reserve": f"{rem:,.1f} {unit}",
            "Reserve Margin (%)": f"{pct:.1f}%",
            "Buffer Health": state_badges.get(crit, crit),
        })

    st.dataframe(pd.DataFrame(reserve_rows), use_container_width=True)

    # 3. Interactive Mid-Season Recourse Simulation
    st.markdown("#### 3. Mid-Season Recourse Shock Simulation")
    st.caption("Simulate unforeseen mid-season resource shifts and observe how FarmTwin re-balances the farm.")

    if farm_profile is not None and cands is not None:
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            water_shift = st.slider("Irrigation Water Shift (%)", min_value=-50, max_value=20, value=-20, step=5)
        with col_s2:
            budget_shift = st.slider("Operating Budget Shift (%)", min_value=-40, max_value=20, value=-15, step=5)
        with col_s3:
            fert_shift = st.slider("Fertilizer Inventory Shift (%)", min_value=-40, max_value=20, value=0, step=5)

        if st.button("⚡ Simulate Mid-Season Recourse Plan", key="btn_midseason_sim"):
            sim_dict = {
                "available_water": float(water_shift),
                "available_budget_inr": float(budget_shift),
                "available_n_kg": float(fert_shift),
            }
            sim_res = simulate_resource_change(
                farm_profile=farm_profile,
                candidate_crops=cands,
                top_n=5,
                resource_changes_pct=sim_dict
            )
            st.session_state["phase10_simulation"] = sim_res

        if "phase10_simulation" in st.session_state:
            s_out = st.session_state["phase10_simulation"]
            st.markdown("##### 📊 Recourse Re-Optimization Comparison")
            c_diff1, c_diff2, c_diff3 = st.columns(3)
            with c_diff1:
                st.metric("Baseline Land Cultivated", f"{s_out['baseline_land_ha']:.2f} ha")
            with c_diff2:
                st.metric("Recourse Land Cultivated", f"{s_out['updated_land_ha']:.2f} ha", f"{s_out['land_delta_ha']:+.2f} ha")
            with c_diff3:
                st.metric("Objective Shift", f"{s_out['updated_objective']:.4f}", f"{s_out['objective_delta']:+.4f}")

            diff_rows = [
                {"Crop": c.capitalize(), "Acreage Adjustment": f"{delta:+.4f} ha"}
                for c, delta in s_out["crop_deltas"].items()
                if abs(delta) > 0.0001
            ]
            if diff_rows:
                st.dataframe(pd.DataFrame(diff_rows), use_container_width=True)
            else:
                st.info("Allocations remained identical under this shock level.")

    # 4. Adaptive Recommendations
    st.markdown("#### 4. Adaptive Recommendations & Actionable Guidance")
    for rec in report.adaptive_recommendations:
        st.write(f"• {rec}")

    # 5. Farmer Explanation
    st.markdown("#### 5. Plain-Language Adaptive Plan Summary")
    st.info(f"📋 {report.explanation}")
