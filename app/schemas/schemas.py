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
    Define which parameters are adjustable and their valid ranges.

    Example:
    {
      "suspension": {
        "ranges": { "spring_rate_front": [3.0, 15.0], "ride_height_front": [50, 150] },
        "current": { "spring_rate_front": 7.5, "ride_height_front": 65 }
      },
      "aerodynamics": {
        "ranges": { "downforce_front": [0, 50], "downforce_rear": [0, 50] }
      }
    }
    """
    suspension: dict[str, Any] | None = None
    aerodynamics: dict[str, Any] | None = None
    differential: dict[str, Any] | None = None
    transmission: dict[str, Any] | None = None
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
