"""
FarmTwin UI Component — Executive Decision Summary & Explainability Card.

High-Aesthetic Executive HUD & Visual Decision Intelligence:
- Executive Decision Summary HUD (Feature 3)
- "WHY DID FARMTWIN MAKE THIS DECISION?" Visual Explainer (Feature 4)
- Farm Resource Balance Card Grid (Feature 6)
"""
from typing import Dict, Any, List
import streamlit as st
import pandas as pd


def render_executive_decision_summary(pipeline_out: Dict[str, Any]) -> None:
    """
    Renders a prominent, high-impact Executive Decision Summary card at the top of the dashboard.
    """
    profile = pipeline_out["profile"]
    opt = pipeline_out["opt_result"]
    suits = pipeline_out["suitability_results"]
    b_rep = pipeline_out["bottleneck_report"]
    a_rep = pipeline_out["adaptive_report"]
    p_rep = pipeline_out["portfolio_report"]

    top_crop = suits[0].crop_name.capitalize() if suits else "None"
    top_score = (suits[0].suitability_score * 100) if suits else 0.0
    top_level = suits[0].suitability_level if suits else "Unknown"

    land_used = opt.total_land_used_ha
    land_total = profile.land_area_ha
    land_pct = (land_used / land_total * 100) if land_total > 0 else 0.0

    prim_bottle = b_rep.primary_bottleneck.replace("_", " ").title() if b_rep.primary_bottleneck else "None"
    prim_util = b_rep.primary_bottleneck_utilization or 0.0

    # Format HUD Card
    trig_status_text = "PLAN STABLE" if a_rep.trigger_status == "PLAN_STABLE" else "REOPTIMIZATION NEEDED"
    trig_color = "#34d399" if a_rep.trigger_status == "PLAN_STABLE" else "#fbbf24"

    hud_html = f"""
<div style="background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(13, 33, 54, 0.92) 100%); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 18px; padding: 24px 28px; margin-bottom: 24px; box-shadow: 0 16px 36px -12px rgba(0, 0, 0, 0.6), 0 0 20px 0 rgba(14, 165, 233, 0.12); backdrop-filter: blur(16px);">
<div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 14px; margin-bottom: 20px;">
<div>
<span style="font-size: 0.72rem; letter-spacing: 1.5px; text-transform: uppercase; color: #38bdf8; font-weight: 700;">Executive Decision HUD</span>
<h3 style="margin: 2px 0 0 0; color: #f8fafc; font-size: 1.35rem; font-weight: 700; letter-spacing: -0.3px;">FARM DECISION SUMMARY</h3>
</div>
<div style="background: rgba(16, 185, 129, 0.12); border: 1px solid rgba(16, 185, 129, 0.35); border-radius: 9999px; padding: 6px 14px; display: flex; align-items: center; gap: 8px;">
<span style="width: 8px; height: 8px; border-radius: 50%; background-color: #34d399; box-shadow: 0 0 10px #34d399;"></span>
<span style="font-size: 0.8rem; font-weight: 700; color: #34d399; letter-spacing: 0.5px;">PARCEL OPTIMIZED</span>
</div>
</div>
<div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 16px;">
<div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px 18px;">
<div style="font-size: 0.75rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Recommended Crop</div>
<div style="font-size: 1.55rem; font-weight: 800; color: #38bdf8; margin: 4px 0 2px 0;">{top_crop}</div>
<div style="font-size: 0.8rem; color: #34d399; font-weight: 600;">{top_score:.1f}% Match <span style="color:#64748b;">({top_level})</span></div>
</div>
<div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px 18px;">
<div style="font-size: 0.75rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Optimized Land</div>
<div style="font-size: 1.55rem; font-weight: 800; color: #f8fafc; margin: 4px 0 2px 0;">{land_used:.2f} ha</div>
<div style="font-size: 0.8rem; color: #94a3b8; font-weight: 600;">{land_pct:.1f}% of {land_total:.2f} ha utilized</div>
</div>
<div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px 18px;">
<div style="font-size: 0.75rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Primary Bottleneck</div>
<div style="font-size: 1.55rem; font-weight: 800; color: {'#f87171' if prim_util >= 99.0 else '#fbbf24'}; margin: 4px 0 2px 0;">{prim_bottle}</div>
<div style="font-size: 0.8rem; color: {'#f87171' if prim_util >= 99.0 else '#fbbf24'}; font-weight: 600;">{prim_util:.1f}% Saturation {'(BINDING)' if prim_util >= 99.0 else ''}</div>
</div>
<div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 12px; padding: 14px 18px;">
<div style="font-size: 0.75rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Resilience & Diversity</div>
<div style="font-size: 1.55rem; font-weight: 800; color: {trig_color}; margin: 4px 0 2px 0;">{trig_status_text}</div>
<div style="font-size: 0.8rem; color: #a5b4fc; font-weight: 600;">Shannon Diversity: {p_rep.diversity_score:.2f} H'</div>
</div>
</div>
</div>
"""
    clean_hud = "\n".join(l.strip() for l in hud_html.splitlines() if l.strip())
    st.markdown(clean_hud, unsafe_allow_html=True)


