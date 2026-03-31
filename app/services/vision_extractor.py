"""
Shared normalization utilities for OCR extraction results.

These are provider-agnostic: any OCR provider (Anthropic, Google Vision, Tesseract)
can use these functions to normalize extracted GT7 tuning values.
"""

from difflib import get_close_matches
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Valid selection options (must match TuningForm.tsx exactly)
# ─────────────────────────────────────────────────────────────────────────────

SELECTION_VALID_OPTIONS: dict[str, list[str]] = {
    # Tires
    "compound_front": [
        "Normal duro", "Normal medio", "Normal blando",
        "Deporte duro", "Deporte medio", "Deporte blando",
        "Carrera: extra duro", "Carrera: duro", "Carrera: medio",
        "Carrera: blando", "Carrera: super blando",
        "Intermedio", "Lluvia",
        "Tierra duro", "Tierra blando", "Nieve",
    ],
    "compound_rear": [
        "Normal duro", "Normal medio", "Normal blando",
        "Deporte duro", "Deporte medio", "Deporte blando",
        "Carrera: extra duro", "Carrera: duro", "Carrera: medio",
        "Carrera: blando", "Carrera: super blando",
        "Intermedio", "Lluvia",
        "Tierra duro", "Tierra blando", "Nieve",
    ],
    # Supercharger
    "turbo": ["No", "rpm bajas", "rpm altas", "Sport", "Carreras"],
    "anti_lag": ["No", "Desactivar", "Activar", "Agresivo"],
    "intercooler": ["No", "Sport", "Carreras"],
    "supercharger": ["No", "Sport", "Carreras"],
    # Intake/Exhaust
    "air_filter": ["No", "Sport", "Carreras"],
    "muffler": ["No", "Sport", "Carreras", "Semi-carreras"],
    "exhaust_manifold": ["No", "Sport", "Carreras"],
    # Brakes
    "brake_system": ["Sport", "Carreras (discos ranurados)", "Carreras (carbono)"],
    "brake_pads": ["Normal", "Sport", "Carreras", "Extremo"],
    "handbrake": ["Normal", "Sport", "Carreras"],
    # Steering
    "steering_kit": ["Normal", "Sport", "Extremo"],
    # Drivetrain
    "clutch": ["Normal", "Sport", "Carreras", "Triple plato"],
    "drive_shaft": ["No", "Sport", "Carreras"],
    # Generic yes/no
    "enabled": ["No", "Sí"],
    "torque_vectoring": ["No", "Sí"],
    "all_wheel_steering": ["No", "Sí"],
    # Body modifications
    "weight_reduction_1": ["--", "Instalado"],
    "weight_reduction_2": ["--", "Instalado"],
    "weight_reduction_3": ["--", "Instalado"],
    "weight_reduction_4": ["--", "Instalado"],
    "weight_reduction_5": ["--", "Instalado"],
    # Engine modifications
    "boring": ["--", "Instalado"],
    "stroke_increase": ["--", "Instalado"],
    "displacement_increase": ["--", "Instalado"],
    "valve_timing": ["--", "Instalado"],
    "valve_lift_amount": ["--", "Instalado"],
    "compression_ratio": ["--", "Instalado"],
    "titanium_exhaust": ["--", "Instalado"],
    "lightweight_flywheel": ["--", "Instalado"],
    "racing_engine_computer": ["--", "Instalado"],
    "all_wheel_drive_convert": ["--", "Instalado"],
    "custom_transmission": ["--", "Instalado"],
    "transmission_oil_cooler": ["--", "Instalado"],
    "racing_transmission": ["--", "Instalado"],
    "carbon_driveshaft": ["--", "Instalado"],
}


def normalize_selection(field_key: str, raw_value: str) -> tuple[str, str | None]:
    """
    Normalize a selection value using fuzzy matching.

    Returns (normalized_value, warning_or_None).
    - Exact match (case-insensitive): warning is None.
    - Fuzzy match: warning explains the normalization.
    - No match: returns the raw value with a warning.
    """
    if field_key not in SELECTION_VALID_OPTIONS:
        return raw_value, f"Unknown field: {field_key}"

    valid_options = SELECTION_VALID_OPTIONS[field_key]

    # Exact match (case-insensitive)
    for opt in valid_options:
        if opt.lower() == raw_value.lower():
            return opt, None

    # Fuzzy match
    matches = get_close_matches(raw_value, valid_options, n=1, cutoff=0.8)
    if matches:
        return matches[0], f"Normalized '{raw_value}' → '{matches[0]}'"

    # No match
    return raw_value, f"Value '{raw_value}' not recognized for {field_key}"


def normalize_extracted_profile(
    extracted: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """
    Normalize all selection values in an extracted tuning profile.

    Returns (normalized_profile, warnings).
    Can be used by any OCR provider after extraction.
    """
    warnings: list[str] = []

    for section_data in extracted.values():
        if not isinstance(section_data, dict):
            continue
        selections = section_data.get("selections")
        if not isinstance(selections, dict):
            continue
        for param_key, param_value in list(selections.items()):
            if isinstance(param_value, str):
                normalized, warning = normalize_selection(param_key, param_value)
                selections[param_key] = normalized
                if warning:
                    warnings.append(warning)

    return extracted, warnings
