import asyncio
import os
import sys

# Add the src directory to the python path so we can import ecofood_backend
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from ecofood_backend.database import Base
from ecofood_backend.services.households import create_household
from ecofood_backend.schemas import HouseholdCreate
from ecofood_backend.agent.tools.mcp.memory import add_memory, get_memories

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def verify_memory_tools():
    print("Setting up test database...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # We need to monkeypatch the AsyncSessionFactory used in the memory tool
    from ecofood_backend.agent.tools.mcp import memory
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session():
        async with async_session() as session:
            yield session

    # Patch the imported name in the memory module
    memory.AsyncSessionFactory = mock_session

    async with async_session() as db:
        print("1. Creating a test Household...")
        household_payload = HouseholdCreate(name="Tool Test Family")
        household = await create_household(db, household_payload)
        print(f"   -> Created Household: {household.name} (ID: {household.id})")

        print("2. Testing 'memory.add' tool...")
        memory_data = await add_memory(
            household_id=household.id,
            category="dietary_restriction",
            value="Gluten-free",
        )
        print(f"   -> Added Memory: {memory_data}")

        print("3. Testing 'memory.get' tool...")
        memories = await get_memories(household_id=household.id)
        print(f"   -> Retrieved {len(memories)} memories.")
        
        found = False
        for m in memories:
            print(f"      - [{m['category']}] {m['value']}")
            if m['value'] == "Gluten-free" and m['category'] == "dietary_restriction":
                found = True
        
        if found:
            print("\nSUCCESS: Memory tools verification passed!")
        else:
            print("\nFAILURE: Created memory was not found via tool.")

if __name__ == "__main__":
    asyncio.run(verify_memory_tools())
