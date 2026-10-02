# FarmTwin — Testing Architecture & Verification Guide

This document describes the test suite architecture, testing methodologies, test runner configurations, and verification procedures for **FarmTwin — Adaptive Farm Decision Engine**.

---

## 1. Test Suite Overview

FarmTwin maintains a comprehensive, deterministic automated test suite with **172 passing test cases** across all 10 architectural phases.

### Quick Execution
Execute all tests using `pytest`:
```bash
python -m pytest -q
```
To run tests with full verbose logs:
```bash
python -m pytest -v
```
To calculate test coverage:
```bash
python -m pytest --cov=engine --cov-report=term-missing
```

---

## 2. Test Structure & Phase Mapping

| Test File | Target Phase | Focus & Scope | Tests Passed |
| :--- | :--- | :--- | :--- |
| `tests/test_profile.py` | Phase 2 | Profile validation, field ranges, units, Pydantic type errors. | 16 |
| `tests/test_crop_suitability.py` | Phase 3 | RF classifier loading, probability normalization, ranking, limiting factors. | 18 |
| `tests/test_yield_prediction.py` | Phase 4 | Quantile estimation structure, `BLOCKED_NO_YIELD_MODEL` enforcement. | 12 |
| `tests/test_scenario_simulator.py` | Phase 5 | 7 stress scenario perturbations, Monte Carlo runs, resilience scores. | 16 |
| `tests/test_resource_calculator.py` | Phase 6 | Agronomic crop norms lookup, allocation demand aggregation, balance sheet. | 15 |
| `tests/test_optimizer.py` | Phase 7 | Continuous LP setup, HiGHS solver convergence, feasibility, bounds. | 22 |
| `tests/test_portfolio_intelligence.py` | Phase 8 | Shannon diversity $H'$, crop count, soil nutrient balance, rotation advisory. | 18 |
| `tests/test_bottleneck_analysis.py` | Phase 9 | Binding constraint detection, dual variables, $+10\%/+20\%$ What-If levers. | 24 |
| `tests/test_adaptive_reserve.py` | Phase 10 | Buffer margins, mid-season triggers, plan stability index, recourse shock. | 20 |
| `tests/test_pipeline_integration.py` | E2E Integration | Full pipeline execution from FarmProfile to AdaptiveReserve. | 11 |
| **Total** | **All Phases** | **Comprehensive Regression Suite** | **172** |

---

## 3. Testing Principles & Guidelines

### 3.1 Absolute Determinism
All optimization and simulation tests are configured with explicit random seeds and deterministic solver tolerances to prevent flaky tests in CI/CD pipelines.

### 3.2 Scientific Honesty Assertions
Unit tests strictly verify that:
- Yield predictions do NOT return unbacked synthetic values.
- Revenue or profit fields remain deactivated in `RESOURCE_ONLY` mode.
- Dual variables are tested as rate-of-change units rather than fabricated currency values.

### 3.3 Boundary & Edge Case Testing
Key edge cases validated in the test suite:
- Zero budget or water availability (must return clean infeasible or zero-allocation result without crashing).
- Tiny farm holdings ($0.05\text{ ha}$) and very large holdings ($1000\text{ ha}$).
- Highly alkaline ($\text{pH} > 9$) or acidic ($\text{pH} < 4$) soils.
- Single-crop domination triggers monoculture constraint ($x_i \le 0.6 \cdot A_{\text{total}}$).

---

## 4. Example Test Case

```python
def test_binding_constraint_detection():
    """Verify that a binding water constraint produces positive dual value and is detected."""
    profile = get_sample_water_constrained_profile()
    optimizer = FarmOptimizer()
    result = optimizer.optimize(profile, get_sample_crops())
    
    analyzer = BottleneckAnalysisEngine()
    report = analyzer.analyze_bottlenecks(result, profile)
    
    assert "water_liters" in report.binding_resources
    assert report.dual_values["water_liters"] > 0.0
    assert report.primary_bottleneck == "Water Capacity"
```