def render_why_this_decision(pipeline_out: Dict[str, Any]) -> None:
    """
    Renders the Explainable Decision section (Feature 4).
    Dynamically articulates the causality behind FarmTwin's recommendation.
    """
    profile = pipeline_out["profile"]
    opt = pipeline_out["opt_result"]
    suits = pipeline_out["suitability_results"]
    b_rep = pipeline_out["bottleneck_report"]
    a_rep = pipeline_out["adaptive_report"]

    top_crop = suits[0].crop_name.capitalize() if suits else "None"
    top_score = (suits[0].suitability_score * 100) if suits else 0.0

    prim_bottle = b_rep.primary_bottleneck.replace("_", " ").title() if b_rep.primary_bottleneck else "None"
    prim_util = b_rep.primary_bottleneck_utilization or 0.0

    reserves = a_rep.reserve_summary
    lowest_res_name = "Water"
    lowest_res_pct = 0.0
    lowest_res_status = "CRITICAL"
    if reserves:
        sorted_res = sorted(reserves.items(), key=lambda x: x[1].get("reserve_pct", 100.0))
        lowest_res_name = sorted_res[0][0].replace("_", " ").title()
        lowest_res_pct = sorted_res[0][1].get("reserve_pct", 0.0)
        lowest_res_status = a_rep.critical_reserves.get(sorted_res[0][0], "HEALTHY")

    st.markdown("### 💡 Why Did FarmTwin Make This Decision?")
    st.caption("Verifiable, transparent causality derived directly from AI classification and continuous LP solver constraints.")

    why_html = f"""
<div style="display: flex; flex-direction: column; gap: 12px; margin-top: 10px; margin-bottom: 24px;">
<div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #38bdf8; border-radius: 0 10px 10px 0; padding: 12px 18px; border: 1px solid rgba(56, 189, 248, 0.12); border-left-width: 4px;">
<div style="color: #38bdf8; font-weight: 700; font-size: 0.88rem; margin-bottom: 3px;">🌾 1. AI Crop Suitability Match</div>
<div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.5;">
<strong>{top_crop}</strong> achieved the highest suitability score (<strong>{top_score:.1f}%</strong>) based on the parcel's soil chemistry (N={profile.nitrogen_n_kg_ha:.0f}, P={profile.phosphorus_p_kg_ha:.0f}, K={profile.potassium_k_kg_ha:.0f} kg/ha, pH={profile.ph:.1f}) and climate ({profile.temperature_c:.1f}°C, {profile.rainfall_mm:.0f}mm rainfall).
</div>
</div>
<div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #f87171; border-radius: 0 10px 10px 0; padding: 12px 18px; border: 1px solid rgba(248, 113, 113, 0.12); border-left-width: 4px;">
<div style="color: #f87171; font-weight: 700; font-size: 0.88rem; margin-bottom: 3px;">🛑 2. Binding Resource Ceiling</div>
<div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.5;">
<strong>{prim_bottle}</strong> is the dominant bottleneck at <strong>{prim_util:.1f}% capacity</strong>. Even though land or labour have surplus availability, the farm cannot physically expand without additional {prim_bottle}.
</div>
</div>
<div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #34d399; border-radius: 0 10px 10px 0; padding: 12px 18px; border: 1px solid rgba(52, 211, 153, 0.12); border-left-width: 4px;">
<div style="color: #34d399; font-weight: 700; font-size: 0.88rem; margin-bottom: 3px;">📐 3. Continuous Acreage Allocation</div>
<div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.5;">
The HiGHS simplex optimizer allocated <strong>{opt.total_land_used_ha:.2f} ha</strong> out of <strong>{profile.land_area_ha:.2f} ha</strong> total land across suitable candidates to maximize suitability-weighted land while guaranteeing feasibility across all 6 physical resource limits.
</div>
</div>
<div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #fbbf24; border-radius: 0 10px 10px 0; padding: 12px 18px; border: 1px solid rgba(251, 191, 36, 0.12); border-left-width: 4px;">
<div style="color: #fbbf24; font-weight: 700; font-size: 0.88rem; margin-bottom: 3px;">🛡️ 4. Buffer & Contingency Reserve</div>
<div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.5;">
The lowest resource buffer (<strong>{lowest_res_name}</strong>) is currently <strong>{lowest_res_status}</strong> ({lowest_res_pct:.1f}% reserve), warning of acute vulnerability to unexpected mid-season {lowest_res_name.lower()} deficits.
</div>
</div>
<div style="background: rgba(15, 23, 42, 0.6); border-left: 4px solid #a78bfa; border-radius: 0 10px 10px 0; padding: 12px 18px; border: 1px solid rgba(167, 139, 250, 0.12); border-left-width: 4px;">
<div style="color: #a78bfa; font-weight: 700; font-size: 0.88rem; margin-bottom: 3px;">🔄 5. Adaptation & Reoptimization Trigger</div>
<div style="color: #cbd5e1; font-size: 0.88rem; line-height: 1.5;">
<em>{a_rep.explanation}</em>
</div>
</div>
</div>
"""
    clean_why = "\n".join(l.strip() for l in why_html.splitlines() if l.strip())
    st.markdown(clean_why, unsafe_allow_html=True)


