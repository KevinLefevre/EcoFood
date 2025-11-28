from __future__ import annotations

from typing import Any, Dict, List, Optional

from ecofood_backend.database import AsyncSessionFactory
from ecofood_backend.services.memory_service import memory_service


async def add_memory(
    household_id: int,
    category: str,
    value: str,
    source_session_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Add a long-term memory for a household.
    
    Args:
        household_id: The ID of the household.
        category: The category of the memory (e.g., "preference", "dietary_restriction").
        value: The content of the memory.
        source_session_id: Optional ID of the session where this memory originated.
    """
    async with AsyncSessionFactory() as db:
        memory = await memory_service.add_memory(
            db, household_id, category, value, source_session_id
        )
        return {
            "id": memory.id,
            "category": memory.category,
            "value": memory.value,
            "created_at": memory.created_at.isoformat(),
        }


async def get_memories(
    household_id: int,
    category: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve long-term memories for a household.
    
    Args:
        household_id: The ID of the household.
        category: Optional category to filter by.
    """
    async with AsyncSessionFactory() as db:
        memories = await memory_service.get_memories(db, household_id, category)
        return [
            {
                "id": m.id,
                "category": m.category,
                "value": m.value,
                "created_at": m.created_at.isoformat(),
            }
            for m in memories
        ]


TOOLS: Dict[str, Any] = {
    "memory.add": add_memory,
    "memory.get": get_memories,
}
