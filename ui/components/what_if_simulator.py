"""
FarmTwin UI Component — Interactive What-If Scenario & Reoptimization Simulator.

Allows users to simulate mid-season parameter shifts (water, budget, land, fertilizers)
and directly re-runs the deterministic LP solver to compare baseline vs what-if plans.
"""
from typing import Any, Dict, Optional
import streamlit as st
import pandas as pd

from engine.profile import FarmProfile
from engine.adaptive_reserve import simulate_resource_change


def render_what_if_simulator(
    farm_profile: FarmProfile,
    candidate_crops: Any,
    top_n: int = 5
) -> None:
    """
    Renders the interactive What-If reoptimization simulator card in Streamlit.
    """
    st.markdown("### ⚡ Interactive What-If Simulator & Plan Stability")
    st.caption("Simulate real-world operational changes and observe how FarmTwin deterministically reoptimizes allocation.")

    st.info(
        "💡 **Deterministic Reoptimization**: Adjust resource capacities below to simulate drought, budget cuts, "
        "or land changes. FarmTwin re-solves the continuous HiGHS linear programming allocation and measures "
        "the exact plan shift (Total Variation Distance) without using synthetic estimates."
    )

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        water_shift = st.slider("Water Capacity Shift (%)", min_value=-60, max_value=60, value=-25, step=5, help="Simulate drought or irrigation expansion")
    with col2:
        budget_shift = st.slider("Budget Shift (%)", min_value=-60, max_value=60, value=0, step=5, help="Simulate capital reduction or emergency loan")
    with col3:
        land_shift = st.slider("Land Area Shift (%)", min_value=-50, max_value=50, value=0, step=5, help="Simulate parcel subdivision or leasing")
    with col4:
        fert_shift = st.slider("Fertilizer Shift (%)", min_value=-60, max_value=60, value=0, step=5, help="Simulate input availability shock")

    changes = {}
    if water_shift != 0:
        changes["available_water"] = float(water_shift)
    if budget_shift != 0:
        changes["available_budget_inr"] = float(budget_shift)
    if land_shift != 0:
        changes["land_area"] = float(land_shift)
    if fert_shift != 0:
        changes["available_n_kg"] = float(fert_shift)
        changes["available_p_kg"] = float(fert_shift)
        changes["available_k_kg"] = float(fert_shift)

    # Simulation execution
    sim_out = simulate_resource_change(
        farm_profile=farm_profile,
        candidate_crops=candidate_crops,
        top_n=top_n,
        resource_changes_pct=changes if changes else {"available_water": -25.0}
    )

    # Plan Stability & Shift calculation
    base_land = sim_out["baseline_land_ha"]
    crop_deltas = sim_out["crop_deltas"]
    abs_delta_sum = sum(abs(v) for v in crop_deltas.values())
    tvd_shift = (abs_delta_sum / (2.0 * base_land)) if base_land > 0 else 0.0
    tvd_shift = min(1.0, max(0.0, tvd_shift))
    stability_score = round(1.0 - tvd_shift, 4)

    if stability_score >= 0.85:
        stab_badge = "🟢 **HIGH STABILITY**"
        stab_expl = f"Allocation shifts by only {tvd_shift * 100:.1f}%. The farm plan is robust to this resource shift."
    elif stability_score >= 0.60:
        stab_badge = "🟡 **MODERATE STABILITY**"
        stab_expl = f"Allocation shifts by {tvd_shift * 100:.1f}%. The optimizer adjusts crop mix to preserve feasibility."
    else:
        stab_badge = "🔴 **LOW STABILITY / HIGH REALLOCATION**"
        stab_expl = f"Allocation shifts by {tvd_shift * 100:.1f}%. Severe acreage contraction or crop abandonment occurs."

    # Display comparison cards
    st.markdown("#### 1. Baseline Plan vs What-If Reoptimized Plan")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "Total Land Allocated",
            f"{sim_out['updated_land_ha']:.2f} ha",
            f"{sim_out['land_delta_ha']:+.2f} ha" if sim_out['land_delta_ha'] != 0 else "No change"
        )
    with m2:
        st.metric(
            "Suitability Objective",
            f"{sim_out['updated_objective']:.3f}",
            f"{sim_out['objective_delta']:+.3f}" if sim_out['objective_delta'] != 0 else "No change"
        )
    with m3:
        st.metric(
            "Plan Stability Score",
            f"{stability_score * 100:.1f}%",
            help="1.0 - Total Variation Distance across crop allocations"
        )
    with m4:
        st.metric(
            "Solver Status",
            sim_out["updated_status"]
        )

    st.markdown(f"**Plan Stability**: {stab_badge} — {stab_expl}")

    # Crop Allocation Comparison Table
    st.markdown("#### 2. Crop-by-Crop Acreage Shift")
    rows = []
    for crop, delta in crop_deltas.items():
        base_alloc = sim_out["baseline_land_ha"]  # just for reference
        rows.append({
            "Crop": crop.capitalize(),
            "Acreage Change": f"{delta:+.3f} ha",
            "Direction": "⬆️ Expanded" if delta > 0.001 else ("⬇️ Reduced" if delta < -0.001 else "Unchanged")
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)
