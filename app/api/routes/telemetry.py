from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.schemas import TelemetryStatus
from app.services.telemetry import TelemetryService

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def _svc(request: Request) -> TelemetryService:
    return request.app.state.telemetry


@router.get("/status", response_model=TelemetryStatus)
async def status(svc: TelemetryService = Depends(_svc)):
    pkt = svc.latest_packet
    speed = rpm = None
    if pkt:
        if isinstance(pkt, dict):
            speed = round((pkt.get("car_speed") or 0) * 3.6, 1)
            rpm = pkt.get("engine_rpm")
        else:
            speed = round((getattr(pkt, "car_speed", 0) or 0) * 3.6, 1)
            rpm = getattr(pkt, "engine_rpm", None)
    return TelemetryStatus(running=svc._running, ps_ip=svc.ps_ip, speed_kmh=speed, rpm=rpm)


@router.post("/start")
async def start(svc: TelemetryService = Depends(_svc)):
    svc.start()
    return {"message": "Telemetry listener started"}


@router.post("/stop")
async def stop(svc: TelemetryService = Depends(_svc)):
    svc.stop()
    return {"message": "Telemetry listener stopped"}
