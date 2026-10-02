# Phase 11A — Historical Yield Data Readiness Report

**Project**: FarmTwin — Adaptive Farm Decision Engine  
**Milestone**: Phase 11A — Historical Agricultural Yield Data Acquisition & Validation  
**Execution Type**: Research & Data Architecture Verification (Zero Engine Modifications)  
**Date**: October 2026  
**Status**: COMPLETE — DATA GATE AUDITED  

---

## 1. Current FarmTwin State

FarmTwin Phases 1 through 10 have been functionally verified, audited, and hardened on the `main` branch. The codebase exhibits strict mathematical and data-honesty integrity:

1. **AI Crop Suitability**: Operational via a 2,200-row Random Forest classifier (`data/raw/crop_recommendation.csv`) evaluating 22 crops across N, P, K, pH, rainfall, temperature, and humidity.
2. **Crop Yield Engine**: Explicitly and safely gated (`BLOCKED_NO_HISTORICAL_DATASET`) in `engine/yield_prediction.py`. Returns structured `YieldPredictionResult` with `p10=None, p50=None, p90=None`.
3. **Future Scenario Simulator**: 7 stress scenarios (baseline, severe drought, heatwave, delayed monsoon, groundwater depletion, input cost spike, combined climate shock) adjusting physical yields by scalar multipliers when yield exists.
4. **Farm Optimization Engine**: SciPy HiGHS simplex solver operating in `RESOURCE_ONLY` mode (suitability-weighted hectares), strictly outputting `expected_profit_inr = None`.
5. **Crop Rotation Intelligence**: Returns `status = "DATA_UNAVAILABLE"` due to unvalidated multi-season rotational matrices.
6. **Automated Test Suite**: 172/172 automated unit and integration tests passing with 0 failures, 0 skips.

---

## 2. Existing Historical Data Audit

A repository-wide physical audit was conducted across `data/`, `data/raw/`, `archive/`, and `config/`:

| File Path | Rows | Columns | Crop Coverage | Spatial Coverage | Temporal Coverage | Usable for Modeling? | Active Engine Usage |
|---|---|---|---|---|---|---|---|
| `data/raw/crop_recommendation.csv` | 2,200 | 8 (`N, P, K, temperature, humidity, ph, rainfall, label`) | 22 crops (100 rows each) | None (no state or district) | None (no year or date) | **NO** (Suitability features only; zero yield observations) | Active in `engine/crop_suitability.py` |
| `archive/yield_data.csv` | 28 (header + 27 data lines) | 9 (`crop, N, P, K, temperature, humidity, ph, rainfall, yield_t_per_ha`) | 22 crops (19 crops have 1 sample; rice has 3, maize 3, chickpea 2) | None (no location tags) | None (no timestamps or years) | **NO** (Toy prototype; statistically degenerate sample size) | Audited as candidate path in `engine/yield_prediction.py` and disqualified |
| `archive/crop_recommendations.csv` | 48 | 8 (`N, P, K, temperature, humidity, ph, rainfall, label`) | 22 crops (1-3 rows each) | None | None | **NO** (Truncated prototype subset) | Legacy archive only |
| `data/raw/historical_yield.csv` | **0 (File does not exist)** | N/A | N/A | N/A | N/A | N/A | Target path for Phase 11 |

### Audit Findings on Existing Data
- The repository contains **zero valid historical yield observations**.
- The legacy file `archive/yield_data.csv` was audited by `audit_and_validate_yield_dataset()` and triggered 4 disqualification gates:
  1. Sample count (27 data rows) fails the minimum threshold of $\ge 200$ rows.
  2. 19 crops contain only 1 sample, failing the $\ge 15$ observations per crop threshold.
  3. Complete lack of temporal time series (`year` or `date`).
  4. Complete lack of geographic coordinates or administrative units (`state`, `district`).

---

## 3. Required Data Contract for FarmTwin

To unblock Phase 4 probabilistic yield estimation (`P10`, `P50`, `P90` quantile regression) without violating data-honesty rules, candidate historical datasets must satisfy the following technical contract:

