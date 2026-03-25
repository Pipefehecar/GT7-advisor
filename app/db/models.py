from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Car(Base):
    """Cars from the ddm999 community catalog."""

    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    car_id: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    manufacturer: Mapped[str] = mapped_column(String(100), default="")
    name: Mapped[str] = mapped_column(String(200), default="")
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    pp_stock: Mapped[float | None] = mapped_column(Float, nullable=True)

    # JSON blob defining which params are tunable and their valid ranges.
    # Shape: { "suspension": { "ranges": { "spring_rate_front": [3.0, 15.0] } }, ... }
    tuning_profile: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    sessions: Mapped[list["Session"]] = relationship(back_populates="car")


class Session(Base):
    """A driving session: one car, one track, many laps."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    car_id: Mapped[int | None] = mapped_column(ForeignKey("cars.id"), nullable=True)
    track_name: Mapped[str] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # User enters setup manually before the session
    manual_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    car: Mapped["Car | None"] = relationship(back_populates="sessions")
    laps: Mapped[list["Lap"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    suggestions: Mapped[list["SetupSuggestion"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Lap(Base):
    """Aggregated telemetry for a single lap."""

    __tablename__ = "laps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    lap_number: Mapped[int] = mapped_column(Integer)
    lap_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    avg_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_throttle: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_brake: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Behaviour events derived from raw telemetry
    oversteer_events: Mapped[int] = mapped_column(Integer, default=0)
    understeer_events: Mapped[int] = mapped_column(Integer, default=0)
    wheel_lock_events: Mapped[int] = mapped_column(Integer, default=0)
    wheelspin_events: Mapped[int] = mapped_column(Integer, default=0)
    bottom_out_events: Mapped[int] = mapped_column(Integer, default=0)

    # Tyre temps averaged per corner over the lap
    tyre_temp_fl: Mapped[float | None] = mapped_column(Float, nullable=True)
    tyre_temp_fr: Mapped[float | None] = mapped_column(Float, nullable=True)
    tyre_temp_rl: Mapped[float | None] = mapped_column(Float, nullable=True)
    tyre_temp_rr: Mapped[float | None] = mapped_column(Float, nullable=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["Session"] = relationship(back_populates="laps")


class SetupSuggestion(Base):
    """LLM-generated setup suggestion tied to a session."""

    __tablename__ = "setup_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"))
    llm_provider: Mapped[str] = mapped_column(String(50))
    llm_model: Mapped[str] = mapped_column(String(100))
    prompt_used: Mapped[str] = mapped_column(Text)
    suggestion_text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["Session"] = relationship(back_populates="suggestions")
