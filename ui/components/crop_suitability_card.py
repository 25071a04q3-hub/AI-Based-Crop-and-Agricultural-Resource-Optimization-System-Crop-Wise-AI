"""
FarmTwin UI Component — Crop Suitability Card.

Renders ranked crop suitability predictions, prototype confidence levels,
lightweight driver explanations, and model transparency metrics.
"""
from typing import List, Dict, Any
import streamlit as st
from engine.crop_suitability import CropSuitabilityResult


def render_crop_suitability_results(
    results: List[CropSuitabilityResult],
    model_metrics: Dict[str, Any],
    top_n: int = 5
) -> None:
    """
    Renders ranked AI crop suitability outcomes in a structured farmer-friendly layout.
    """
    st.markdown("### 🌾 AI Crop Suitability Predictions")
    st.caption("Machine learning prediction based on farm soil chemistry and climatic conditions.")

    # Status / Disclaimer Banner
    st.info(
        "💡 **Prototype AI prediction — not a guaranteed crop outcome.** "
        "Suitability is predicted from the farm's soil, weather, and available training data."
    )

    if not results:
        st.warning("No crop suitability predictions available.")
        return

    # 1. Summary Cards for Top Matches
    display_results = results[:top_n]
    
    # Render table / list of ranked crops
    for r in display_results:
        # Badge color / style based on level
        if r.suitability_level == "Highly Suitable":
            level_badge = "🟢 **Highly Suitable**"
        elif r.suitability_level == "Suitable":
            level_badge = "🔵 **Suitable**"
        elif r.suitability_level == "Moderately Suitable":
            level_badge = "🟡 **Moderately Suitable**"
        else:
            level_badge = "⚪ **Low Suitability**"

        with st.container():
            c1, c2, c3 = st.columns([1, 4, 3])
            c1.markdown(f"### #{r.rank}")
            
            with c2:
                st.markdown(f"**{r.crop_name.capitalize()}** — {level_badge}")
                st.caption(r.explanation)

            with c3:
                pct = r.suitability_score * 100
                st.metric(
                    label=f"Suitability Score",
                    value=f"{pct:.1f}%",
                    help=f"Raw model probability: {r.model_probability:.4f}"
                )
                st.progress(min(1.0, max(0.0, r.suitability_score)))

            # Expandable agronomic metadata details
            meta = r.supporting_features.get("crop_metadata", {})
            if meta:
                with st.expander(f"ℹ️ Agronomic Profile for {r.crop_name.capitalize()}", expanded=False):
                    m1, m2, m3 = st.columns(3)
                    duration = meta.get("duration_days", "N/A")
                    water = meta.get("water_req_mm", "N/A")
                    cost = meta.get("cost_per_ha", "N/A")
                    m1.metric("Est. Duration", f"{duration} days" if duration != "N/A" else "N/A")
                    m2.metric("Water Need", f"{water} mm" if water != "N/A" else "N/A")
                    m3.metric("Cost Baseline", f"₹{cost:,.0f}/ha" if isinstance(cost, (int, float)) else "N/A")

            st.markdown("---")

    # 2. Transparent Model Diagnostics (Expander)
    with st.expander("🧪 Prototype Model Performance & Global Drivers", expanded=False):
        st.markdown("**Prototype Dataset Performance (22-Crop Benchmark)**")
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Model Accuracy", f"{model_metrics.get('accuracy', 0.0) * 100:.1f}%")
        d2.metric("Weighted F1", f"{model_metrics.get('f1', 0.0):.4f}")
        d3.metric("Macro F1", f"{model_metrics.get('f1_macro', 0.0):.4f}")
        d4.metric("Algorithm", "Random Forest (100 trees)")

        importances = model_metrics.get("feature_importances", {})
        if importances:
            st.markdown("**Global Feature Importance Ranking**:")
            sorted_imp = sorted(importances.items(), key=lambda x: x[1], reverse=True)
            cols = st.columns(len(sorted_imp))
            for col, (feat, val) in zip(cols, sorted_imp):
                col.metric(feat.capitalize(), f"{val * 100:.1f}%")
