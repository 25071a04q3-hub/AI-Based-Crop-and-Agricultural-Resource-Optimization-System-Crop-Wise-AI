"""
FarmTwin — Mid-Season Re-Optimization Engine.

Future Responsibility:
- Dynamically recalculate farm resource allocation and irrigation schedules mid-crop cycle.
- Ingest real-time weather anomalies (e.g., severe rainfall deficit at day 45) and update expected yields.
- Determine optimal recourse actions: deficit irrigation, sacrificial crop thinning, supplemental fertilization,
  or partial replanting to preserve farm solvency.
"""

# Re-export Phase 10 Adaptive Reserve & Mid-Season Re-Optimization symbols
from engine.adaptive_reserve import (
    ReoptimizationTriggerConfig,
    AdaptiveReserveResult,
    analyze_resource_reserves,
    identify_critical_reserves,
    evaluate_reoptimization_triggers,
    analyze_plan_stability,
    generate_adaptive_recommendations,
    simulate_resource_change,
    generate_adaptive_report,
)
