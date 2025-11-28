import asyncio
import os
import sys

# Add the src directory to the python path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Connection string from docker-compose (using localhost since we run from host)
DATABASE_URL = "postgresql+asyncpg://admin:adminpwd@localhost:5432/ecofood"

async def add_column():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_async_engine(DATABASE_URL, echo=True)

    async with engine.begin() as conn:
        print("Checking if column exists...")
        # Check if column exists to avoid error
        result = await conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='meal_plan_entries' AND column_name='co2_per_person';"
        ))
        if result.scalar():
            print("Column 'co2_per_person' already exists.")
        else:
            print("Adding 'co2_per_person' column...")
            await conn.execute(text(
                "ALTER TABLE meal_plan_entries ADD COLUMN co2_per_person INTEGER;"
            ))
            print("Column added successfully.")

    await engine.dispose()

if __name__ == "__main__":
    try:
        asyncio.run(add_column())
    except Exception as e:
        print(f"Error: {e}")
