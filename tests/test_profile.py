"""
Test Suite: Farm Profile & Input Validation Engine.
Covers Section 23 requirements for Phase 2.
"""
import pytest
from pydantic import ValidationError
from engine.profile import (
    FarmProfile,
    LandUnit,
    WaterUnit,
    Season,
    get_demo_farm_profile,
    format_validation_errors,
    HECTARES_PER_ACRE,
    LITERS_PER_M3,
)


def create_base_profile_dict():
    """Helper returning a valid profile dictionary."""
    return {
        "farm_id": "FARM-TEST-01",
        "farmer_name": "Ramesh Kumar",
        "state": "Andhra Pradesh",
        "district": "Kurnool",
        "latitude": 15.8281,
        "longitude": 78.0373,
        "land_area": 4.0,
        "land_unit": "hectare",
        "nitrogen_n_kg_ha": 65.0,
        "phosphorus_p_kg_ha": 35.0,
        "potassium_k_kg_ha": 45.0,
        "ph": 7.2,
        "temperature_c": 29.5,
        "humidity_percent": 60.0,
        "rainfall_mm": 120.0,
        "available_water": 50000.0,
        "water_unit": "liter",
        "available_n_kg": 200.0,
        "available_p_kg": 100.0,
        "available_k_kg": 80.0,
        "available_budget_inr": 150000.0,
        "available_labour_days": 120.0,
        "season": "kharif",
        "year": 2026,
        "risk_tolerance": 0.4,
    }


# -------------------------------------------------------------
# Test 1 — Valid Profile
# -------------------------------------------------------------
def test_valid_profile_accepted():
    data = create_base_profile_dict()
    profile = FarmProfile(**data)
    assert profile.farm_id == "FARM-TEST-01"
    assert profile.land_area == 4.0
    assert profile.land_unit == LandUnit.HECTARE
    assert profile.land_area_ha == 4.0
    assert profile.water_liters == 50000.0
    assert profile.season == Season.KHARIF


# -------------------------------------------------------------
# Test 2 — Invalid Land Area
# -------------------------------------------------------------
def test_invalid_land_area_fails():
    data = create_base_profile_dict()
    data["land_area"] = -1.0
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Land area must be greater than 0" in e for e in errors)

    data["land_area"] = 0.0
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Land area must be greater than 0" in e for e in errors)


# -------------------------------------------------------------
# Test 3 — Acre Conversion (1 acre ≈ 0.404686 hectare)
# -------------------------------------------------------------
def test_acre_to_hectare_conversion():
    data = create_base_profile_dict()
    data["land_area"] = 1.0
    data["land_unit"] = "acre"
    profile = FarmProfile(**data)
    assert profile.original_land_area == 1.0
    assert profile.original_land_unit == "acre"
    assert profile.land_area_ha == pytest.approx(HECTARES_PER_ACRE, abs=1e-5)

    # 5 acres worked example
    data["land_area"] = 5.0
    profile_5ac = FarmProfile(**data)
    assert profile_5ac.land_area_ha == pytest.approx(5.0 * 0.404686, abs=1e-4)


# -------------------------------------------------------------
# Test 4 — Water Conversion (1 m³ = 1,000 liters)
# -------------------------------------------------------------
def test_water_m3_to_liters_conversion():
    data = create_base_profile_dict()
    data["available_water"] = 100.0
    data["water_unit"] = "m3"
    profile = FarmProfile(**data)
    assert profile.original_water_amount == 100.0
    assert profile.original_water_unit == "m3"
    assert profile.water_liters == pytest.approx(100.0 * LITERS_PER_M3, abs=1e-3)
    assert profile.water_liters == 100000.0


# -------------------------------------------------------------
# Test 5 — Invalid Humidity
# -------------------------------------------------------------
def test_invalid_humidity_fails():
    data = create_base_profile_dict()
    data["humidity_percent"] = 150.0
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Humidity must be between 0 and 100%" in e for e in errors)

    data["humidity_percent"] = -5.0
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Humidity must be between 0 and 100%" in e for e in errors)


# -------------------------------------------------------------
# Test 6 — Invalid pH
# -------------------------------------------------------------
def test_invalid_ph_fails():
    data = create_base_profile_dict()
    data["ph"] = 15.0
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Soil pH must be between 0 and 14" in e for e in errors)

    data["ph"] = -1.0
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Soil pH must be between 0 and 14" in e for e in errors)


# -------------------------------------------------------------
# Test 7 — Invalid Risk Tolerance
# -------------------------------------------------------------
def test_invalid_risk_tolerance_fails():
    data = create_base_profile_dict()
    data["risk_tolerance"] = 1.5
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Risk tolerance must be between 0 and 1" in e for e in errors)

    data["risk_tolerance"] = -0.1
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Risk tolerance must be between 0 and 1" in e for e in errors)


# -------------------------------------------------------------
# Test 8 — Serialization / Deserialization
# -------------------------------------------------------------
def test_profile_serialization():
    original = FarmProfile(**create_base_profile_dict())
    
    # 1. Dict round-trip
    dumped_dict = original.model_dump()
    reconstructed_from_dict = FarmProfile.model_validate(dumped_dict)
    assert reconstructed_from_dict.farm_id == original.farm_id
    assert reconstructed_from_dict.land_area_ha == original.land_area_ha
    assert reconstructed_from_dict.water_liters == original.water_liters

    # 2. JSON string round-trip
    json_str = original.model_dump_json()
    reconstructed_from_json = FarmProfile.model_validate_json(json_str)
    assert reconstructed_from_json.farm_id == original.farm_id
    assert reconstructed_from_json.land_area_ha == original.land_area_ha
    assert reconstructed_from_json.water_liters == original.water_liters

    # 3. Normalized export
    normalized = original.to_normalized()
    assert normalized["farm_id"] == "FARM-TEST-01"
    assert normalized["land"]["normalized_area_ha"] == 4.0
    assert normalized["resources"]["normalized_water_liters"] == 50000.0


# -------------------------------------------------------------
# Test 9 — Demo Profile Factory
# -------------------------------------------------------------
def test_demo_profile_generation():
    demo = get_demo_farm_profile()
    assert demo.farm_id == "FARM-001"
    assert demo.is_demo is True
    assert demo.land_area_ha == 2.0
    assert demo.water_liters == 100000.0
    assert demo.season == Season.KHARIF
    assert demo.year == 2026
    assert demo.risk_tolerance == 0.5

    # Check normalized export
    norm = demo.to_normalized()
    assert norm["farm_id"] == "FARM-001"
    assert norm["land"]["normalized_area_ha"] == 2.0
    assert norm["resources"]["normalized_water_liters"] == 100000.0
    assert norm["resources"]["normalized_water_m3"] == 100.0


# -------------------------------------------------------------
# Test 10 — Negative Resource & Coordinate Validation
# -------------------------------------------------------------
def test_negative_resources_fail():
    data = create_base_profile_dict()
    data["available_water"] = -500.0
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Water availability cannot be negative" in e for e in errors)

    data = create_base_profile_dict()
    data["available_budget_inr"] = -1000.0
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Available budget cannot be negative" in e for e in errors)

    data = create_base_profile_dict()
    data["farm_id"] = "   "
    with pytest.raises(ValidationError) as exc_info:
        FarmProfile(**data)
    errors = format_validation_errors(exc_info.value)
    assert any("Farm ID must be a non-empty string" in e for e in errors)
