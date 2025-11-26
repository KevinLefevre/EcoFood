from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ecofood_backend.database import get_session
from ecofood_backend.schemas import (
    SessionCreate,
    SessionResponse,
    SessionMessageCreate,
    SessionMessageResponse,
)
from ecofood_backend.services.session_service import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("/", response_model=SessionResponse)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_session)):
    return await session_service.create_session(
        db, payload.household_id, payload.session_uuid
    )


@router.get("/{session_uuid}", response_model=SessionResponse)
async def get_session_endpoint(session_uuid: str, db: AsyncSession = Depends(get_session)):
    session = await session_service.get_session(db, session_uuid)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/{session_id}/messages", response_model=SessionMessageResponse)
async def add_message(
    session_id: int, payload: SessionMessageCreate, db: AsyncSession = Depends(get_session)
):
    return await session_service.add_message(
        db, session_id, payload.role, payload.content
    )


@router.get("/{session_id}/history", response_model=List[SessionMessageResponse])
async def get_history(
    session_id: int, limit: int = 50, db: AsyncSession = Depends(get_session)
):
    return await session_service.get_history(db, session_id, limit)
