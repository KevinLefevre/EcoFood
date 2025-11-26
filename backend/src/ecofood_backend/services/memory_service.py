from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ecofood_backend.models import LongTermMemory


class MemoryService:
    async def add_memory(
        self,
        db: AsyncSession,
        household_id: int,
        category: str,
        value: str,
        source_session_id: Optional[int] = None,
    ) -> LongTermMemory:
        memory = LongTermMemory(
            household_id=household_id,
            category=category,
            value=value,
            source_session_id=source_session_id,
        )
        db.add(memory)
        await db.commit()
        await db.refresh(memory)
        return memory

    async def get_memories(
        self, db: AsyncSession, household_id: int, category: Optional[str] = None
    ) -> List[LongTermMemory]:
        query = select(LongTermMemory).where(LongTermMemory.household_id == household_id)
        if category:
            query = query.where(LongTermMemory.category == category)

        result = await db.execute(query)
        return list(result.scalars().all())


memory_service = MemoryService()
