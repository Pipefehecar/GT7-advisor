import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import cars, sessions, telemetry
from app.core.config import get_settings
from app.db.models import Base, Lap as LapModel  # noqa: F401  triggers model registration
from app.db.session import AsyncSessionLocal, engine
from app.services.telemetry import LapSummary, TelemetryService

settings = get_settings()

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)

logger = logging.getLogger(__name__)


async def _persist_lap(session_id: int, summary: LapSummary) -> None:
    """Guarda un lap completado en la BD desde el hilo de telemetría."""
    async with AsyncSessionLocal() as db:
        lap = LapModel(
            session_id=session_id,
            lap_number=summary.lap_number,
            lap_time_ms=summary.lap_time_ms,
            avg_speed_kmh=summary.avg_speed_kmh,
            max_speed_kmh=summary.max_speed_kmh,
            avg_throttle=summary.avg_throttle,
            avg_brake=summary.avg_brake,
            oversteer_events=summary.oversteer_events,
            understeer_events=summary.understeer_events,
            wheel_lock_events=summary.wheel_lock_events,
            wheelspin_events=summary.wheelspin_events,
            bottom_out_events=summary.bottom_out_events,
            tyre_temp_fl=summary.tyre_temp_fl,
            tyre_temp_fr=summary.tyre_temp_fr,
            tyre_temp_rl=summary.tyre_temp_rl,
            tyre_temp_rr=summary.tyre_temp_rr,
        )
        db.add(lap)
        await db.commit()
        logger.info("Lap %d auto-guardado en sesión %d", summary.lap_number, session_id)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    loop = asyncio.get_event_loop()
    svc = TelemetryService(ps_ip=settings.ps_ip)
    app.state.telemetry = svc
    app.state.active_session_id = None  # se activa con POST /sessions/{id}/activate

    def on_lap_complete(summary: LapSummary) -> None:
        sid = app.state.active_session_id
        if sid is not None:
            asyncio.run_coroutine_threadsafe(_persist_lap(sid, summary), loop)
        else:
            logger.debug("Lap %d completado sin sesión activa — ignorado", summary.lap_number)

    svc.on_lap_complete = on_lap_complete
    svc.start()

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    svc.stop()


app = FastAPI(
    title="GT7 AI Setup Advisor",
    version="0.1.0",
    description=(
        "Telemetry-powered setup suggestions for Gran Turismo 7. "
        "Listens to the PS4/PS5 UDP stream, stores session data, "
        "and uses an LLM to recommend car setup changes."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cars.router)
app.include_router(sessions.router)
app.include_router(telemetry.router)


@app.get("/health", tags=["meta"])
async def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_provider": settings.llm_provider,
        "db": settings.database_url.split("///")[0],
    }