### Minimum Schema Specification
- `year`: (integer) Multi-year agricultural recording (minimum 5–10 years to capture climatic variance).
- `state`: (string) Administrative state identifier (e.g., "Telangana", "Punjab", "Maharashtra").
- `district`: (string) Administrative district identifier (e.g., "Warangal", "Ludhiana", "Nashik").
- `crop`: (string) Standardized crop name matching or mappable to FarmTwin's 22 candidate crops.
- `season`: (string) Agricultural season ("Kharif", "Rabi", "Summer/Zaid", "Whole Year").
- `area_ha`: (float) Net cultivated area in hectares ($> 0.0$).
- `production_tonnes`: (float) Total production harvested in metric tonnes.
- `yield_t_per_ha`: (float) Yield in metric tonnes per hectare ($\text{t/ha}$). Either directly reported or deterministically derived as $\text{production\_tonnes} / \text{area\_ha}$.

### Statistical & Methodological Requirements
- **Sample Density**: $\ge 200$ total records, with $\ge 15$ (preferably $\ge 50$) observations per candidate crop across diverse years and districts.
- **Unit Homogeneity**: Area strictly in hectares, production in metric tonnes, yield in tonnes/ha. (Crops like coconut reported in thousands of nuts require explicit conversion factors or unit-specific scaling).
- **Temporal & Spatial Variation**: Sufficient spread across years (capturing drought, flood, and normal monsoons) and districts (capturing soil and agro-climatic zone differences).
- **Official Provenance**: Published by recognized national/state agricultural statistical agencies or accredited CGIAR research institutes.

---

## 4. Candidate Data Sources

A systematic investigation of authentic Indian agricultural data repositories was conducted:

| Source | Organization | Years Available | Geographic Level | Crops Covered | Total Records | Yield Availability | Provenance Credibility | Status |
|---|---|---|---|---|---|---|---|---|
| **District-Wise Season-Wise Crop Production Statistics (APY)** | Directorate of Economics and Statistics (DES), Ministry of Agriculture & Farmers Welfare, GoI | 1997–2015 (classic) / 2019+ (UPAg) | District-level (500+ districts across 36 States/UTs) | 124+ crops (covers 20+ FarmTwin crops) | ~246,091 rows | Derived ($\text{Production} / \text{Area}$) | **Official Government Statistical Authority** (data.gov.in / aps.dac.gov.in) | **PARTIALLY_SUITABLE** (Primary Acquisition Target) |
| **ICRISAT District Level Database (DLD)** | International Crops Research Institute for the Semi-Arid Tropics (ICRISAT) & Tata-Cornell Institute | 1966–2017 (50+ years longitudinal) | District-level (311 apportioned districts across 19 States) | 20+ major crops (cereals, pulses, oilseeds, cotton) | ~15,000+ district-year records | Direct ($\text{kg/ha}$) & Derived | **Accredited CGIAR International Institute** | **PARTIALLY_SUITABLE** (Secondary / Cross-Validation Target) |
| **Comprehensive Scheme on Cost of Cultivation (CACP)** | Commission for Agricultural Costs and Prices (CACP), MoA&FW | 2000–2024 (Annual reports) | State-level aggregate | 22 mandated MSP crops | ~1,500 state-year records | Direct ($\text{Quintal/ha}$) | **Statutory Government Advisory Body** | **REJECTED for District Yield** (Lacks district granularity; reserved for economic costs) |
| **RBI Handbook of Statistics on Indian Economy** | Reserve Bank of India (RBI) | 1980–2023 | State-level only | Major field crops | ~3,000 state-year records | Direct ($\text{kg/ha}$) | **Central Bank Statistical Division** | **REJECTED for District Yield** (State-level only; no district variance) |
| **Legacy Prototype (`archive/yield_data.csv`)** | Legacy hackathon repository | None | None | 22 crops | 28 rows | Direct synthetic | **Unverified / Toy Prototype** | **REJECTED** (Statistically disqualified) |

---

## 5. Detailed Validation of Serious Candidates