def render_farm_resource_balance(pipeline_out: Dict[str, Any]) -> None:
    """
    Renders the visual Farm Resource Balance sheet across 6 physical constraints (Feature 6).
    """
    profile = pipeline_out["profile"]
    opt = pipeline_out["opt_result"]
    b_rep = pipeline_out["bottleneck_report"]

    st.markdown("### ⚖️ Farm Resource Balance & Utilization")
    st.caption("Real-time balance sheet comparing allocated resource demand against total farm capacity.")

    resources = [
        ("Land Area", "land_ha", "ha", opt.total_land_used_ha, profile.land_area_ha, "🌍"),
        ("Irrigation Water", "water_liters", "L", opt.resource_usage.get("water_liters", 0.0), profile.available_water, "💧"),
        ("Nitrogen (N)", "nitrogen_kg", "kg", opt.resource_usage.get("nitrogen_kg", 0.0), profile.available_n_kg, "🧪"),
        ("Phosphorus (P)", "phosphorus_kg", "kg", opt.resource_usage.get("phosphorus_kg", 0.0), profile.available_p_kg, "⚡"),
        ("Potassium (K)", "potassium_kg", "kg", opt.resource_usage.get("potassium_kg", 0.0), profile.available_k_kg, "🪴"),
        ("Working Budget", "budget_inr", "₹", opt.resource_usage.get("budget_inr", 0.0), profile.available_budget_inr, "💰"),
    ]

    c_left, c_right = st.columns(2)
    for idx, (label, key, unit, used, capacity, icon) in enumerate(resources):
        col = c_left if idx % 2 == 0 else c_right
        util_pct = (used / capacity * 100.0) if capacity > 0 else 0.0
        reserve_pct = max(0.0, 100.0 - util_pct)

        if util_pct >= 99.0:
            badge_color = "#ef4444"
            badge_text = "BINDING (100%)"
            bar_color = "linear-gradient(90deg, #f87171, #ef4444)"
        elif util_pct >= 90.0:
            badge_color = "#f59e0b"
            badge_text = "NEAR-BINDING"
            bar_color = "linear-gradient(90deg, #fbbf24, #f59e0b)"
        elif util_pct >= 60.0:
            badge_color = "#38bdf8"
            badge_text = "ACTIVE"
            bar_color = "linear-gradient(90deg, #0ea5e9, #38bdf8)"
        else:
            badge_color = "#10b981"
            badge_text = "SURPLUS SLACK"
            bar_color = "linear-gradient(90deg, #059669, #10b981)"

        if unit == "₹":
            usage_str = f"₹{used:,.0f} / ₹{capacity:,.0f}"
        elif unit == "L":
            usage_str = f"{used:,.0f} L / {capacity:,.0f} L"
        else:
            usage_str = f"{used:.2f} {unit} / {capacity:.2f} {unit}"

        with col:
            st.markdown(f"""
            <div style="background: rgba(15, 23, 42, 0.65); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 14px 18px; margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <div style="font-weight: 700; color: #f1f5f9; font-size: 0.92rem; display: flex; align-items: center; gap: 8px;">
                        <span>{icon}</span> {label}
                    </div>
                    <div style="background: rgba({ '239, 68, 68' if util_pct >= 99.0 else ('245, 158, 11' if util_pct >= 90.0 else ('56, 189, 248' if util_pct >= 60.0 else '16, 185, 129')) }, 0.15); color: {badge_color}; border: 1px solid {badge_color}; border-radius: 6px; padding: 2px 8px; font-size: 0.72rem; font-weight: 700;">
                        {badge_text}
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #94a3b8; margin-bottom: 6px;">
                    <span>Demand: <strong style="color: #e2e8f0;">{usage_str}</strong></span>
                    <span>Reserve: <strong style="color: {'#ef4444' if reserve_pct < 1.0 else '#34d399'};">{reserve_pct:.1f}%</strong></span>
                </div>
                <div style="width: 100%; height: 8px; background: rgba(30, 41, 59, 0.8); border-radius: 9999px; overflow: hidden;">
                    <div style="width: {min(100.0, max(0.0, util_pct)):.1f}%; height: 100%; background: {bar_color}; border-radius: 9999px; transition: width 0.5s ease-in-out;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
