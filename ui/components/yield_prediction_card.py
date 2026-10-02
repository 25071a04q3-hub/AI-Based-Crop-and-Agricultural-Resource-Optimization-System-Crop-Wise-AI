"""
FarmTwin UI Component — Probabilistic Crop Yield Prediction Card.

Renders probabilistic crop yield estimates (P10 pessimistic, P50 expected, P90 optimistic)
or displays strict data honesty notices when model training is blocked due to the lack
of validated historical yield records.
"""
from typing import Optional
import streamlit as st
from engine.yield_prediction import YieldPredictionResult
from engine.crop_suitability import CropSuitabilityResult


def render_yield_prediction_card(
    yield_result: YieldPredictionResult,
    suitability_result: Optional[CropSuitabilityResult] = None,
) -> None:
    """
    Renders the Phase 4 probabilistic yield prediction card.
    Adheres strictly to the Dataset Decision Gate and Data Honesty rules.
    """
    st.markdown("### 📈 Probabilistic Crop Yield Estimation")
    st.caption("Distribution estimates: P10 (lower scenario), P50 (expected median), P90 (upper scenario).")

    # 1. Check if suitability warning is needed
    if suitability_result is not None:
        score_pct = suitability_result.suitability_score * 100
        if score_pct < 40.0:
            st.warning(
                f"⚠️ **Agronomic Suitability Warning**: {yield_result.crop_name.capitalize()} has low predicted suitability "
                f"({score_pct:.1f}%) for this farm's soil and climatic conditions."
            )
        else:
            st.success(
                f"🌱 Selected Crop: **{yield_result.crop_name.capitalize()}** "
                f"(Suitability Rank: #{suitability_result.rank} — {score_pct:.1f}% Match)"
            )

    # 2. Decision Gate Handling
    if yield_result.status == "BLOCKED_NO_HISTORICAL_DATASET":
        # Mandatory Data Honesty Notice (Section 17)
        st.error("🚫 **Probabilistic yield prediction is not yet available.**")
        st.info(
            "📋 **A validated historical yield dataset is required before the model can be trained.**\n\n"
            "In strict accordance with FarmTwin Data Honesty rules (Case B — Dataset Decision Gate):\n"
            "- The existing `data/raw/crop_recommendation.csv` is a suitability dataset with no historical yield figures.\n"
            "- The legacy 28-row prototype sample (`archive/yield_data.csv`) contains only 1 sample for 19 crops without temporal or spatial dimensions.\n"
            "- Model training is safely blocked to prevent misleading agricultural claims.\n"
            "- Fabricated P10, P50, and P90 numbers will not be shown."
        )

        with st.expander("🔍 Prospective Architecture & Dataset Audit Details", expanded=False):
            st.markdown("""
            **Target Yield Quantile Architecture:**
            * **P10 (Pessimistic Yield)**: 10th percentile estimate via Quantile Gradient Boosting (`loss='quantile'`, $\\alpha=0.10$).
            * **P50 (Expected Yield)**: 50th percentile median estimate via Quantile Gradient Boosting ($\\alpha=0.50$).
            * **P90 (Optimistic Yield)**: 90th percentile estimate via Quantile Gradient Boosting ($\\alpha=0.90$).
            * **Farm Production**: $\\text{Production (tonnes)} = \\text{Yield (t/ha)} \\times \\text{Farm Area (ha)}$.
            * **Quantile Monotonicity**: Enforces $P10 \\le P50 \\le P90$ to prevent quantile crossing.
            """)
            audit = yield_result.supporting_metrics.get("audit", {})
            if audit:
                st.markdown("**Dataset Audit Findings:**")
                st.write(f"- Candidate Filename: `{audit.get('filename')}`")
                st.write(f"- Total Rows: {audit.get('rows', 0)}")
                st.write(f"- Missing Values: {audit.get('missing_values', 0)}")
                st.write(f"- Duplicates: {audit.get('duplicates', 0)}")
                reasons = audit.get("disqualification_reasons", [])
                if reasons:
                    st.write("**Disqualification Reasons:**")
                    for r in reasons:
                        st.write(f"  • {r}")
        return

    # 3. Available Model Display (CASE A)
    st.info(
        "💡 **Prototype probabilistic estimate based on available historical yield data. Not a guaranteed harvest.**"
    )

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            label="P10 — Lower Yield Estimate",
            value=f"{yield_result.p10_yield_t_per_ha:.2f} t/ha",
            help="10th percentile yield scenario under adverse conditions"
        )
        if yield_result.farm_yield_p10_tonnes is not None:
            st.caption(f"🚜 Farm Production: **{yield_result.farm_yield_p10_tonnes:.2f} tonnes**")

    with c2:
        st.metric(
            label="P50 — Median Expected Yield",
            value=f"{yield_result.p50_yield_t_per_ha:.2f} t/ha",
            help="50th percentile median expected yield under observed conditions"
        )
        if yield_result.farm_yield_p50_tonnes is not None:
            st.caption(f"🚜 Farm Production: **{yield_result.farm_yield_p50_tonnes:.2f} tonnes**")

    with c3:
        st.metric(
            label="P90 — Upper Yield Estimate",
            value=f"{yield_result.p90_yield_t_per_ha:.2f} t/ha",
            help="90th percentile yield scenario under highly favorable conditions"
        )
        if yield_result.farm_yield_p90_tonnes is not None:
            st.caption(f"🚜 Farm Production: **{yield_result.farm_yield_p90_tonnes:.2f} tonnes**")

    if yield_result.prediction_interval_width is not None:
        st.caption(f"📊 Yield Uncertainty Spread (P90 - P10): **{yield_result.prediction_interval_width:.2f} t/ha**")

    with st.expander("🧪 Prototype Model Performance & Explainability", expanded=False):
        st.markdown(f"**Methodology**: {yield_result.methodology}")
        metrics = yield_result.supporting_metrics
        if metrics:
            st.markdown("**Prototype Dataset Performance**:")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("MAE", f"{metrics.get('mae', 'N/A')} t/ha")
            m2.metric("RMSE", f"{metrics.get('rmse', 'N/A')} t/ha")
            m3.metric("R²", f"{metrics.get('r2', 'N/A')}")
            m4.metric("Pinball Loss (P50)", f"{metrics.get('quantile_loss_p50', 'N/A')}")
        st.caption("Estimated yield is influenced by the farm's soil NPK, pH, rainfall, temperature, and selected crop species.")
