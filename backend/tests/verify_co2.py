import asyncio
import os
import sys
from datetime import date

# Add the src directory to the python path so we can import ecofood_backend
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from ecofood_backend.database import Base
from ecofood_backend.services.households import create_household
from ecofood_backend.services.meal_plans import save_plan, update_entry
from ecofood_backend.schemas import HouseholdCreate, MealPlanEntryUpdate

# Use an in-memory SQLite database for testing
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async def verify_co2_feature():
    print("Setting up test database...")
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        print("1. Creating a test Household...")
        household_payload = HouseholdCreate(name="CO2 Test Family")
        household = await create_household(db, household_payload)
        
        print("2. Saving a plan with CO2 data...")
        week_start = date(2025, 11, 24)
        plan_items = [
            {
                "day": "Mon",
                "meal": "Dinner",
                "title": "Low Carbon Pasta",
                "summary": "Delicious pasta with local veggies.",
                "ingredients": [],
                "steps": [],
                "calories_per_person": 500,
                "co2_per_person": 300, # 300g CO2
            }
        ]
        
        plan = await save_plan(
            db,
            household_id=household.id,
            week_start=week_start,
            session_id="test-session",
            plan_items=plan_items,
            timeline=[],
            eco_friendly=True,
            use_leftovers=False,
            notes="Test notes",
            attendee_map={("Mon", "Dinner"): [1]}, # Assuming member ID 1 exists
        )
        
        if not plan.entries:
            print("   -> FAILURE: No entries saved. Check attendee_map.")
            return

        entry = plan.entries[0]
        print(f"   -> Saved Entry: {entry.title}")
        print(f"   -> Calories: {entry.calories_per_person}")
        print(f"   -> CO2: {entry.co2_per_person}")
        
        if entry.co2_per_person == 300:
            print("   -> SUCCESS: CO2 data saved correctly.")
        else:
            print(f"   -> FAILURE: Expected 300, got {entry.co2_per_person}")

        print("3. Updating CO2 data...")
        update_payload = MealPlanEntryUpdate(co2_per_person=450)
        updated_entry = await update_entry(db, entry.id, update_payload)
        
        print(f"   -> Updated CO2: {updated_entry.co2_per_person}")
        
        if updated_entry.co2_per_person == 450:
            print("   -> SUCCESS: CO2 data updated correctly.")
        else:
            print(f"   -> FAILURE: Expected 450, got {updated_entry.co2_per_person}")

if __name__ == "__main__":
    asyncio.run(verify_co2_feature())
