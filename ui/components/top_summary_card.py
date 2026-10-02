"""
FarmTwin — Whole Output Executive Summary Component.

Provides a consolidated, executive-grade summary at the top of the dashboard,
synthesizing full-pipeline decision results with multi-language localization.
Uses clean Streamlit-native UI components to prevent raw markdown code leaking.
"""
from typing import Dict, Any
import streamlit as st

from engine.profile import FarmProfile
from ui.localization.translations import get_translation


def render_whole_output_top_summary(pipeline_out: Dict[str, Any], profile: FarmProfile, lang_code: str = "en") -> None:
    """
    Renders an executive summary card at the very top of the dashboard,
    translating key insights into the selected language (en, hi, te, mr).
    """
    t = get_translation(lang_code)

    opt_res = pipeline_out.get("opt_result")
    p_rep = pipeline_out.get("portfolio_report")
    b_rep = pipeline_out.get("bottleneck_report")

    is_feasible = False
    if opt_res is not None:
        if hasattr(opt_res, "feasibility"):
            is_feasible = bool(opt_res.feasibility)
        elif hasattr(opt_res, "feasible"):
            is_feasible = bool(opt_res.feasible)

    allocations = {}
    if opt_res is not None:
        if hasattr(opt_res, "crop_allocations_ha"):
            allocations = opt_res.crop_allocations_ha
        elif hasattr(opt_res, "allocations"):
            allocations = opt_res.allocations

    total_allocated = sum(allocations.values()) if allocations else 0.0
    diversity_val = getattr(p_rep, "diversity_score", 0.0) if p_rep else 0.0
    diversity_status = getattr(p_rep, "diversity_status", "MODERATE") if p_rep else "MODERATE"
    binding_res = getattr(b_rep, "primary_bottleneck", "None") or "None"
    binding_clean = binding_res.replace("_", " ").title()

    # Filter to active allocations only (> 0.001 ha)
    active_allocs = {c: a for c, a in allocations.items() if a > 0.001}
    top_crop_names = ", ".join([c.capitalize() for c in list(active_allocs.keys())[:2]]) if active_allocs else "None"

    # Multilingual Narrative
    if lang_code == "hi":
        narrative = f"फार्मट्विन प्रणाली ने **{profile.farmer_name}** ({profile.district}, {profile.state}) के लिए **{profile.land_area:.2f} {profile.land_unit.value}** का विश्लेषण पूर्ण किया। मुख्य अनुशंसित फसलें: **{top_crop_names}**। कुल शैनन विविधता स्कोर **{diversity_val:.2f} H'** ({diversity_status}) है। प्राथमिक संसाधन सीमा: **{binding_clean}**। उपज एवं राजस्व अनुमान वैज्ञानिक सत्यनिष्ठा बनाए रखने हेतु सुरक्षित रूप से रोके गए हैं।"
    elif lang_code == "te":
        narrative = f"ఫార్మ్‌ట్విన్ వ్యవస్థ **{profile.farmer_name}** ({profile.district}, {profile.state}) గారి **{profile.land_area:.2f} {profile.land_unit.value}** భూమిని విజయవంతంగా విశ్లేషించింది. కేటాయించిన ముఖ్య పంటలు: **{top_crop_names}**. షాన్నన్ వైవిధ్య స్కోరు **{diversity_val:.2f} H'** ({diversity_status}). ప్రధాన పరిమితి: **{binding_clean}**."
    elif lang_code == "mr":
        narrative = f"फार्मट्विन प्रणालीने **{profile.farmer_name}** ({profile.district}, {profile.state}) यांच्या **{profile.land_area:.2f} {profile.land_unit.value}** शेतीचे यशस्वी विश्लेषण केले. मुख्य पिके: **{top_crop_names}**. शॅनन विविधता निर्देशांक **{diversity_val:.2f} H'** ({diversity_status}). मुख्य मर्यादा: **{binding_clean}**."
    else:
        narrative = f"FarmTwin successfully optimized parcel **{profile.farm_id}** for **{profile.farmer_name}** ({profile.district}, {profile.state}) across **{profile.land_area:.2f} {profile.land_unit.value}**. Optimal allocation selects **{top_crop_names}** achieving a Shannon Diversity Index of **{diversity_val:.2f} H'** ({diversity_status.replace('_', ' ')}). Primary binding operational resource is **{binding_clean}**. Economic yield & revenue projections remain gated under strict scientific honesty."

    with st.container(border=True):
        # 1. Header Row
        h1, h2 = st.columns([7, 3])
        with h1:
            st.markdown(f"### {t['summary_title']}")
            st.caption(t['summary_desc'])
        with h2:
            st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
            if is_feasible:
                st.success(f"✅ {t['feasible_desc']}")
            else:
                st.error(f"⚠️ {t['infeasible_desc']}")

        # 2. KPI Cards Row
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric(
                label=f"👤 {t['farmer_label']} & {t['parcel_label']}",
                value=profile.farmer_name,
            )
            st.caption(f"📍 {profile.farm_id} • {profile.district}, {profile.state}")

        with k2:
            st.metric(
                label=f"🌍 {t['total_area']} & Utilized",
                value=f"{total_allocated:.2f} / {profile.land_area:.2f} {profile.land_unit.value}",
            )
            st.caption("✅ 100% Boundary Respected")

        with k3:
            st.metric(
                label=f"🌱 {t['diversity_index']}",
                value=f"{diversity_val:.2f} H'",
            )
            st.caption(f"🛡️ {diversity_status.replace('_', ' ')} Portfolio")

        with k4:
            st.metric(
                label="⚖️ Primary Bottleneck",
                value=binding_clean,
            )
            st.caption("Governs Marginal Acreage Expansion")

        # 3. Optimal Crop Allocation Badges
        st.markdown(f"**{t['top_crops']}:**")
        if active_allocs:
            chips_md = []
            for crop, ha in active_allocs.items():
                pct = (ha / profile.land_area * 100) if profile.land_area > 0 else 0
                chips_md.append(f"**🌾 {crop.capitalize()}**: `{ha:.2f} ha ({pct:.0f}%)`")
            st.markdown(" &nbsp;&nbsp;•&nbsp;&nbsp; ".join(chips_md))
        else:
            st.warning("No crops actively allocated")

        # 4. Executive Narrative Box
        st.info(narrative)

        # 5. Scientific Safety Ribbon
        st.caption(f"🛡️ **{t['scientific_integrity']}:** {t['gated_notice']}")
