import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath("/home/kuku/projects/EcoFood/backend/src"))

from ecofood_backend.database import init_db, get_session
from ecofood_backend.services.session_service import session_service
from ecofood_backend.services.memory_service import memory_service
from ecofood_backend.services import households as household_service
from ecofood_backend.schemas import HouseholdCreate

async def verify():
    await init_db()
    async for db in get_session():
        print("Creating household...")
        household = await household_service.create_household(db, HouseholdCreate(name="Memory Test Household"))
        print(f"Household created: {household.id}")

        print("Creating session...")
        session = await session_service.create_session(db, household.id)
        print(f"Session created: {session.session_uuid}")

        print("Adding memory...")
        await memory_service.add_memory(db, household.id, "preference", "I love spicy food and hate cilantro.")
        print("Memory added.")

        print("Adding message to session...")
        await session_service.add_message(db, session.id, "user", "Hello, I want to plan a dinner.")
        print("Message added.")

        print("Retrieving history...")
        history = await session_service.get_history(db, session.id)
        print(f"History length: {len(history)}")
        assert len(history) == 1
        assert history[0].content == "Hello, I want to plan a dinner."

        print("Retrieving memories...")
        memories = await memory_service.get_memories(db, household.id)
        print(f"Memories found: {len(memories)}")
        assert len(memories) >= 1
        assert "spicy food" in memories[0].value

        print("Verification successful!")
        return

if __name__ == "__main__":
    asyncio.run(verify())
