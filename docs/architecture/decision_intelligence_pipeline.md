# FarmTwin — Decision Intelligence Pipeline Diagram

This diagram visualizes how raw mathematical optimization outputs are enriched by the three post-optimization decision intelligence engines (Phases 8, 9, and 10).

```mermaid
flowchart LR
    OptResult["Optimization Output: Primal x*, Duals lambda*, Slacks"]
    Profile["Validated FarmProfile Context"]

    subgraph IntelligenceLayer ["Farm Decision Intelligence Triad"]
        subgraph Phase8 ["Phase 8: Portfolio Intelligence"]
            H["Shannon Diversity Index (H')"]
            SoilPres["Soil Nutrient Balance Ratio"]
            RotAudit["Crop Rotation Diagnostics"]
        end

        subgraph Phase9 ["Phase 9: Bottleneck Analysis"]
            Classify["Regime Classifier: Binding / Near-Binding / Slack"]
            DualNorm["Shadow Value Attribution (Duals)"]
            WhatIf["What-If Sensitivity Sweeps (+10%, +20%)"]
        end

        subgraph Phase10 ["Phase 10: Adaptive Reserve Engine"]
            Reserves["Safety Margin Tracker (Water, Budget)"]
            Triggers["Mid-Season Threshold Triggers"]
            Stability["Plan Stability Index (Recourse LP)"]
        end
    end

    subgraph FarmerActions ["Actionable Farmer Directives"]
        D1["Ecological Diversity Rating"]
        D2["Nutrient Exhaustion Warning"]
        D3["Top ROI Resource Investment Recommendation"]
        D4["Buffer Adequacy & Weather Risk Warning"]
    end

    OptResult --> Phase8
    Profile --> Phase8
    OptResult --> Phase9
    Profile --> Phase9
    OptResult --> Phase10
    Profile --> Phase10

    H --> D1
    SoilPres --> D2
    RotAudit --> D2
    Classify --> D3
    DualNorm --> D3
    WhatIf --> D3
    Reserves --> D4
    Triggers --> D4
    Stability --> D4
```
