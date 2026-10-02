"""
FarmTwin UI Component — Crop Portfolio & Soil Rotation Intelligence Card (Phase 8).

Displays:
- Portfolio Summary (Crops Used, Land Used, Diversity Status, Resilience Status, Rotation Status)
- Shannon Diversity Index score and classification
- Soil Nutrient Pressure (N, P, K utilization percentages and heuristic thresholds)
- Portfolio Warnings (monoculture risks, high water dependence, nutrient pressure)
- Scenario Resilience Metric (% of cultivated land preserved under worst-case stress)
- Plain-language farmer explanation
"""
from typing import Optional, Dict, Any
import streamlit as st
import pandas as pd

from engine.optimizer import FarmOptimizationResult
from engine.portfolio_intelligence import (
    generate_portfolio_report,
    PortfolioAnalysisResult,
)


def render_portfolio_intelligence_card(
    optimization_result: Optional[FarmOptimizationResult] = None,
    scenario_results: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Renders Phase 8 Crop Portfolio & Soil Rotation Intelligence dashboard card in Streamlit.
    """
    st.markdown("### 🌾 Phase 8: Crop Portfolio & Soil Rotation Intelligence")
    st.caption("Evaluates portfolio diversity, soil nutrient pressure, and scenario stress resilience.")

    st.info(
        "💡 **Portfolio & Soil Intelligence Layer**: "
        "Evaluates the health, diversity, soil sustainability, and stress resilience of the optimized allocation. "
        "**This module does not optimize or modify allocations**; it audits the farm portfolio against "
        "deterministic diversity and nutrient pressure standards."
    )

    if optimization_result is None or not optimization_result.feasibility:
        st.warning("⚠️ Run the Phase 7 Optimizer above with a feasible farm plan to evaluate portfolio intelligence.")
        return

    # Check if scenarios are available in session
    scen_data = scenario_results
    if scen_data is None and "phase7_scenarios" in st.session_state:
        scen_data = st.session_state["phase7_scenarios"]

    # Generate Portfolio Report
    report: PortfolioAnalysisResult = generate_portfolio_report(
        optimization_result=optimization_result,
        scenario_results=scen_data,
    )

    # 1. Portfolio Summary Metrics
    st.markdown("#### 1. Portfolio Summary")
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Crops Used", f"{report.total_crops}")
    with col2:
        st.metric("Land Cultivated", f"{report.total_land_used_ha:.2f} ha")
    with col3:
        st.metric("Diversity Status", report.diversity_status.replace("_", " "), help=f"Shannon Diversity Index H' = {report.diversity_score:.4f}")
    with col4:
        res_display = report.resilience_status.replace("_", " ")
        res_help = f"Retention ratio = {report.resilience_score * 100:.1f}%" if report.resilience_score is not None else "Requires scenario comparisons"
        st.metric("Resilience Status", res_display, help=res_help)
    with col5:
        st.metric("Rotation Status", report.rotation_status, help="Status of repository crop rotation and family metadata")

    # 2. Detailed Diversity & Active Crop Distribution
    st.markdown("#### 2. Crop Diversity & Allocation Distribution")
    col_d1, col_d2 = st.columns([1, 2])
    with col_d1:
        st.metric("Shannon Diversity Index (H')", f"{report.diversity_score:.4f}")
        if report.diversity_status == "HIGH_DIVERSITY":
            st.success("🌟 **High Diversity**: Well-balanced multi-crop portfolio.")
        elif report.diversity_status == "MODERATE_DIVERSITY":
            st.info("⚖️ **Moderate Diversity**: Land shared across multiple crops.")
        else:
            st.warning("⚠️ **Low Diversity**: Single-crop dominance or monoculture risk.")

    with col_d2:
        if report.crop_entries:
            crop_df = pd.DataFrame([
                {
                    "Crop": e.crop_name.capitalize(),
                    "Allocated Area (ha)": f"{e.allocated_area_ha:.4f} ha",
                    "Portfolio Share (%)": f"{(e.allocated_area_ha / report.total_land_used_ha * 100):.1f}%" if report.total_land_used_ha > 0 else "0.0%"
                }
                for e in report.crop_entries
            ])
            st.dataframe(crop_df, use_container_width=True)
        else:
            st.write("No active crop allocations.")

    # 3. Soil Nutrient Pressure
    st.markdown("#### 3. Soil Nutrient Sustainability & Extraction Pressure")
    st.caption("Heuristic standards: ≥90% High Pressure (depletion risk), 60%–90% Moderate, <60% Low Pressure.")

    nut_data = report.nutrient_utilization_pct
    col_n1, col_n2, col_n3, col_n4 = st.columns(4)
    with col_n1:
        st.metric("Overall Pressure", report.nutrient_pressure_status.replace("_", " "))
    with col_n2:
        n_val = nut_data.get("nitrogen_kg")
        st.metric("Nitrogen (N) Utilization", f"{n_val:.1f}%" if n_val is not None else "N/A")
    with col_n3:
        p_val = nut_data.get("phosphorus_kg")
        st.metric("Phosphorus (P) Utilization", f"{p_val:.1f}%" if p_val is not None else "N/A")
    with col_n4:
        k_val = nut_data.get("potassium_kg")
        st.metric("Potassium (K) Utilization", f"{k_val:.1f}%" if k_val is not None else "N/A")

    # 4. Warnings & Risk Alerts
    st.markdown("#### 4. Portfolio Warnings & Vulnerabilities")
    if report.warnings:
        for w in report.warnings:
            st.warning(f"⚠️ {w}")
    else:
        st.success("✅ No critical portfolio vulnerabilities detected.")

    # 5. Farmer Explanation Layer
    st.markdown("#### 5. Farmer Decision Summary")
    st.info(f"📋 {report.explanation}")
