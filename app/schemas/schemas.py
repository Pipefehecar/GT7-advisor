from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ── Car ───────────────────────────────────────────────────────────────────────

class CarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    car_id: str
    manufacturer: str
    name: str
    category: str | None = None
    pp_stock: float | None = None
    tuning_profile: dict | None = None


class TuningProfileIn(BaseModel):
    """
    Full GT7 tuning sheet — mirrors the in-game configuration screen.
    Each section is a dict that can contain:
      - ranges:     { param_key: [min, max] }       numeric tunable params
      - current:    { param_key: value }             current numeric values
      - selections: { param_key: "option_string" }   dropdown / categorical values

    Example:
    {
      "suspension": {
        "ranges": { "ride_height_front": [50, 150], "arb_front": [1, 10] },
        "current": { "ride_height_front": 65, "arb_front": 5 }
      },
      "tires": {
        "selections": { "compound_front": "Carrera: blando", "compound_rear": "Carrera: blando" }
      },
      "supercharger": {
        "selections": { "turbo": "rpm altas", "anti_lag": "Desactivar" }
      }
    }
    """
    # ── Page 1 ──────────────────────────────────────────────────────────────
    tires: dict[str, Any] | None = None
    suspension: dict[str, Any] | None = None
    aerodynamics: dict[str, Any] | None = None
    weight_balance: dict[str, Any] | None = None
    differential: dict[str, Any] | None = None
    transmission: dict[str, Any] | None = None
    nitro: dict[str, Any] | None = None

    # ── Page 2 ──────────────────────────────────────────────────────────────
    supercharger: dict[str, Any] | None = None
    intake_exhaust: dict[str, Any] | None = None
    brakes: dict[str, Any] | None = None
    steering: dict[str, Any] | None = None
    drivetrain: dict[str, Any] | None = None
    engine_mods: dict[str, Any] | None = None
    body: dict[str, Any] | None = None

    # ── Legacy (kept for backward compat) ───────────────────────────────────
    brake_balance: dict[str, Any] | None = None


# ── Session ───────────────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    car_id: int | None = None
    track_name: str
    manual_config: dict[str, Any] | None = None


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    car_id: int | None = None
    track_name: str
    started_at: datetime
    manual_config: dict | None = None


# ── Lap ───────────────────────────────────────────────────────────────────────

class LapIn(BaseModel):
    lap_number: int
    lap_time_ms: int | None = None
    avg_speed_kmh: float | None = None
    max_speed_kmh: float | None = None
    avg_throttle: float | None = None
    avg_brake: float | None = None
    oversteer_events: int = 0
    understeer_events: int = 0
    wheel_lock_events: int = 0
    wheelspin_events: int = 0
    bottom_out_events: int = 0
    tyre_temp_fl: float | None = None
    tyre_temp_fr: float | None = None
    tyre_temp_rl: float | None = None
    tyre_temp_rr: float | None = None


class LapOut(LapIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: int
    recorded_at: datetime


# ── Suggestion ────────────────────────────────────────────────────────────────

class SuggestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    session_id: int
    llm_provider: str
    llm_model: str
    suggestion_text: str
    created_at: datetime


# ── Telemetry ─────────────────────────────────────────────────────────────────

class TelemetryStatus(BaseModel):
    running: bool
    ps_ip: str
    speed_kmh: float | None = None
    rpm: float | None = None


# ── OCR / Vision Extraction ────────────────────────────────────────────────────

class TuningScreenshotResponse(BaseModel):
    """Response from OCR/Vision extraction of a GT7 tuning screenshot."""

    extracted_profile: dict[str, Any]
    """Extracted tuning profile (same structure as TuningProfileIn)."""

    provider: str
    """LLM provider used (e.g. 'anthropic')."""

    model: str
    """Model name (e.g. 'claude-3-5-sonnet-20241022')."""

    sections_found: list[str]
    """List of sections that had visible data (e.g. ['tires', 'suspension'])."""

    warnings: list[str]
    """Non-critical warnings (e.g. ambiguous values, unrecognized options)."""

    car_name: str | None = None
    """Car name detected in the screenshot, if visible."""
