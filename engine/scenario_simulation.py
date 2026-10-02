"""
FarmTwin — Weather & Market Scenario Simulation Engine.

Phase 5: Future Scenario Simulator & Farm Stress Testing Engine.
- Multi-future scenario definition (Baseline, Drought, Excess Rainfall, Water Shortage, Fertilizer Shock, Market Shock, Combined Stress).
- Transformed physical and economic farm conditions with boundary validation.
- Controlled reproducible randomized stress testing.
- Clean integration with Phase 2 FarmProfile, Phase 3 Suitability, and Phase 4 Yield Prediction.
"""

from engine.scenario_simulator import (
    ScenarioCategory,
    ScenarioStatus,
    ScenarioDefinition,
    ScenarioResult,
    get_predefined_scenarios,
    apply_scenario,
    generate_random_scenarios,
    generate_scenarios,
    simulate_scenario,
    simulate_scenarios,
    compare_scenarios,
)

__all__ = [
    "ScenarioCategory",
    "ScenarioStatus",
    "ScenarioDefinition",
    "ScenarioResult",
    "get_predefined_scenarios",
    "apply_scenario",
    "generate_random_scenarios",
    "generate_scenarios",
    "simulate_scenario",
    "simulate_scenarios",
    "compare_scenarios",
]
