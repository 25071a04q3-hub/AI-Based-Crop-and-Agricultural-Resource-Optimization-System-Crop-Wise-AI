# FarmTwin — End-to-End Data Flow Diagram

This diagram traces the flow and transformations of data throughout the FarmTwin analytical pipeline, from raw user telemetry to actionable decision recommendations.

```mermaid
sequenceDiagram
    autonumber
    actor Farmer as Farmer / Agronomist
    participant UI as Streamlit UI
    participant Profile as FarmProfile Validator
    participant Suitability as AI Crop Suitability
    participant Simulator as Stress Simulator
    participant Calculator as Resource Calculator
    participant Optimizer as HiGHS LP Optimizer
    participant Intelligence as Decision Intelligence Layer

    Farmer->>UI: Input soil (N,P,K,pH), climate (temp, rain, hum), resources (land, water, budget)
    UI->>Profile: Construct & Validate FarmProfile
    Profile-->>UI: Return Validated Immutable Profile

    UI->>Suitability: Evaluate candidate crops across 22 classes
    Suitability-->>UI: Return Ranked Crop Suitability Scores + Limiting Factors

    opt Stress Scenario Exploration
        UI->>Simulator: Run 7 Climate/Cost Shocks
        Simulator-->>UI: Return Perturbed Suitabilities & Resilience Ratios
    end

    UI->>Calculator: Query per-hectare demands (water, budget, N, P, K)
    Calculator-->>Optimizer: Provide Crop Resource Coefficient Vectors

    UI->>Optimizer: Execute Resource-Constrained LP Optimization
    Optimizer->>Optimizer: Solve via SciPy HiGHS Simplex
    Optimizer-->>UI: Return Optimal Land Allocations, Slacks & Dual Variables

    UI->>Intelligence: Dispatch Allocation & Context to Intelligence Layer
    par Intelligence Pipeline
        Intelligence->>Intelligence: Portfolio Engine computes Shannon Index (H') & Soil Balance
        Intelligence->>Intelligence: Bottleneck Engine computes Binding Regimes & What-If Levers
        Intelligence->>Intelligence: Adaptive Reserve Engine computes Safety Margins & Shock Triggers
    end
    Intelligence-->>UI: Consolidated Farm Intelligence Report
    UI-->>Farmer: Interactive Visual Dashboard with Actionable Directives
```
