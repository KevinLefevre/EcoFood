import sys
import os
from datetime import date
from unittest.mock import MagicMock

# Mock database dependencies
sys.modules["sqlalchemy"] = MagicMock()
sys.modules["sqlalchemy.ext.asyncio"] = MagicMock()
sys.modules["sqlalchemy.orm"] = MagicMock()
sys.modules["ecofood_backend.main"] = MagicMock()
sys.modules["ecofood_backend.routers"] = MagicMock()

# Mock schemas to bypass Pydantic version issues
mock_schemas = MagicMock()
sys.modules["ecofood_backend.schemas"] = mock_schemas

class MockMealPlanResponse:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

mock_schemas.MealPlanEntryResponse.model_validate.side_effect = lambda x: x
mock_schemas.MealPlanResponse = MockMealPlanResponse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

# Define simple mock classes
class MockMealPlanEntry:
    def __init__(self, day, slot, calories_per_person, co2_per_person, attendee_ids=None):
        self.day = day
        self.slot = slot
        self.calories_per_person = calories_per_person
        self.co2_per_person = co2_per_person
        self.attendee_ids = attendee_ids or []

class MockMealPlan:
    def __init__(self, id, household_id, week_start, eco_friendly, use_leftovers, entries, timeline=None, notes=None):
        self.id = id
        self.household_id = household_id
        self.week_start = week_start
        self.eco_friendly = eco_friendly
        self.use_leftovers = use_leftovers
        self.entries = entries
        self.timeline = timeline or []
        self.notes = notes

from ecofood_backend.services.meal_plans import _map_plan

def test_dynamic_stats():
    print("INFO:__main__:Testing dynamic stats computation...")
    
    # Create mock entries
    entries = [
        MockMealPlanEntry(
            day=date(2024, 1, 1),
            slot="Dinner",
            calories_per_person=800,
            co2_per_person=3500
        ),
        MockMealPlanEntry(
            day=date(2024, 1, 2),
            slot="Dinner",
            calories_per_person=600,
            co2_per_person=1500
        ),
        MockMealPlanEntry(
            day=date(2024, 1, 3),
            slot="Dinner",
            calories_per_person=None, # Missing data
            co2_per_person=None
        )
    ]
    
    plan = MockMealPlan(
        id=1,
        household_id=1,
        week_start=date(2024, 1, 1),
        eco_friendly=False,
        use_leftovers=False,
        entries=entries,
        timeline=[] # Empty timeline
    )
    
    response = _map_plan(plan)
    stats = response.stats
    
    print(f"INFO:__main__:Computed Stats: {stats}")
    
    expected_mean_cals = round((800 + 600) / 2) # 700
    expected_mean_co2 = round((3500 + 1500) / 2) # 2500
    expected_total_co2 = 3500 + 1500 # 5000
    
    if stats["mean_calories_per_person"] != expected_mean_cals:
        print(f"ERROR: Mean calories mismatch. Expected {expected_mean_cals}, got {stats['mean_calories_per_person']}")
        sys.exit(1)
        
    if stats["mean_co2_per_person"] != expected_mean_co2:
        print(f"ERROR: Mean CO2 mismatch. Expected {expected_mean_co2}, got {stats['mean_co2_per_person']}")
        sys.exit(1)
        
    if stats["total_co2_per_person"] != expected_total_co2:
        print(f"ERROR: Total CO2 mismatch. Expected {expected_total_co2}, got {stats['total_co2_per_person']}")
        sys.exit(1)
        
    print("INFO:__main__:SUCCESS: Dynamic stats computation verified.")

if __name__ == "__main__":
    test_dynamic_stats()
