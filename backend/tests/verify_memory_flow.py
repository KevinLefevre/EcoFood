import asyncio
import os
import sys
from datetime import date

# Add the src directory to the python path so we can import ecofood_backend
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from ecofood_backend.database import Base
from ecofood_backend.models import Household, Session, LongTermMemory
from ecofood_backend.services.memory_service import memory_service
from ecofood_backend.services.session_service import session_service
from ecofood_backend.services.households import create_household
from ecofood_backend.schemas import HouseholdCreate

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def verify_memory_flow():
    print("Setting up test database...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        print("1. Creating a test Household...")
        household_payload = HouseholdCreate(name="Test Family")
        household = await create_household(db, household_payload)
        print(f"   -> Created Household: {household.name} (ID: {household.id})")

        print("2. Creating a Session...")
        session = await session_service.create_session(db, household.id)
        print(f"   -> Created Session: {session.session_uuid} (ID: {session.id})")

        print("3. Adding a Message to the Session...")
        msg = await session_service.add_message(db, session.id, "user", "I don't like mushrooms.")
        print(f"   -> Added Message: {msg.content} (Role: {msg.role})")

        print("4. Adding a LongTermMemory...")
        memory_value = "User dislikes mushrooms"
        memory = await memory_service.add_memory(
            db, 
            household.id, 
            "preference", 
            memory_value, 
            source_session_id=session.id
        )
        print(f"   -> Added Memory: {memory.value} (Category: {memory.category})")

        print("5. Retrieving Memories...")
        memories = await memory_service.get_memories(db, household.id)
        print(f"   -> Retrieved {len(memories)} memories.")
        
        found = False
        for m in memories:
            print(f"      - [{m.category}] {m.value} (Source Session ID: {m.source_session_id})")
            if m.value == memory_value and m.source_session_id == session.id:
                found = True
        
        if found:
            print("\nSUCCESS: Memory verification passed!")
        else:
            print("\nFAILURE: Created memory was not found.")

if __name__ == "__main__":
    asyncio.run(verify_memory_flow())
