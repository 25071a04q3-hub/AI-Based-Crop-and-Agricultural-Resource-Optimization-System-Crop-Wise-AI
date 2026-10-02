"""
FarmTwin — Farm Profile & Input Validation Engine.

This module is the canonical entry point and data contract for farm operational parameters.
It validates all agronomic, physical, economic, and climatic inputs and standardizes them
into the FarmTwin internal unit system:
- Land: hectares (ha)
- Water: liters (L)
- Currency: Indian Rupee (INR)
- Risk Tolerance: normalized float [0.0 - 1.0]

IMPORTANT ARCHITECTURAL RULE:
This module must remain completely independent of UI/Streamlit frameworks.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError


# ==========================================
# STRICT PHYSICAL CONVERSION CONSTANTS
# ==========================================
ACRES_PER_HECTARE: float = 2.47105
HECTARES_PER_ACRE: float = 0.404686
LITERS_PER_M3: float = 1000.0


class LandUnit(str, Enum):
    HECTARE = "hectare"
    ACRE = "acre"

    @classmethod
    def _missing_(cls, value: object) -> Optional["LandUnit"]:
        if isinstance(value, str):
            val = value.strip().lower()
            if val in ("ha", "hectares", "hectare"):
                return cls.HECTARE
            if val in ("ac", "acres", "acre"):
                return cls.ACRE
        return None


class WaterUnit(str, Enum):
    LITER = "liter"
    M3 = "m3"

    @classmethod
    def _missing_(cls, value: object) -> Optional["WaterUnit"]:
        if isinstance(value, str):
            val = value.strip().lower()
            if val in ("l", "liter", "liters", "litre", "litres"):
                return cls.LITER
            if val in ("m3", "m^3", "cum", "cubic_meter", "cubic_meters", "cubic metres", "m³"):
                return cls.M3
        return None


class Season(str, Enum):
    KHARIF = "kharif"
    RABI = "rabi"
    ZAID = "zaid"

    @classmethod
    def _missing_(cls, value: object) -> Optional["Season"]:
        if isinstance(value, str):
            val = value.strip().lower()
            for member in cls:
                if member.value == val:
                    return member
        return None


class FarmProfile(BaseModel):
    """
    Validated representation of a farmer's operational profile and resource limits.
    Serves as the common input contract across all downstream FarmTwin engines.
    """
    # 1. Farm Identity
    farm_id: str = Field(description="Unique non-empty identifier for the farm parcel")
    farmer_name: Optional[str] = Field(default=None, description="Optional non-sensitive farmer identifier")

    # 2. Location
    state: Optional[str] = Field(default=None, description="State of operation")
    district: Optional[str] = Field(default=None, description="District of operation")
    latitude: Optional[float] = Field(default=None, description="Geographical latitude [-90 to +90]")
    longitude: Optional[float] = Field(default=None, description="Geographical longitude [-180 to +180]")

    # 3. Land Information
    land_area: float = Field(description="Operational land area (must be > 0)")
    land_unit: LandUnit = Field(default=LandUnit.HECTARE, description="Unit of entered land area (hectare or acre)")
    original_land_area: float = Field(default=0.0, description="Preserved original land area as entered")
    original_land_unit: str = Field(default="", description="Preserved original land unit")
    land_area_ha: float = Field(default=0.0, description="Normalized land area in hectares")

    # 4. Soil Information
    nitrogen_n_kg_ha: float = Field(description="Available soil Nitrogen (N) in kg/ha")
    phosphorus_p_kg_ha: float = Field(description="Available soil Phosphorus (P) in kg/ha")
    potassium_k_kg_ha: float = Field(description="Available soil Potassium (K) in kg/ha")
    ph: float = Field(description="Soil pH level [0.0 - 14.0]")

    # 5. Weather / Observed Climate
    temperature_c: float = Field(description="Observed/forecast temperature in Celsius")
    humidity_percent: float = Field(description="Observed/forecast relative humidity percentage [0 - 100]")
    rainfall_mm: float = Field(description="Observed/expected seasonal rainfall in mm")

    # 6. Water Resource
    available_water: float = Field(description="Total usable irrigation water available")
    water_unit: WaterUnit = Field(default=WaterUnit.LITER, description="Unit of entered water (liter or m3)")
    original_water_amount: float = Field(default=0.0, description="Preserved original water amount as entered")
    original_water_unit: str = Field(default="", description="Preserved original water unit")
    water_liters: float = Field(default=0.0, description="Normalized water capacity in liters")

    # 7. Fertilizer Resources (Available capacity limits, NOT crop demands)
    available_n_kg: float = Field(description="Available Nitrogen fertilizer inventory in kg")
    available_p_kg: float = Field(description="Available Phosphorus fertilizer inventory in kg")
    available_k_kg: float = Field(description="Available Potassium fertilizer inventory in kg")

    # 8. Budget & Economics
    available_budget_inr: float = Field(description="Total working capital budget in INR")

    # 9. Labour Resource
    available_labour_days: float = Field(description="Total farm labour availability in person-days")

    # 10. Planning Season
    season: Season = Field(description="Agricultural season (kharif, rabi, zaid)")
    year: int = Field(description="Agricultural planning year")

    # 11. Risk Preference
    risk_tolerance: float = Field(
        default=0.5,
        description="Farmer risk preference: 0.0 (extreme risk aversion) to 1.0 (risk tolerant)"
    )

    # Metadata
    is_demo: bool = Field(default=False, description="Flag indicating synthetic/demo profile")

    # -------------------------------------------------------------
    # FIELD VALIDATORS WITH FARMER-FRIENDLY ERROR MESSAGES
    # -------------------------------------------------------------
    @field_validator("farm_id")
    @classmethod
    def validate_farm_id(cls, v: str) -> str:
        cleaned = v.strip() if isinstance(v, str) else ""
        if not cleaned:
            raise ValueError("Farm ID must be a non-empty string.")
        return cleaned

    @field_validator("farmer_name", "state", "district")
    @classmethod
    def validate_optional_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = v.strip()
        return cleaned if cleaned else None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-90.0 <= v <= 90.0):
            raise ValueError("Latitude must be between -90 and +90 degrees.")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (-180.0 <= v <= 180.0):
            raise ValueError("Longitude must be between -180 and +180 degrees.")
        return v

    @field_validator("land_area")
    @classmethod
    def validate_land_area(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Land area must be greater than 0.")
        return v

    @field_validator("nitrogen_n_kg_ha", "phosphorus_p_kg_ha", "potassium_k_kg_ha")
    @classmethod
    def validate_soil_nutrients(cls, v: float, info: Any) -> float:
        if v < 0:
            field_name = info.field_name.split("_")[0].capitalize()
            raise ValueError(f"Soil {field_name} level cannot be negative.")
        return v

    @field_validator("ph")
    @classmethod
    def validate_ph(cls, v: float) -> float:
        if not (0.0 <= v <= 14.0):
            raise ValueError("Soil pH must be between 0 and 14.")
        return v

    @field_validator("temperature_c")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not (-20.0 <= v <= 60.0):
            raise ValueError("Temperature must be within realistic agricultural limits (-20°C to 60°C).")
        return v

    @field_validator("humidity_percent")
    @classmethod
    def validate_humidity(cls, v: float) -> float:
        if not (0.0 <= v <= 100.0):
            raise ValueError("Humidity must be between 0 and 100%.")
        return v

    @field_validator("rainfall_mm")
    @classmethod
    def validate_rainfall(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Rainfall cannot be negative.")
        return v

    @field_validator("available_water")
    @classmethod
    def validate_available_water(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Water availability cannot be negative.")
        return v

    @field_validator("available_n_kg", "available_p_kg", "available_k_kg")
    @classmethod
    def validate_fertilizers(cls, v: float, info: Any) -> float:
        if v < 0:
            nutrient = info.field_name.split("_")[1].upper()
            raise ValueError(f"Available {nutrient} fertilizer inventory cannot be negative.")
        return v

    @field_validator("available_budget_inr")
    @classmethod
    def validate_budget(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Available budget cannot be negative.")
        return v

    @field_validator("available_labour_days")
    @classmethod
    def validate_labour(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Available labour days cannot be negative.")
        return v

    @field_validator("year")
    @classmethod
    def validate_year(cls, v: int) -> int:
        if not (2000 <= v <= 2100):
            raise ValueError("Planning year must be a realistic calendar year (2000 to 2100).")
        return v

    @field_validator("risk_tolerance")
    @classmethod
    def validate_risk_tolerance(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError("Risk tolerance must be between 0 and 1.")
        return v

    # -------------------------------------------------------------
    # MODEL VALIDATOR FOR UNIT NORMALIZATION & PRESERVATION
    # -------------------------------------------------------------
    @model_validator(mode="after")
    def compute_normalized_units(self) -> "FarmProfile":
        # Preserve original land representation
        self.original_land_area = float(self.land_area)
        self.original_land_unit = self.land_unit.value

        # Convert to hectares internally
        if self.land_unit == LandUnit.ACRE:
            self.land_area_ha = round(self.land_area * HECTARES_PER_ACRE, 6)
        else:
            self.land_area_ha = round(float(self.land_area), 6)

        # Preserve original water representation
        self.original_water_amount = float(self.available_water)
        self.original_water_unit = self.water_unit.value

        # Convert to liters internally (1 m³ = 1,000 liters)
        if self.water_unit == WaterUnit.M3:
            self.water_liters = round(self.available_water * LITERS_PER_M3, 4)
        else:
            self.water_liters = round(float(self.available_water), 4)

        return self

    def to_normalized(self) -> Dict[str, Any]:
        """
        Exports the canonical normalized data dictionary consumed by downstream engines.
        All units in this export are strictly standardized:
        - land: hectares
        - water: liters
        - currency: INR
        - nutrients: kg / kg/ha
        """
        return {
            "farm_id": self.farm_id,
            "farmer_name": self.farmer_name,
            "location": {
                "state": self.state,
                "district": self.district,
                "latitude": self.latitude,
                "longitude": self.longitude,
            },
            "land": {
                "entered_area": self.original_land_area,
                "entered_unit": self.original_land_unit,
                "normalized_area_ha": self.land_area_ha,
            },
            "soil": {
                "nitrogen_kg_ha": self.nitrogen_n_kg_ha,
                "phosphorus_kg_ha": self.phosphorus_p_kg_ha,
                "potassium_kg_ha": self.potassium_k_kg_ha,
                "ph": self.ph,
            },
            "weather": {
                "temperature_c": self.temperature_c,
                "humidity_percent": self.humidity_percent,
                "rainfall_mm": self.rainfall_mm,
            },
            "resources": {
                "entered_water": self.original_water_amount,
                "entered_water_unit": self.original_water_unit,
                "normalized_water_liters": self.water_liters,
                "normalized_water_m3": round(self.water_liters / LITERS_PER_M3, 4),
                "fertilizer_n_kg": self.available_n_kg,
                "fertilizer_p_kg": self.available_p_kg,
                "fertilizer_k_kg": self.available_k_kg,
                "budget_inr": self.available_budget_inr,
                "labour_days": self.available_labour_days,
            },
            "strategy": {
                "season": self.season.value,
                "year": self.year,
                "risk_tolerance": self.risk_tolerance,
            },
            "is_demo": self.is_demo,
        }


def format_validation_errors(e: ValidationError) -> List[str]:
    """
    Extracts farmer-friendly string messages from a Pydantic ValidationError.
    Strips raw code prefixes (e.g. 'Value error, ') for clean UI presentation.
    """
    messages: List[str] = []
    for err in e.errors():
        msg = err.get("msg", "Invalid input value.")
        if msg.startswith("Value error, "):
            msg = msg[len("Value error, "):]
        messages.append(msg)
    return messages


def get_demo_farm_profile() -> FarmProfile:
    """
    Generates a validated synthetic demo farm profile for testing and evaluation.

    NOTICE:
    -------------------------------------------------------------------------
    DEMO / TEST PROFILE ONLY.
    Not real farmer data. Values are for simulation and architectural testing.
    -------------------------------------------------------------------------
    """
    return FarmProfile(
        farm_id="FARM-001",
        farmer_name="Demo Farmer",
        state="Telangana",
        district="Hyderabad",
        latitude=17.3850,
        longitude=78.4867,
        land_area=2.0,
        land_unit=LandUnit.HECTARE,
        nitrogen_n_kg_ha=80.0,
        phosphorus_p_kg_ha=40.0,
        potassium_k_kg_ha=50.0,
        ph=6.8,
        temperature_c=28.0,
        humidity_percent=65.0,
        rainfall_mm=100.0,
        available_water=100000.0,
        water_unit=WaterUnit.LITER,
        available_n_kg=160.0,
        available_p_kg=80.0,
        available_k_kg=100.0,
        available_budget_inr=100000.0,
        available_labour_days=100.0,
        season=Season.KHARIF,
        year=2026,
        risk_tolerance=0.5,
        is_demo=True,
    )
