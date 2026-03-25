from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Car, Lap, Session, SetupSuggestion
from app.db.session import get_db
from app.schemas.schemas import LapIn, LapOut, SessionCreate, SessionOut, SuggestionOut
from app.services.llm.base import BaseLLMProvider
from app.services.llm.factory import get_llm_provider
from app.services.prompt_builder import SYSTEM_PROMPT, build_prompt

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionOut, status_code=201)
async def create_session(body: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = Session(
        car_id=body.car_id,
        track_name=body.track_name,
        manual_config=body.manual_config,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


@router.get("/", response_model=list[SessionOut])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Session).order_by(Session.started_at.desc()).limit(50)
    )
    return result.scalars().all()


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: int, db: AsyncSession = Depends(get_db)):
    s = await db.get(Session, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return s


@router.post("/{session_id}/activate", status_code=200)
async def activate_session(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Marca esta sesión como activa para que el listener UDP auto-guarde los laps."""
    s = await db.get(Session, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    request.app.state.active_session_id = session_id
    return {"message": f"Sesión {session_id} activa — los laps se guardarán automáticamente"}


# ── Laps ──────────────────────────────────────────────────────────────────────

@router.post("/{session_id}/laps", response_model=LapOut, status_code=201)
async def add_lap(
    session_id: int,
    body: LapIn,
    db: AsyncSession = Depends(get_db),
):
    """Add a lap manually (telemetry service also calls this internally)."""
    s = await db.get(Session, session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    lap = Lap(session_id=session_id, **body.model_dump())
    db.add(lap)
    await db.flush()
    await db.refresh(lap)
    return lap


@router.get("/{session_id}/laps", response_model=list[LapOut])
async def list_laps(session_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Lap).where(Lap.session_id == session_id).order_by(Lap.lap_number)
    )
    return result.scalars().all()


# ── AI Suggestions ────────────────────────────────────────────────────────────

@router.post("/{session_id}/suggest", response_model=SuggestionOut, status_code=201)
async def request_suggestion(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    llm: BaseLLMProvider = Depends(get_llm_provider),
):
    """Ask the active LLM provider to analyse this session and suggest setup changes."""
    session = await db.get(Session, session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    car = await db.get(Car, session.car_id) if session.car_id else None

    laps_result = await db.execute(
        select(Lap).where(Lap.session_id == session_id).order_by(Lap.lap_number)
    )
    laps = list(laps_result.scalars().all())

    if not laps:
        raise HTTPException(400, "No laps recorded for this session yet")

    user_prompt = build_prompt(session=session, car=car, laps=laps)
    llm_resp = await llm.complete(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt)

    suggestion = SetupSuggestion(
        session_id=session_id,
        llm_provider=llm_resp.provider,
        llm_model=llm_resp.model,
        prompt_used=user_prompt,
        suggestion_text=llm_resp.content,
    )
    db.add(suggestion)
    await db.flush()
    await db.refresh(suggestion)
    return suggestion


@router.get("/{session_id}/suggestions", response_model=list[SuggestionOut])
async def list_suggestions(session_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SetupSuggestion)
        .where(SetupSuggestion.session_id == session_id)
        .order_by(SetupSuggestion.created_at.desc())
    )
    return result.scalars().all()
