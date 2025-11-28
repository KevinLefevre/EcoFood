import sys
import os
from datetime import date
from unittest.mock import MagicMock, AsyncMock
import asyncio

# Mock database dependencies
sys.modules["sqlalchemy"] = MagicMock()
sys.modules["sqlalchemy.ext.asyncio"] = MagicMock()
sys.modules["sqlalchemy.orm"] = MagicMock()
sys.modules["ecofood_backend.main"] = MagicMock()
sys.modules["ecofood_backend.routers"] = MagicMock()

# Mock models
mock_models = MagicMock()
sys.modules["ecofood_backend.models"] = mock_models
mock_models.MealPlan = MagicMock()
mock_models.MealPlanEntry = MagicMock()

# Mock schemas
mock_schemas = MagicMock()
sys.modules["ecofood_backend.schemas"] = mock_schemas

class MockStatPoint:
    def __init__(self, label, mean_calories, mean_co2_per_meal, total_co2):
        self.label = label
        self.mean_calories = mean_calories
        self.mean_co2_per_meal = mean_co2_per_meal
        self.total_co2 = total_co2
    def __eq__(self, other):
        return self.__dict__ == other.__dict__
    def __repr__(self):
        return f"StatPoint(label={self.label}, cals={self.mean_calories}, co2={self.total_co2})"

class MockStatsResponse:
    def __init__(self, weekly, monthly, yearly):
        self.weekly = weekly
        self.monthly = monthly
        self.yearly = yearly
    def __repr__(self):
        return f"StatsResponse(weekly={self.weekly}, monthly={self.monthly}, yearly={self.yearly})"

mock_schemas.StatPoint = MockStatPoint
mock_schemas.StatsResponse = MockStatsResponse
# Mock other schemas used in imports
mock_schemas.MealPlanEntryResponse = MagicMock()
mock_schemas.MealPlanEntryUpdate = MagicMock()
mock_schemas.MealPlanResponse = MagicMock()
mock_schemas.MealPlanSummaryResponse = MagicMock()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

# Import service
# We need to make sure the import works even with mocks
from ecofood_backend.services.meal_plans import get_household_stats

# Mock MealPlanEntry for the test data
class MockEntry:
    def __init__(self, day, calories_per_person, co2_per_person):
        self.day = day
        self.calories_per_person = calories_per_person
        self.co2_per_person = co2_per_person

async def test_stats_aggregation():
    print("INFO:__main__:Testing stats aggregation...")
    
    # Mock DB session
    db = AsyncMock()
    
    # Mock entries
    # 2023-10-01 is Sunday (Week 39)
    # 2023-10-02 is Monday (Week 40)
    # 2023-11-01 is Wednesday (Week 44)
    entries = [
        MockEntry(date(2023, 10, 1), 500, 1000), 
        MockEntry(date(2023, 10, 2), 600, 1200), 
        MockEntry(date(2023, 11, 1), 700, 1400), 
    ]
    
    # Mock result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = entries
    db.execute.return_value = mock_result
    
    stats = await get_household_stats(db, 1)
    
    print(f"INFO:__main__:Computed Stats: {stats}")
    
    # Verify Weekly
    # Week 39: 1 entry, 500 cals, 1000 co2
    # Week 40: 1 entry, 600 cals, 1200 co2
    # Week 44: 1 entry, 700 cals, 1400 co2
    
    if len(stats.weekly) != 3:
         print(f"ERROR: Expected 3 weeks, got {len(stats.weekly)}")
         sys.exit(1)

    w39 = next((s for s in stats.weekly if "W39" in s.label), None)
    if not w39 or w39.total_co2 != 1000:
        print(f"ERROR: Week 39 stats mismatch: {w39}")
        sys.exit(1)

    # Verify Monthly
    # Oct: 2 entries (500+600)/2 = 550 cals, (1000+1200)/2 = 1100 co2, total 2200
    # Nov: 1 entry 700 cals, 1400 co2, total 1400
    
    oct_stats = next((s for s in stats.monthly if s.label == "2023-10"), None)
    if not oct_stats:
        print("ERROR: Missing Oct 2023 stats")
        sys.exit(1)
        
    if oct_stats.mean_calories != 550:
        print(f"ERROR: Oct mean cals mismatch. Expected 550, got {oct_stats.mean_calories}")
        sys.exit(1)
        
    if oct_stats.total_co2 != 2200:
        print(f"ERROR: Oct total CO2 mismatch. Expected 2200, got {oct_stats.total_co2}")
        sys.exit(1)

    print("INFO:__main__:SUCCESS: Stats aggregation verified.")

async def test_insights():
    print("INFO:__main__:Testing insights generation...")
    
    # Mock generate_text_async
    # We need to patch it where it is imported in meal_plans.py
    # Since we imported get_household_stats from meal_plans, we can patch it there
    
    with unittest.mock.patch("ecofood_backend.services.meal_plans.generate_text_async", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = {"text": '{"insight": "Good job!"}'}
        
        # Create dummy stats
        stats = MockStatsResponse([], [], [])
        
        from ecofood_backend.services.meal_plans import generate_stats_insight
        insight = await generate_stats_insight(stats)
        
        print(f"INFO:__main__:Generated Insight: {insight}")
        
        if insight != "Good job!":
            print(f"ERROR: Insight mismatch. Expected 'Good job!', got '{insight}'")
            sys.exit(1)
            
    print("INFO:__main__:SUCCESS: Insights generation verified.")

if __name__ == "__main__":
    import unittest.mock
    asyncio.run(test_stats_aggregation())
    asyncio.run(test_insights())
