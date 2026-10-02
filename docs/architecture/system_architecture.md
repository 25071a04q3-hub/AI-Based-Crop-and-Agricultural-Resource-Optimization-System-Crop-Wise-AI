# FarmTwin — System Architecture Diagram

This document illustrates the high-level system architecture of the **FarmTwin — Adaptive Farm Decision Engine**, showing the relationships between UI presentation, analytical engine components, data layers, and solver engines.

```mermaid
graph TD
    subgraph UI_Layer ["Presentation & Interaction Layer (Streamlit ui/app.py)"]
        ProfileForm["Farm Profile Input Form"]
        SuitabilityCard["Crop Suitability Evaluation Card"]
        OptimizationCard["Resource Optimizer Card"]
        PortfolioCard["Portfolio & Soil Intelligence Card"]
        BottleneckCard["Bottleneck & Shadow Analysis Card"]
        ReserveCard["Adaptive Reserve & Recourse Card"]
    end

    subgraph Core_Engine ["FarmTwin Core Engine (engine/)"]
        P1["FarmProfile Validator (profile.py)"]
        P2["Crop Suitability Classifier (crop_suitability.py)"]
        P3["Probabilistic Yield Safeguard (yield_prediction.py)"]
        P4["Scenario Stress Simulator (scenario_simulator.py)"]
        P5["Resource Calculator (resource_calculator.py)"]
        P6["HiGHS LP Optimizer (optimizer.py)"]
        P7["Portfolio Intelligence (portfolio_intelligence.py)"]
        P8["Bottleneck Intelligence (bottleneck_analysis.py)"]
        P9["Adaptive Reserve Engine (adaptive_reserve.py)"]
    end

    subgraph Data_Config ["Configuration & Storage Layer"]
        CropData["Crop Benchmark Dataset (data/raw/crop_recommendation.csv)"]
        CropProfileJSON["Agronomic Crop Norms (config/crops_profile.json)"]
        TrainedModel["In-Memory Random Forest Classifier (_MODEL_CACHE)"]
    end

    subgraph External_Solver ["Mathematical Solver Backend"]
        SciPy["SciPy HiGHS Simplex Solver (C++)"]
    end

    ProfileForm -->|Validated Raw Inputs| P1
    CropData -->|Training| TrainedModel
    TrainedModel -->|Inference| P2
    P1 -->|Validated FarmProfile| P2
    P1 -->|Base FarmProfile| P4
    P2 -->|Suitability Scores| P6
    CropProfileJSON -->|Per-Hectare Demands| P5
    P5 -->|Constraint Matrix| P6
    P6 <-->|LP Matrix Formulation & Duals| SciPy
    P6 -->|Optimization Result| P7
    P6 -->|Optimization Result| P8
    P6 -->|Optimization Result| P9
    P1 -->|Farm Profile Context| P7
    P1 -->|Farm Profile Context| P8
    P1 -->|Farm Profile Context| P9

    P2 -.->|Results| SuitabilityCard
    P6 -.->|Results| OptimizationCard
    P7 -.->|Metrics| PortfolioCard
    P8 -.->|Insights| BottleneckCard
    P9 -.->|Buffers| ReserveCard
```
