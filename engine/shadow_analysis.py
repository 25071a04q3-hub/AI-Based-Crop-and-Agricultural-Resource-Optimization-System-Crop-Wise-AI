"""
FarmTwin — Resource Bottleneck & Shadow Value (Dual Variable) Analysis Engine.

Future Responsibility:
- Extract dual variables (shadow prices) from linear programming optimization solutions.
- Quantify the marginal financial value of relaxing specific resource constraints
  (e.g., "Adding 100 m³ of water increases farm net profit by ₹X; adding 10 kg of Nitrogen adds ₹0").
- Identify critical limiting bottlenecks and diagnose constraint infeasibilities with actionable relaxation advice.
"""

# Re-export Phase 9 Bottleneck & Shadow Value Intelligence symbols
from engine.bottleneck_analysis import (
    BottleneckAnalysisResult,
    analyze_resource_constraints,
    identify_primary_bottleneck,
    identify_secondary_bottlenecks,
    analyze_shadow_values,
    run_resource_sensitivity_analysis,
    rank_resource_levers,
    generate_bottleneck_report,
)
