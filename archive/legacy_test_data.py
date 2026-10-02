import pytest
from data import revenue_per_ha, water_mm_to_m3_per_ha

def test_unit_conversions_worked_example():
    """
    Hand-Calculated Worked Example:
    -------------------------------
    - Yield: 4.5 tonnes/ha
    - Market Price: 2,200 INR/quintal
    - Price Conversion: 1 tonne = 10 quintals
    - Expected Revenue = 4.5 tonnes/ha * 10 quintals/tonne * 2,200 INR/quintal = 99,000 INR/ha
    
    Water Example:
    --------------
    - Applied Depth: 120 mm
    - Conversion: 1 mm over 1 ha = 10 m³/ha
    - Expected Volume = 120 * 10 = 1,200 m³/ha
    """
    yield_t_ha = 4.5
    price_q = 2200.0
    expected_revenue = 99000.0

    calculated_revenue = revenue_per_ha(yield_t_ha, price_q)
    assert calculated_revenue == pytest.approx(expected_revenue, abs=1e-3), \
        f"Expected {expected_revenue}, but got {calculated_revenue}"

    water_mm = 120.0
    expected_m3 = 1200.0
    calculated_m3 = water_mm_to_m3_per_ha(water_mm)
    assert calculated_m3 == pytest.approx(expected_m3, abs=1e-3), \
        f"Expected {expected_m3}, but got {calculated_m3}"

if __name__ == "__main__":
    pytest.main([__file__])