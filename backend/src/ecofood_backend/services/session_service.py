from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ecofood_backend.models import Session, SessionMessage


class SessionService:
    async def create_session(
        self, db: AsyncSession, household_id: int, session_uuid: Optional[str] = None
    ) -> Session:
        if not session_uuid:
            session_uuid = str(uuid4())

        session = Session(household_id=household_id, session_uuid=session_uuid)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def get_session(
        self, db: AsyncSession, session_uuid: str
    ) -> Optional[Session]:
        result = await db.execute(
            select(Session).where(Session.session_uuid == session_uuid)
        )
        return result.scalar_one_or_none()

    async def add_message(
        self, db: AsyncSession, session_id: int, role: str, content: str
    ) -> SessionMessage:
        message = SessionMessage(session_id=session_id, role=role, content=content)
        db.add(message)
        await db.commit()
        await db.refresh(message)
        return message

    async def get_history(
        self, db: AsyncSession, session_id: int, limit: int = 50
    ) -> List[SessionMessage]:
        # Get the last N messages
        query = (
            select(SessionMessage)
            .where(SessionMessage.session_id == session_id)
            .order_by(SessionMessage.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        messages = result.scalars().all()
        return list(reversed(messages))


session_service = SessionService()
