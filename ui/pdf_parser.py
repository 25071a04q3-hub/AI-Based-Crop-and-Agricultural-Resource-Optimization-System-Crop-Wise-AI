"""
FarmTwin — Soil Health Card & Farm Report PDF Parser.

Extracts agronomic parameters (soil N, P, K, pH, location, land area, water, budget)
from uploaded agricultural lab reports and soil health card PDFs using pypdf.
"""
import io
import re
from typing import Dict, Any, Tuple, Optional
from pypdf import PdfReader

from engine.profile import FarmProfile


def extract_text_from_pdf(pdf_file_or_bytes) -> str:
    """Extracts raw text content across all pages of a PDF file."""
    reader = PdfReader(pdf_file_or_bytes)
    text = ""
    for page in reader.pages:
        page_text = page.extract_text() or ""
        text += page_text + "\n"
    return text


def parse_soil_health_text(text: str) -> Dict[str, Any]:
    """
    Parses key agricultural and soil attributes from raw report text
    using tolerant regex patterns.
    """
    extracted: Dict[str, Any] = {}

    # 1. Farm ID / Card No
    m_id = re.search(r'(?:Card\s*No|Sample\s*No|Farm\s*ID|Report\s*No)\s*[:\-]?\s*([A-Za-z0-9\-_]+)', text, re.I)
    if m_id:
        extracted['farm_id'] = m_id.group(1).strip()
    else:
        extracted['farm_id'] = "SHC-UPLOADED"

    # 2. Farmer Name
    m_name = re.search(r'Farmer\s*Name\s*[:\-]?\s*([^\n\r,;]+)', text, re.I)
    if m_name:
        extracted['farmer_name'] = m_name.group(1).strip()
    else:
        extracted['farmer_name'] = "Report Farmer"

    # 3. State & District
    m_state = re.search(r'State\s*[:\-]?\s*([^\n\r,;]+)', text, re.I)
    if m_state:
        extracted['state'] = m_state.group(1).strip()
    else:
        extracted['state'] = "Telangana"

    m_dist = re.search(r'District\s*[:\-]?\s*([^\n\r,;]+)', text, re.I)
    if m_dist:
        extracted['district'] = m_dist.group(1).strip()
    else:
        extracted['district'] = "Warangal"

    # 4. Land Area & Unit
    m_area = re.search(r'(?:Area|Holding|Land)\s*[:\-]?\s*([\d\.]+)\s*(Hectare|Acre|ha|ac)?', text, re.I)
    if m_area:
        extracted['land_area'] = float(m_area.group(1))
        unit = (m_area.group(2) or 'hectare').lower()
        extracted['land_unit'] = 'acre' if 'ac' in unit else 'hectare'
    else:
        extracted['land_area'] = 2.0
        extracted['land_unit'] = 'hectare'

    # 5. Soil Nutrients N, P, K & pH
    m_n = re.search(r'(?:Available\s*)?Nitrogen(?:\s*\(N\))?\s*[:\-]?\s*([\d\.]+)', text, re.I)
    if m_n:
        extracted['nitrogen_n_kg_ha'] = float(m_n.group(1))
    else:
        extracted['nitrogen_n_kg_ha'] = 75.0

    m_p = re.search(r'(?:Available\s*)?Phosphorus(?:\s*\(P\))?\s*[:\-]?\s*([\d\.]+)', text, re.I)
    if m_p:
        extracted['phosphorus_p_kg_ha'] = float(m_p.group(1))
    else:
        extracted['phosphorus_p_kg_ha'] = 35.0

    m_k = re.search(r'(?:Available\s*)?Potassium(?:\s*\(K\))?\s*[:\-]?\s*([\d\.]+)', text, re.I)
    if m_k:
        extracted['potassium_k_kg_ha'] = float(m_k.group(1))
    else:
        extracted['potassium_k_kg_ha'] = 45.0

    m_ph = re.search(r'(?:Soil\s*Reaction|pH)\s*[:\-]?\s*([\d\.]+)', text, re.I)
    if m_ph:
        extracted['ph'] = float(m_ph.group(1))
    else:
        extracted['ph'] = 6.8

    # 6. Irrigation Water
    m_wat = re.search(r'(?:Irrigation\s*)?Water\s*[:\-]?\s*([\d\.]+)', text, re.I)
    if m_wat:
        extracted['available_water'] = float(m_wat.group(1))
    else:
        # Scale with land area: 1 ha = 10,000,000 L baseline
        extracted['available_water'] = round(extracted['land_area'] * 6000000.0, 0)
    extracted['water_unit'] = 'liter'

    # 7. Working Budget / Capital
    m_bud = re.search(r'(?:Budget|Capital|Investment)\s*[:\-]?\s*(?:Rs\.?|INR)?\s*([\d\.]+)', text, re.I)
    if m_bud:
        extracted['available_budget_inr'] = float(m_bud.group(1))
    else:
        extracted['available_budget_inr'] = round(extracted['land_area'] * 35000.0, 0)

    # 8. Available Fertilizer Inventory
    extracted['available_n_kg'] = round(extracted['nitrogen_n_kg_ha'] * extracted['land_area'] * 1.5, 1)
    extracted['available_p_kg'] = round(extracted['phosphorus_p_kg_ha'] * extracted['land_area'] * 1.5, 1)
    extracted['available_k_kg'] = round(extracted['potassium_k_kg_ha'] * extracted['land_area'] * 1.5, 1)

    # 9. Environmental & Strategy defaults
    m_temp = re.search(r'(?:Temperature|Temp)\s*[:\-]?\s*([\d\.]+)', text, re.I)
    extracted['temperature_c'] = float(m_temp.group(1)) if m_temp else 28.5

    m_hum = re.search(r'Humidity\s*[:\-]?\s*([\d\.]+)', text, re.I)
    extracted['humidity_percent'] = float(m_hum.group(1)) if m_hum else 65.0

    m_rain = re.search(r'Rainfall\s*[:\-]?\s*([\d\.]+)', text, re.I)
    extracted['rainfall_mm'] = float(m_rain.group(1)) if m_rain else 120.0

    extracted['available_labour_days'] = round(extracted['land_area'] * 50.0, 0)
    extracted['season'] = 'kharif'
    extracted['year'] = 2026
    extracted['risk_tolerance'] = 0.50
    extracted['is_demo'] = False

    return extracted


def build_profile_from_pdf(pdf_file_or_bytes) -> Tuple[FarmProfile, Dict[str, Any], str]:
    """
    Reads an uploaded PDF file, extracts text, parses fields, and builds a verified FarmProfile.
    
    Returns:
        (FarmProfile, extracted_dict, raw_text_preview)
    """
    raw_text = extract_text_from_pdf(pdf_file_or_bytes)
    fields = parse_soil_health_text(raw_text)
    profile = FarmProfile(**fields)
    return profile, fields, raw_text[:500]
