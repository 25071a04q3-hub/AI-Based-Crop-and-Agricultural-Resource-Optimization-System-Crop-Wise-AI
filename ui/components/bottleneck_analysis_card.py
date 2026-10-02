"""
FarmTwin UI Component — Bottleneck Analysis & Shadow Value Intelligence Card (Phase 9).

Displays:
- Primary & Secondary Bottlenecks
- Constraint Utilization Table (UNDERUTILIZED, ACTIVE, NEAR_BINDING, BINDING)
- Dual Shadow Value status and values (objective units per resource unit)
- What-If Sensitivity Experiments (+10%, +20% resource expansions)
- Resource Lever Ranking (actionable farmer investment advice)
- Plain-language farmer explanation
"""
from typing import Optional, Dict, Any
import streamlit as st
import pandas as pd

from engine.profile import FarmProfile
from engine.optimizer import FarmOptimizationResult
from engine.portfolio_intelligence import PortfolioAnalysisResult
from engine.bottleneck_analysis import (
    generate_bottleneck_report,
    BottleneckAnalysisResult,
)


def render_bottleneck_analysis_card(
    optimization_result: Optional[FarmOptimizationResult] = None,
    farm_profile: Optional[FarmProfile] = None,
    candidate_crops: Optional[Any] = None,
    portfolio_result: Optional[PortfolioAnalysisResult] = None,
) -> None:
    """
    Renders Phase 9 Bottleneck Analysis & Shadow Value Intelligence in Streamlit.
    """
    st.markdown("### 🔍 Phase 9: Bottleneck Analysis & Shadow Value Intelligence")
    st.caption("Identify binding farm bottlenecks, evaluate dual shadow multipliers, and rank high-leverage resource expansions.")

    st.info(
        "💡 **Diagnostic Bottleneck Engine**: Evaluates which physical farm constraints most restrict "
        "crop cultivation. **Does not alter optimization outputs.** What-If sensitivity analysis re-runs "
        "the deterministic LP solver under controlled +10% and +20% resource expansions. "
        "Dual shadow values reflect marginal suitability gains, **not currency (INR)**, adhering to the Data Honesty Rule."
    )

    if optimization_result is None or not optimization_result.feasibility:
        st.warning("⚠️ Run the Phase 7 Optimizer above with a feasible farm plan to evaluate bottleneck intelligence.")
        return

    # Generate or retrieve Bottleneck Report
    cands = candidate_crops
    if cands is None and "suitability_results" in st.session_state:
        cands = st.session_state["suitability_results"]

    report: BottleneckAnalysisResult = generate_bottleneck_report(
        optimization_result=optimization_result,
        farm_profile=farm_profile,
        candidate_crops=cands,
        top_n=5,
        portfolio_result=portfolio_result,
    )

    # 1. Primary & Secondary Bottleneck Summary Cards
    st.markdown("#### 1. Primary & Secondary Resource Bottlenecks")
    col1, col2, col3 = st.columns(3)
    with col1:
        prim_label = report.primary_bottleneck.replace("_", " ").title() if report.primary_bottleneck else "None"
        st.metric(
            "Primary Bottleneck",
            prim_label,
            f"{report.primary_bottleneck_utilization:.1f}% Utilized" if report.primary_bottleneck_utilization is not None else None,
            help="The single most saturated constraint ceiling restricting further farm acreage expansion."
        )

    with col2:
        sec_names = [s.replace("_", " ").title() for s in report.secondary_bottlenecks[:2]]
        sec_str = ", ".join(sec_names) if sec_names else "None"
        st.metric(
            "Secondary Bottlenecks",
            sec_str,
            help="Subsequent constraints with high utilization."
        )

    with col3:
        st.metric(
            "Shadow Value Status",
            report.shadow_value_status,
            help="Authentic dual multipliers extracted directly from the HiGHS linear programming solver."
        )

    # 2. Constraint Utilization Table
    st.markdown("#### 2. Resource Utilization & Constraint Regimes")
    st.caption("Thresholds: <60% Underutilized, 60%–90% Active, 90%–99% Near Binding, ≥99% Binding.")

    friendly_labels = {
        "land_ha": "Operational Land (ha)",
        "water_liters": "Irrigation Water (L)",
        "nitrogen_kg": "Nitrogen Fertilizer (N)",
        "phosphorus_kg": "Phosphorus Fertilizer (P)",
        "potassium_kg": "Potassium Fertilizer (K)",
        "budget_inr": "Operating Budget (₹)",
    }

    state_badges = {
        "BINDING": "🛑 BINDING (100% Saturation)",
        "NEAR_BINDING": "⚠️ NEAR BINDING (≥90%)",
        "ACTIVE": "🔵 ACTIVE (60%–90%)",
        "UNDERUTILIZED": "🟢 UNDERUTILIZED (<60%)",
        "UNCONSTRAINED": "⚪ UNCONSTRAINED",
    }

    constraint_rows = []
    for res_key, label in friendly_labels.items():
        pct = optimization_result.resource_utilization_pct.get(res_key)
        state = report.constraint_states.get(res_key, "UNCONSTRAINED")
        shadow = report.shadow_values.get(res_key)
        shadow_str = f"+{shadow:.6f}" if shadow and shadow > 1e-6 else "0.000000"

        constraint_rows.append({
            "Resource": label,
            "Utilization (%)": f"{pct:.1f}%" if pct is not None else "N/A",
            "Constraint State": state_badges.get(state, state),
            "Dual Shadow Value": shadow_str,
        })

    st.dataframe(pd.DataFrame(constraint_rows), use_container_width=True)

    # 3. What-If Sensitivity Experiments & Lever Ranking
    st.markdown("#### 3. What-If Resource Sensitivity & Management Levers")
    st.caption("Measured objective improvements from relaxing specific resource constraints by +10% and +20%.")

    if report.resource_lever_ranking:
        lever_df = pd.DataFrame([
            {
                "Rank": item["rank"],
                "Resource Lever": item["resource_label"],
                "Gain with +10% Relax (%)": f"+{item['objective_delta_pct_10']:.1f}%",
                "Land Cultivated Delta": f"+{item['land_delta_ha_10']:.2f} ha",
                "Management Impact": item["impact_label"].replace("_", " "),
            }
            for item in report.resource_lever_ranking
        ])
        st.dataframe(lever_df, use_container_width=True)
    else:
        st.info("Sensitivity analysis requires active candidate crop profiles and farm profile inputs.")

    # 4. Warnings & Alerts
    st.markdown("#### 4. Bottleneck Warnings")
    if report.warnings:
        for w in report.warnings:
            st.warning(f"⚠️ {w}")
    else:
        st.success("✅ No critical binding constraints or capacity deficits detected.")

    # 5. Farmer Explanation Layer
    st.markdown("#### 5. Plain-Language Bottleneck Explanation")
    st.info(f"📋 {report.explanation}")
