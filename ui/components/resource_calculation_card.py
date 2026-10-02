"""
FarmTwin UI Component — Resource Requirement & Balance Card.

Phase 6: Deterministic Resource Calculation & Balance Sheet.
- Calculates land, water, N, P, K, budget, and labour requirements.
- Compares requirements directly against FarmProfile inventories.
- Displays feasibility badges, constraint deficits, and utilization rates.
- Supports scenario-adjusted available resource conditions (e.g. Drought water rationing).
- Does NOT perform optimization or automatic allocation.
"""
from typing import Optional, Dict
import streamlit as st
import pandas as pd

from engine.profile import FarmProfile
from engine.scenario_simulator import get_predefined_scenarios, apply_scenario
from engine.resource_calculator import (
    get_all_crop_resource_profiles,
    calculate_crop_resources,
    calculate_portfolio_resources,
    ResourceCalculationReport,
)


def render_resource_calculation_card(
    profile: FarmProfile,
    default_crop: Optional[str] = None
) -> None:
    """
    Renders Phase 6 Resource Calculation & Resource Balance Engine in Streamlit.
    """
    st.markdown("### ⚖️ Phase 6: Resource Requirement & Balance Engine")
    st.caption("Deterministic resource requirement calculations and balance sheet against available farm inventories.")

    st.info(
        "💡 **Deterministic Resource Accounting**: Evaluates exact resource demands (water, N, P, K, budget, labour) "
        "and balance versus farm inventories. **This is a calculation layer, not an optimizer.** "
        "Optimization, CVaR, and allocation decisions are reserved for upcoming phases."
    )

    all_profiles = get_all_crop_resource_profiles()
    available_crops = sorted(list(all_profiles.keys()))

    tab_single, tab_portfolio = st.tabs([
        "🌾 Single-Crop Resource Analysis",
        "📦 Multi-Crop Portfolio Check",
    ])

    # Optional scenario selection for scenario compatibility (Section 12)
    with st.expander("🌦️ Evaluate Against Future Scenario Inventory (Optional)", expanded=False):
        scen_options = ["Baseline (Normal Inventory)"] + [s.scenario_name for s in get_predefined_scenarios() if s.scenario_name != "Baseline"]
        selected_scen_name = st.selectbox(
            "Select Farm Condition Baseline",
            options=scen_options,
            help="Compare demands against Baseline or a Phase 5 Scenario (e.g. Drought with reduced available water)"
        )

        active_profile = profile
        if selected_scen_name != "Baseline (Normal Inventory)":
            scen_obj = next((s for s in get_predefined_scenarios() if s.scenario_name == selected_scen_name), None)
            if scen_obj:
                adj_prof, _ = apply_scenario(profile, scen_obj)
                if adj_prof:
                    active_profile = adj_prof
                    st.caption(f"Active Scenario: **{selected_scen_name}** | Available Water: **{active_profile.water_liters:,.0f} L**")

    # =========================================================================
    # TAB 1: Single-Crop Resource Analysis
    # =========================================================================
    with tab_single:
        c_crop, c_area = st.columns([3, 2])

        default_idx = 0
        if default_crop and default_crop.lower() in available_crops:
            default_idx = available_crops.index(default_crop.lower())

        sel_crop = c_crop.selectbox(
            "Select Crop to Analyze",
            options=available_crops,
            index=default_idx,
            format_func=lambda x: x.capitalize(),
            key="res_single_crop_sel"
        )

        farm_max_land = float(active_profile.land_area_ha)
        sel_land = c_area.number_input(
            f"Land Area to Plant (ha) [Farm Total: {farm_max_land:.2f} ha]",
            min_value=0.01,
            max_value=max(100.0, farm_max_land * 2),
            value=min(1.0, farm_max_land),
            step=0.25,
            format="%.2f",
            key="res_single_land_val"
        )

        report = calculate_crop_resources(sel_crop, sel_land, active_profile)
        bal = report.balance

        # Feasibility Banner
        if report.is_feasible:
            st.success(f"✅ **FEASIBLE PLAN**: {sel_crop.capitalize()} on {sel_land:.2f} ha satisfies all evaluated resource constraints.")
        else:
            st.error(f"❌ **INFEASIBLE PLAN**: {len(report.constraint_violations)} constraint violation(s) detected.")
            for v in report.constraint_violations:
                st.markdown(f"• ⚠️ **{v}**")

        # Tabular Resource Balance Sheet
        st.markdown("#### 📋 Resource Balance Sheet")
        bal_records = [
            {
                "Resource": "Operational Land",
                "Unit": "ha",
                "Required": f"{bal.land.required:.2f}" if bal.land.required is not None else "N/A",
                "Available": f"{bal.land.available:.2f}" if bal.land.available is not None else "N/A",
                "Remaining": f"{bal.land.remaining:.2f}" if bal.land.remaining is not None else "N/A",
                "Utilization": f"{bal.land.utilization_pct:.1f}%" if bal.land.utilization_pct is not None else "N/A",
                "Status": "🟢 FEASIBLE" if bal.land.is_feasible else "🔴 EXCEEDED",
            },
            {
                "Resource": "Irrigation Water",
                "Unit": "liters",
                "Required": f"{bal.water.required:,.0f}" if bal.water.required is not None else "N/A",
                "Available": f"{bal.water.available:,.0f}" if bal.water.available is not None else "N/A",
                "Remaining": f"{bal.water.remaining:,.0f}" if bal.water.remaining is not None else "N/A",
                "Utilization": f"{bal.water.utilization_pct:.1f}%" if bal.water.utilization_pct is not None else "N/A",
                "Status": "🟢 FEASIBLE" if bal.water.is_feasible else "🔴 SHORTAGE",
            },
            {
                "Resource": "Nitrogen (N)",
                "Unit": "kg",
                "Required": f"{bal.nitrogen.required:.1f}" if bal.nitrogen.required is not None else "N/A",
                "Available": f"{bal.nitrogen.available:.1f}" if bal.nitrogen.available is not None else "N/A",
                "Remaining": f"{bal.nitrogen.remaining:.1f}" if bal.nitrogen.remaining is not None else "N/A",
                "Utilization": f"{bal.nitrogen.utilization_pct:.1f}%" if bal.nitrogen.utilization_pct is not None else "N/A",
                "Status": "🟢 FEASIBLE" if bal.nitrogen.is_feasible else "🔴 DEFICIT",
            },
            {
                "Resource": "Phosphorus (P)",
                "Unit": "kg",
                "Required": f"{bal.phosphorus.required:.1f}" if bal.phosphorus.required is not None else "N/A",
                "Available": f"{bal.phosphorus.available:.1f}" if bal.phosphorus.available is not None else "N/A",
                "Remaining": f"{bal.phosphorus.remaining:.1f}" if bal.phosphorus.remaining is not None else "N/A",
                "Utilization": f"{bal.phosphorus.utilization_pct:.1f}%" if bal.phosphorus.utilization_pct is not None else "N/A",
                "Status": "🟢 FEASIBLE" if bal.phosphorus.is_feasible else "🔴 DEFICIT",
            },
            {
                "Resource": "Potassium (K)",
                "Unit": "kg",
                "Required": f"{bal.potassium.required:.1f}" if bal.potassium.required is not None else "N/A",
                "Available": f"{bal.potassium.available:.1f}" if bal.potassium.available is not None else "N/A",
                "Remaining": f"{bal.potassium.remaining:.1f}" if bal.potassium.remaining is not None else "N/A",
                "Utilization": f"{bal.potassium.utilization_pct:.1f}%" if bal.potassium.utilization_pct is not None else "N/A",
                "Status": "🟢 FEASIBLE" if bal.potassium.is_feasible else "🔴 DEFICIT",
            },
            {
                "Resource": "Working Budget",
                "Unit": "INR (₹)",
                "Required": f"₹{bal.budget.required:,.0f}" if bal.budget.required is not None else "N/A",
                "Available": f"₹{bal.budget.available:,.0f}" if bal.budget.available is not None else "N/A",
                "Remaining": f"₹{bal.budget.remaining:,.0f}" if bal.budget.remaining is not None else "N/A",
                "Utilization": f"{bal.budget.utilization_pct:.1f}%" if bal.budget.utilization_pct is not None else "N/A",
                "Status": "🟢 FEASIBLE" if bal.budget.is_feasible else "🔴 SHORTAGE",
            },
            {
                "Resource": "Operational Labour",
                "Unit": "person-days",
                "Required": "DATA_UNAVAILABLE",
                "Available": f"{bal.labour.available:.1f}" if bal.labour.available is not None else "N/A",
                "Remaining": "DATA_UNAVAILABLE",
                "Utilization": "DATA_UNAVAILABLE",
                "Status": "⚪ UNRECORDED",
            },
        ]
        st.dataframe(pd.DataFrame(bal_records), use_container_width=True, hide_index=True)

        with st.expander("ℹ️ Data Honesty & Parameter Disclosures", expanded=False):
            st.markdown("""
            * **Water Consumption**: Derived from `water_req_mm` in `config/crops_profile.json` using exact agronomic conversion:
              $1\\text{ mm depth over } 1\\text{ ha} = 10\\text{ m}^3 = 10,000\\text{ liters}$.
            * **Rainfall Distinction**: Seasonal rainfall is an environmental parameter and is **not** conflated with available irrigation water.
            * **Nutrients (N-P-K)**: Tracked independently against the farm's available fertilizer stocks.
            * **Labour Requirement**: Not present in `config/crops_profile.json`. Reported honestly as `DATA_UNAVAILABLE`.
            """)

    # =========================================================================
    # TAB 2: Multi-Crop Portfolio Check
    # =========================================================================
    with tab_portfolio:
        st.markdown("#### Multi-Crop Arithmetic Allocation Check")
        st.caption("Verify aggregated resource requirements across a user-defined crop combination.")

        col1, col2, col3 = st.columns(3)
        crop1 = col1.selectbox("Crop #1", options=available_crops, index=available_crops.index("rice") if "rice" in available_crops else 0, key="port_c1")
        area1 = col1.number_input(f"Area for {crop1.capitalize()} (ha)", min_value=0.1, max_value=farm_max_land, value=min(0.8, farm_max_land), step=0.1, key="port_a1")

        crop2 = col2.selectbox("Crop #2", options=available_crops, index=available_crops.index("maize") if "maize" in available_crops else 1, key="port_c2")
        area2 = col2.number_input(f"Area for {crop2.capitalize()} (ha)", min_value=0.1, max_value=farm_max_land, value=min(0.7, farm_max_land), step=0.1, key="port_a2")

        crop3 = col3.selectbox("Crop #3", options=available_crops, index=available_crops.index("chickpea") if "chickpea" in available_crops else 2, key="port_c3")
        area3 = col3.number_input(f"Area for {crop3.capitalize()} (ha)", min_value=0.1, max_value=farm_max_land, value=min(0.5, farm_max_land), step=0.1, key="port_a3")

        alloc_dict = {crop1: area1, crop2: area2, crop3: area3}

        if st.button("📊 Calculate Portfolio Requirements", type="primary", key="btn_calc_portfolio"):
            port_report = calculate_portfolio_resources(alloc_dict, active_profile)
            p_bal = port_report.balance

            if port_report.is_feasible:
                st.success(f"✅ **FEASIBLE PORTFOLIO**: Total {port_report.total_land_used_ha:.2f} ha used of {active_profile.land_area_ha:.2f} ha.")
            else:
                st.error(f"❌ **INFEASIBLE PORTFOLIO**: {len(port_report.constraint_violations)} violation(s).")
                for v in port_report.constraint_violations:
                    st.markdown(f"• ⚠️ **{v}**")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Land Used", f"{port_report.total_land_used_ha:.2f} ha", delta=f"{p_bal.land.remaining:.2f} ha rem")
            m2.metric("Total Water", f"{port_report.total_water_liters:,.0f} L", delta=f"{p_bal.water.remaining:,.0f} L rem")
            m3.metric("Total N-P-K", f"{port_report.total_n_kg:.0f}N / {port_report.total_p_kg:.0f}P / {port_report.total_k_kg:.0f}K kg")
            m4.metric("Total Cost", f"₹{port_report.total_cost_inr:,.0f}" if port_report.total_cost_inr is not None else "N/A")