### Candidate A: Directorate of Economics & Statistics (DES) APY Dataset
- **Portal & Identifier**: Open Government Data Platform India (`data.gov.in/catalog/district-wise-season-wise-crop-production-statistics`) & APS Portal (`aps.dac.gov.in/APY/Index.htm`).
- **Schema**: `State_Name`, `District_Name`, `Crop_Year`, `Season`, `Crop`, `Area`, `Production`.
- **Row Count**: 246,091 records in the standard multi-year release.
- **Coverage**: 36 States/UTs, 500+ districts, 1997 through 2015+.
- **FarmTwin Crop Overlap**:
  - Cereals: Rice, Maize.
  - Pulses: Chickpea (Gram), Pigeonpeas (Arhar/Tur), Mungbean (Moong), Blackgram (Urad), Lentil (Masur), Mothbeans.
  - Commercial/Cash: Cotton (lint), Jute, Coffee, Coconut.
  - Fruits/Horticulture: Banana, Mango, Papaya, Apple, Grapes, Orange. (Note: Muskmelon and Watermelon are grouped under minor cucurbits in some states).
- **Yield Calculation**: Deterministic: $\text{yield\_t\_per\_ha} = \frac{\text{Production (tonnes)}}{\text{Area (hectares)}}$.
- **Known Quality Artifacts**:
  1. *Missing Production*: Approximately 3,730 records have valid `Area` but `Production = NaN` (mostly due to crop loss or pending reporting).
  2. *Coconut Unit Anomaly*: Coconut production is recorded in numbers/thousands of nuts, not metric tonnes. Requires either separate handling or exclusion of nuts-measured tree crops.
  3. *Zero Area Division*: Records where `Area == 0` must be filtered prior to computing yield.
- **License**: Government Open Data License — India (GODL-India). Permitted for open research, educational, and computational usage with attribution.

### Candidate B: ICRISAT District Level Database (DLD)
- **Portal & Identifier**: `http://data.icrisat.org/dld/` (ICRISAT Dataverse).
- **Schema**: `State_Code`, `State_Name`, `Dist_Code`, `District_Name`, `Year`, `Crop_Area_1000ha`, `Crop_Production_1000t`, `Crop_Yield_kg_ha`.
- **Row Count**: ~15,000+ rows spanning 1966 to 2017.
- **Coverage**: 19 major agricultural states, 311 1966-apportioned districts (ensuring spatial consistency despite district bifurcations).
- **FarmTwin Crop Overlap**: Excellent coverage of dryland field crops: Rice, Maize, Chickpea, Pigeonpea, Blackgram, Mungbean, Cotton. Zero coverage for temperate/horticultural fruits (Apple, Banana, Grapes, Papaya, Coffee).
- **Yield Calculation**: Direct reporting in $\text{kg/ha}$; easily normalized by dividing by 1,000 to reach $\text{t/ha}$.
- **License**: Creative Commons Attribution 4.0 International (CC BY 4.0).

---

## 6. FarmTwin Compatibility & Architectural Impact

Evaluating Candidate A (DES APY) against the downstream FarmTwin pipeline:

```
[DES APY Raw Data] 
       ↓ (ETL Pipeline: Clean NaN, derive yield, map crop names)
[data/raw/historical_yield.csv]
       ↓ (Quantile Gradient Boosting: alpha=0.10, 0.50, 0.90)
[P10 / P50 / P90 Yield Distributions]
       ↓ (Scenario Multipliers)
[Scenario Simulation Engine]
       ↓ (Resource Multipliers)
[Resource-Aware Optimizer]
```

### Evaluation Criteria
1. **Temporal Variation**: Supported. Spanning 18+ agricultural years, capturing historical climate shocks (e.g., 2002 and 2009 all-India drought years, 2010 normal monsoon).
2. **Geographic Variation**: Supported. 500+ districts provide distinct agro-climatic conditions matching `FarmProfile.district` and `FarmProfile.state`.
3. **Season Variation**: Supported. Explicit segmentation into `Kharif`, `Rabi`, and `Summer` matches `FarmProfile.season`.
4. **Training/Validation Splitting**: Supported. Ample sample size ($\ge 200$ rows per major crop) permits temporal train-test splits (e.g., train on 1997–2010, evaluate on 2011–2015).
5. **Yield Uncertainty (P10/P50/P90)**: Supported. Quantile regression (`GradientBoostingRegressor(loss='quantile')`) can extract authentic non-parametric variance across district-year observations.
6. **FarmProfile Integration**:
   - `FarmProfile` already contains `state`, `district`, and `season`.
   - Candidate models can condition on `(crop, state, district, season)` or agro-climatic clusters.
   - Soil N, P, K and weather features from `crop_recommendation.csv` do not exist in DES APY. Therefore, a hybrid or two-stage model (Suitability Filter $\rightarrow$ Regional Historical Quantile Yield) is mathematically required.

