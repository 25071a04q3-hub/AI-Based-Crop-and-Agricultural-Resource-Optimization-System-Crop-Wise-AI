"""
FarmTwin UI Component — Risk-Aware Farm Optimization Engine (Phase 7).

Displays:
- Optimization Mode (RESOURCE_ONLY, strictly honest gating of economic optimization)
- Candidate crop selection and Phase 3 suitability ranking
- Continuous linear programming allocation (SciPy HiGHS)
- Optimized land allocation table (ha)
- Resource usage vs available inventory balance sheet
- Solver feasibility status (OPTIMAL / INFEASIBLE)
- Binding resource identification
- Farmer-friendly plain-language explanation
- Scenario comparison tab (Baseline vs Drought vs Water Shortage)
"""
from typing import Optional, List, Dict, Any
import streamlit as st
import pandas as pd

from engine.profile import FarmProfile
from engine.optimizer import (
    optimize_farm_allocation,
    optimize_across_scenarios,
    OptimizationMode,
    OptimizationObjective,
    FarmOptimizationResult,
)
from engine.scenario_simulator import get_predefined_scenarios


def render_optimizer_card(
    profile: FarmProfile,
    candidate_crops: Optional[List[Any]] = None,
) -> None:
    """
    Renders Phase 7 Risk-Aware Farm Optimization Engine card in Streamlit.
    """
    st.markdown("### 🎯 Phase 7: Risk-Aware Farm Optimization Engine")
    st.caption("Continuous mathematical land & resource allocation under scarce farm constraints.")

    # Data honesty notice
    st.info(
        "💡 **Data Honesty & Provisional Resource Optimization**: "
        "Economic yield optimization is currently **BLOCKED** because the Phase 4 historical yield model "
        "lacks an authentic empirical training dataset. Operating in **`RESOURCE_ONLY`** mode: "
        "maximizing suitability-weighted productive land subject to physical land, water, nutrient, and budget limits. "
        "No simulated or fake profit is displayed."
    )

    col_meta1, col_meta2, col_meta3 = st.columns(3)
    with col_meta1:
        st.metric("Optimization Mode", "RESOURCE_ONLY", help="Provisional resource allocation mode")
    with col_meta2:
        st.metric("Objective Function", "Suitability-Weighted Land", help="maximize sum(suitability_i * x_i)")
    with col_meta3:
        st.metric("Expected Profit", "DATA_UNAVAILABLE", help="Gated until empirical yield data is integrated")

    # Candidate crops setup
    # If candidate crops passed from session (e.g. from Phase 3), offer top-N selection; otherwise allow selection
    top_candidates = []
    if candidate_crops:
        top_candidates = candidate_crops
    elif "suitability_results" in st.session_state and st.session_state["suitability_results"]:
        top_candidates = st.session_state["suitability_results"]

    st.markdown("#### 1. Candidate Crop Selection")
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        top_n = st.slider("Top N Candidates to Optimize", min_value=2, max_value=8, value=5, step=1)

    # Prepare candidate display / selection
    if top_candidates:
        # Use top N candidates from Phase 3
        # Can be list of CropSuitabilityResult or dicts
        st.markdown(f"Using **Top {top_n} crops** from Phase 3 AI Suitability ranking:")
        cand_rows = []
        for i, c in enumerate(top_candidates[:top_n]):
            name = getattr(c, "crop_name", None) or (c.get("crop") if isinstance(c, dict) else str(c))
            score = getattr(c, "suitability_score", None) or (c.get("score") if isinstance(c, dict) else 0.70)
            cand_rows.append({"Rank": i + 1, "Crop": name.capitalize(), "Suitability Score": f"{score:.4f}"})
        st.table(pd.DataFrame(cand_rows))
        selected_candidates = top_candidates[:top_n]
    else:
        st.warning("Phase 3 AI Suitability has not run yet. Using default diverse regional candidates.")
        default_dict = {"rice": 0.82, "maize": 0.76, "chickpea": 0.71, "pigeonpeas": 0.68, "cotton": 0.61}
        selected_candidates = list(default_dict.items())[:top_n]
        cand_rows = [{"Rank": idx + 1, "Crop": k.capitalize(), "Suitability Score": f"{v:.4f}"} for idx, (k, v) in enumerate(selected_candidates)]
        st.table(pd.DataFrame(cand_rows))

    tab_opt, tab_scen = st.tabs([
        "🌾 Farm Optimization Plan",
        "🌦️ Scenario-Adjusted Resource Comparison",
    ])

    with tab_opt:
        if st.button("🚀 Run FarmTwin Optimizer", type="primary", key="btn_run_optimizer"):
            with st.spinner("Solving linear programming allocation via SciPy HiGHS..."):
                res: FarmOptimizationResult = optimize_farm_allocation(
                    profile=profile,
                    candidate_crops=selected_candidates,
                    top_n=top_n,
                    mode=OptimizationMode.RESOURCE_ONLY,
                )
                st.session_state["phase7_result"] = res

        if "phase7_result" in st.session_state:
            res: FarmOptimizationResult = st.session_state["phase7_result"]

            # Status Banner
            if res.feasibility and res.status == "OPTIMAL":
                st.success(f"✅ **Solver Status: {res.status}** — Feasible allocation plan determined successfully.")
            elif res.feasibility:
                st.info(f"ℹ️ **Solver Status: {res.status}**")
            else:
                st.error(f"❌ **Solver Status: {res.status}** — Infeasible farm constraints: {', '.join(res.constraint_violations)}")

            # Metrics
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.metric("Total Land Used", f"{res.total_land_used_ha:.2f} ha", f"of {profile.land_area:.2f} ha")
            with m2:
                st.metric("Land Remaining", f"{res.land_remaining_ha:.2f} ha")
            with m3:
                st.metric("Objective Value", f"{res.objective_value:.4f}" if res.objective_value is not None else "N/A", help="Total suitability-weighted land")
            with m4:
                risk_label = "BLOCKED" if "BLOCKED" in res.risk_status else res.risk_status
                st.metric("Risk Optimization", risk_label, help="Requires calibrated empirical scenario probabilities")

            st.markdown("##### 📐 Optimized Land Allocation")
            alloc_rows = []
            for crop, ha in res.crop_allocations_ha.items():
                alloc_rows.append({
                    "Crop": crop.capitalize(),
                    "Allocated Land (ha)": f"{ha:.4f} ha",
                    "Share of Farm (%)": f"{(ha / profile.land_area * 100.0):.1f}%" if profile.land_area > 0 else "0.0%",
                })
            st.dataframe(pd.DataFrame(alloc_rows), use_container_width=True)

            st.markdown("##### 📊 Resource Consumption vs Available Inventory")
            resource_rows = []
            display_names = {
                "land_ha": ("Land", "ha"),
                "water_liters": ("Water", "L"),
                "nitrogen_kg": ("Nitrogen (N)", "kg"),
                "phosphorus_kg": ("Phosphorus (P)", "kg"),
                "potassium_kg": ("Potassium (K)", "kg"),
                "budget_inr": ("Budget", "₹"),
                "labour_days": ("Labour", "days"),
            }

            for key, (label, unit) in display_names.items():
                used = res.resource_usage.get(key, 0.0)
                rem = res.resource_remaining.get(key, 0.0)
                pct = res.resource_utilization_pct.get(key)
                # compute available = used + rem
                avail = used + rem if rem is not None else None

                used_str = f"{used:,.1f} {unit}" if used is not None else "N/A"
                avail_str = f"{avail:,.1f} {unit}" if avail is not None else "UNRESTRICTED"
                rem_str = f"{rem:,.1f} {unit}" if rem is not None else "UNRESTRICTED"
                pct_str = f"{pct:.1f}%" if pct is not None else "N/A (unconstrained)"

                is_binding = "⚠️ NEAR BINDING" if key in res.binding_resources else "OK"
                resource_rows.append({
                    "Resource": label,
                    "Required": used_str,
                    "Available": avail_str,
                    "Remaining": rem_str,
                    "Utilization (%)": pct_str,
                    "Constraint State": is_binding,
                })
            st.dataframe(pd.DataFrame(resource_rows), use_container_width=True)

            if res.binding_resources:
                st.caption(f"⚠️ **Saturated Constraints**: The optimizer was limited by: `{[display_names[r][0] for r in res.binding_resources]}`.")

            st.markdown("##### 💬 FarmTwin Decision Explanation")
            st.markdown(f"> {res.explanation}")

    with tab_scen:
        st.markdown("#### Scenario-Adjusted Resource Allocation")
        st.caption("Compares farm allocations across baseline, drought, and water shortage resource states.")

        if st.button("🔄 Compare Across Resource Scenarios", key="btn_compare_scenarios"):
            with st.spinner("Evaluating allocations under adjusted scenario inventories..."):
                scen_results = optimize_across_scenarios(
                    profile=profile,
                    candidate_crops=selected_candidates,
                    top_n=top_n,
                )
                st.session_state["phase7_scenarios"] = scen_results

        if "phase7_scenarios" in st.session_state:
            scen_results = st.session_state["phase7_scenarios"]
            comparison_rows = []
            for scen_name, s_res in scen_results.items():
                alloc_str = ", ".join([f"{c}: {ha:.2f} ha" for c, ha in s_res.crop_allocations_ha.items() if ha > 0]) or "None (0 ha)"
                comparison_rows.append({
                    "Scenario": scen_name,
                    "Available Water (L)": f"{s_res.resource_usage['water_liters'] + s_res.resource_remaining['water_liters']:,.0f} L",
                    "Status": s_res.status,
                    "Allocations": alloc_str,
                    "Land Used (ha)": f"{s_res.total_land_used_ha:.2f} ha",
                    "Objective Value": f"{s_res.objective_value:.4f}" if s_res.objective_value is not None else "N/A",
                })
            st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True)

            # Informative scenario shift explanation
            if "Baseline" in scen_results and "Drought" in scen_results:
                base_alloc = scen_results["Baseline"].crop_allocations_ha
                drought_alloc = scen_results["Drought"].crop_allocations_ha
                if base_alloc != drought_alloc:
                    st.info(
                        "🌦️ **Scenario Shift Insight**: Under drought conditions, available water is curtailed, "
                        "causing the optimizer to reduce or drop high-water demanding crops in favor of water-efficient allocations."
                    )
