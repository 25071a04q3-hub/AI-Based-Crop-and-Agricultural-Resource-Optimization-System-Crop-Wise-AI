"""
FarmTwin UI Component — Future Scenario Simulator & Stress Testing Card.

Allows farmers to evaluate how single or multiple future scenarios
(e.g., Drought, Excess Rainfall, Water Shortage, Fertilizer Inflation, Market Crashes)
impact their farm parcel conditions and operational resources.
Adheres strictly to Phase 5 Data Honesty rules.
"""
from typing import Optional
import streamlit as st
import pandas as pd

from engine.profile import FarmProfile
from engine.scenario_simulator import (
    ScenarioDefinition,
    ScenarioResult,
    ScenarioStatus,
    get_predefined_scenarios,
    generate_random_scenarios,
    simulate_scenario,
    simulate_scenarios,
    compare_scenarios,
)


def render_scenario_simulator_card(
    profile: FarmProfile,
    selected_crop: Optional[str] = None
) -> None:
    """
    Renders the Phase 5 Future Scenario Simulator section in Streamlit.
    """
    st.markdown("### 🔮 Future Scenario Simulator & Farm Stress Testing")
    st.caption("Stress-test the farm profile across possible climate and macroeconomic futures.")

    st.info(
        "💡 **Multi-Future Stress Testing**: Evaluates how farm conditions transform under adverse shocks. "
        "Because Phase 4 historical yield data is pending, outcome predictions are transparently marked as "
        "`BLOCKED_NO_YIELD_MODEL`. No synthetic yields or fabricated profits are generated."
    )

    tab_single, tab_batch, tab_random = st.tabs([
        "🎯 Single Scenario Analysis",
        "📋 Standard Scenario Suite (7 Futures)",
        "🎲 Monte Carlo Stress Suite (100 Futures)",
    ])

    standard_scenarios = get_predefined_scenarios()
    scen_map = {s.scenario_name: s for s in standard_scenarios}

    # =========================================================================
    # TAB 1: Single Scenario Analysis
    # =========================================================================
    with tab_single:
        selected_name = st.selectbox(
            "Select Stress Scenario to Evaluate",
            options=list(scen_map.keys()),
            index=1,  # Default to Drought
            help="Choose from standardized agronomic stress scenarios"
        )
        active_scen = scen_map[selected_name]

        # Display Scenario Shock Specs
        st.markdown(f"**Scenario Description**: {active_scen.description}")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Rainfall Shock", f"{active_scen.rainfall_change_pct:+.1f}%")
        c2.metric("Irrigation Water Shock", f"{active_scen.water_change_pct:+.1f}%")
        c3.metric("Fertilizer Price Shock", f"{active_scen.fertilizer_price_change_pct:+.1f}%")
        c4.metric("Market Price Shock", f"{active_scen.market_price_change_pct:+.1f}%")

        if st.button("🚀 Evaluate Scenario Conditions", type="primary", key="btn_single_scen"):
            result = simulate_scenario(profile, active_scen, crop_name=selected_crop)

            st.markdown("#### 🌾 Adjusted Farm Parcel Conditions")
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric(
                "Adjusted Rainfall",
                f"{result.adjusted_rainfall_mm:.1f} mm" if result.adjusted_rainfall_mm is not None else "N/A",
                delta=f"{active_scen.rainfall_change_pct:+.1f}%"
            )
            col_b.metric(
                "Adjusted Usable Water",
                f"{result.adjusted_water_liters:,.0f} L" if result.adjusted_water_liters is not None else "N/A",
                delta=f"{active_scen.water_change_pct:+.1f}%"
            )
            col_c.metric(
                "Adjusted Temperature",
                f"{result.adjusted_temperature_c:.1f} °C" if result.adjusted_temperature_c is not None else "N/A",
                delta=f"{active_scen.temperature_change_c:+.1f} °C"
            )
            col_d.metric(
                "Fertilizer Cost Factor",
                f"{result.adjusted_fertilizer_price_factor:.2f}x",
                delta=f"{active_scen.fertilizer_price_change_pct:+.1f}%"
            )

            st.markdown("#### 📊 Scenario Outcome Evaluation")
            if result.status == ScenarioStatus.BLOCKED_NO_YIELD_MODEL:
                st.warning("⚠️ **Yield & Economic Evaluation Unavailable (Status: BLOCKED_NO_YIELD_MODEL)**")
                st.info(
                    "📋 **A validated historical yield dataset is required before future yield outcomes can be estimated.**\n\n"
                    "• The physical and economic conditions for this scenario were successfully generated and validated.\n"
                    "• No fake or guessed yield, production, revenue, or profit numbers are shown.\n"
                    "• Once historical yield data is integrated into Phase 4, probabilistic outcomes will automatically populate here."
                )
            elif result.status == ScenarioStatus.INVALID_SCENARIO:
                st.error(f"❌ **Invalid Scenario Rejected**: {result.explanation}")
            elif result.status == ScenarioStatus.READY:
                st.success("✅ **Scenario Yield Outcomes Evaluated**")
                # When future model is unblocked
                s1, s2, s3 = st.columns(3)
                s1.metric("P10 Yield", f"{result.yield_p10:.2f} t/ha")
                s2.metric("P50 Yield", f"{result.yield_p50:.2f} t/ha")
                s3.metric("P90 Yield", f"{result.yield_p90:.2f} t/ha")

    # =========================================================================
    # TAB 2: Standard Scenario Suite (7 Futures)
    # =========================================================================
    with tab_batch:
        st.markdown("#### Evaluate Standard 7-Scenario Stress Matrix")
        st.caption("Compares farm condition shifts across Baseline, Drought, Flood, Water Shortage, Fertilizer Shock, Market Crash, and Combined Stress.")

        if st.button("▶️ Run Standard Scenarios", type="primary", key="btn_run_suite"):
            results = simulate_scenarios(profile, standard_scenarios, crop_name=selected_crop)
            df_comp = compare_scenarios(results)

            st.dataframe(df_comp, use_container_width=True, hide_index=True)

            st.info(
                "ℹ️ **Understanding Status**: All scenarios report `BLOCKED_NO_YIELD_MODEL`. "
                "This indicates that scenario environmental transformations are functioning and validated, "
                "while outcome prediction is legitimately paused pending authentic historical yield data."
            )

    # =========================================================================
    # TAB 3: Randomized Monte Carlo Stress Suite
    # =========================================================================
    with tab_random:
        st.markdown("#### Generate Randomized Future Scenarios (Prototype Stress Testing)")
        st.caption("Generates reproducible Monte Carlo stress perturbations to test farm boundary resilience.")

        c_cnt, c_seed = st.columns(2)
        n_rand = c_cnt.slider("Number of Random Scenarios", min_value=10, max_value=500, value=100, step=10)
        seed_val = int(c_seed.number_input("Random Seed (Reproducibility)", min_value=0, max_value=99999, value=42))

        if st.button("🎲 Generate & Evaluate Random Scenarios", key="btn_run_random"):
            with st.spinner(f"Generating and evaluating {n_rand} randomized stress futures..."):
                rand_scens = generate_random_scenarios(n_scenarios=n_rand, random_state=seed_val)
                rand_results = simulate_scenarios(profile, rand_scens, crop_name=selected_crop)
                df_rand = compare_scenarios(rand_results)

                st.success(f"Generated {len(rand_results)} scenarios (Seed: {seed_val}). All physical bounds verified.")
                st.dataframe(df_rand.head(20), use_container_width=True, hide_index=True)
                st.caption(f"Showing first 20 of {len(df_rand)} randomized scenarios. 100% evaluated with strict boundary safety.")
