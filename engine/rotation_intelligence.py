"""
FarmTwin — Multi-Season Crop Rotation & Portfolio Intelligence Engine.

Future Responsibility:
- Evaluate multi-period crop sequencing, legume nitrogen-fixation benefits, and soil replenishment cycles.
- Enforce biological pest/disease break intervals across botanical plant families.
- Generate multi-season crop portfolio recommendations that maximize long-term soil health and financial resilience.
"""

# Re-export Phase 8 Portfolio Intelligence components
from engine.portfolio_intelligence import (
    CropPortfolioEntry,
    PortfolioAnalysisResult,
    analyze_portfolio_diversity,
    analyze_nutrient_pressure,
    analyze_rotation_compatibility,
    analyze_resilience,
    generate_portfolio_report,
)
