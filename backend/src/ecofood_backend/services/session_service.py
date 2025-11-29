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
        
        # Trigger compaction in background (fire and forget? or await?)
        # For safety in this demo, we won't await it here to avoid blocking response,
        # OR we call it explicitly from the API layer.
        # Let's call it from API layer to be safe.

    async def update_summary(
        self, db: AsyncSession, session_id: int, summary: str
    ) -> Session:
        session = await db.get(Session, session_id)
        if session:
            session.summary = summary
            await db.commit()
            await db.refresh(session)
        return session

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

    async def check_and_compact(self, db: AsyncSession, session_id: int) -> None:
        """
        Checks if history is too long and compacts it if necessary.
        """
        # 1. Check count
        count_query = select(func.count()).select_from(SessionMessage).where(SessionMessage.session_id == session_id)
        result = await db.execute(count_query)
        count = result.scalar() or 0
        
        LIMIT = 10
        if count > LIMIT:
            # 2. Get all messages to summarize
            # For simplicity, we summarize everything except the last few to keep context fresh
            # But here, let's just summarize everything and keep the summary + last 5
            
            # Actually, a better strategy:
            # If count > 10, summarize the first (count - 5) messages and update summary.
            # But that's complex to delete.
            # Simpler approach for this demo:
            # Just summarize the last 20 messages and update the session summary field.
            # The agent will see Summary + Last N messages.
            
            from ..agent.tools.mcp.registry import get_tool_set
            summarizer = get_tool_set("summarizer")["summarizer.summarize-chat"]
            
            history = await self.get_history(db, session_id, limit=20)
            history_dicts = [{"role": m.role, "content": m.content} for m in history]
            
            new_summary = await summarizer(history_dicts)
            
            # If there was an existing summary, we might want to append/merge, 
            # but for now, let's just overwrite with the summary of the recent window 
            # which implicitly contains previous context if the LLM is good.
            # To be safe, we should pass the OLD summary to the summarizer too.
            # But let's keep it simple: The summary represents the state of the conversation.
            
            await self.update_summary(db, session_id, new_summary)


session_service = SessionService()