---

## 7. Data Quality & Integrity Risks

Before any data ingestion occurs in future phases, the following risks must be managed:

1. **Measurement Units for Tree/Plantation Crops**:
   - Coconut and certain fruit crops are tracked in count units rather than tonnes. Ingesting raw values without unit harmonization would distort quantile yield predictions by a factor of 1,000.
2. **Missing Production Records**:
   - ~1.5% of rows contain unrecorded production. Imputing values or treating them as zero yield without verification introduces bias. Rows with missing production must be explicitly logged and pruned.
3. **District Boundary Evolution**:
   - India expanded from 500 to 700+ districts between 1997 and 2024. A lookup dictionary mapping bifurcated districts to parent districts is required to prevent prediction dropouts.
4. **Outlier Reporting Errors**:
   - Historical survey datasets occasionally contain extreme typographical errors (e.g., yield $> 500\text{ t/ha}$ for cereals). Strict agronomic biological caps (e.g., Rice yield $< 15\text{ t/ha}$) must be enforced.

---

## 8. Final Decision Gate

In accordance with Section 6 of the Phase 11A Specification:

### Verdict: **PARTIALLY_SUITABLE**

### Objective Evidence & Rationale:
1. **Authentic External Source Verified**: The Directorate of Economics and Statistics (DES), Ministry of Agriculture & Farmers Welfare, Government of India published APY dataset meets all authentic provenance, volume ($\ge 200,000$ rows), multi-year temporal, and district-level spatial requirements.
2. **Current Repository Status**: The physical file `data/raw/historical_yield.csv` does **NOT** yet exist in the repository. The existing file `archive/yield_data.csv` remains disqualified.
3. **Data Pre-processing Prerequisite**: The raw government data requires a deterministic, scripted ETL pipeline to:
   - download the official release,
   - filter null production records and `Area == 0`,
   - map crop nomenclature to FarmTwin tokens,
   - derive and validate $\text{yield\_t\_per\_ha}$,
   - filter or convert non-standard units (e.g., Coconut).
4. **Zero Engine Modifications Preserved**: Under Phase 11A research constraints, no production engine code or data files were modified. Therefore, the status is **PARTIALLY_SUITABLE** pending the formal Phase 11B acquisition and normalization pipeline.

---

## 9. Recommended Next Action

**RECOMMENDED NEXT PHASE**: **Phase 11B — Deterministic Acquisition & Normalization Pipeline**

### Action Plan for Phase 11B:
1. Implement a standalone data acquisition script (`scripts/acquire_historical_yield.py`) that retrieves the verified DES APY dataset from the official government repository.
2. Deterministically clean and normalize the schema into `data/raw/historical_yield.csv`:
   - Columns: `crop, year, state, district, season, area_ha, production_tonnes, yield_t_per_ha`
   - Filter `area_ha > 0` and `production_tonnes > 0`
   - Map DES crop names to FarmTwin 22-crop tokens
   - Apply agronomic upper-bound sanity filters per crop family
3. Run `audit_and_validate_yield_dataset()` to verify that `data/raw/historical_yield.csv` passes all 5 validation gates.
4. Only upon gate validation, train `GradientBoostingRegressor` quantile models ($\alpha = 0.10, 0.50, 0.90$) and transition `engine/yield_prediction.py` status from `BLOCKED_NO_HISTORICAL_DATASET` to `AVAILABLE`.

---
*Report certified under FarmTwin Phase 11A Data Verification Protocol.*
