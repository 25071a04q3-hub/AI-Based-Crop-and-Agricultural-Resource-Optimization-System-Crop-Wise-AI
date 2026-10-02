# FarmTwin — Repository Folder Structure

This diagram outlines the complete file and folder hierarchy of the FarmTwin repository.

```mermaid
graph TD
    Root["/ (FarmTwin Root)"]
    
    subgraph ConfigDir ["config/"]
        CropProfile["crops_profile.json"]
        RotationMatrix["crop_rotation_matrix.json"]
        RegionalDefaults["regional_defaults.json"]
    end
    
    subgraph DataDir ["data/raw/"]
        CropCSV["crop_recommendation.csv (2,200 rows)"]
    end
    
    subgraph EngineDir ["engine/"]
        E1["profile.py (FarmProfile)"]
        E2["crop_suitability.py (Random Forest)"]
        E3["yield_prediction.py (Quantile GBDT gate)"]
        E4["scenario_simulator.py (7 stress scenarios)"]
        E5["resource_calculator.py (Balance sheet)"]
        E6["optimizer.py (HiGHS LP simplex)"]
        E7["portfolio_intelligence.py (Shannon H')"]
        E8["bottleneck_analysis.py (Dual variables)"]
        E9["adaptive_reserve.py (Buffer margins & TVD)"]
        Facades["Facades (suitability, shadow, etc.)"]
    end
    
    subgraph UIDir ["ui/"]
        AppPy["app.py (Streamlit dashboard)"]
        UIComp["components/ (9 active cards, stubs)"]
        UILoc["localization/ (en, hi, te)"]
    end
    
    subgraph TestsDir ["tests/"]
        TestAll["172 passing test suites"]
    end
    
    subgraph DocsDir ["docs/"]
        ArchDoc["PROJECT_ARCHITECTURE.md"]
        ModDoc["MODULE_REFERENCE.md"]
        UserDoc["USER_GUIDE.md"]
        TechDoc["TECHNICAL_GUIDE.md"]
        TestDoc["TESTING_GUIDE.md"]
        ArchDir["architecture/*.md (Mermaid diagrams)"]
    end
    
    subgraph ArchiveDir ["archive/"]
        LegacyCropWise["Legacy CropWise AI Archive"]
    end

    Root --> ConfigDir
    Root --> DataDir
    Root --> EngineDir
    Root --> UIDir
    Root --> TestsDir
    Root --> DocsDir
    Root --> ArchiveDir
```
