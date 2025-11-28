import asyncio
import logging
import os
import sys
from unittest.mock import MagicMock

# Mock database dependencies
sys.modules["asyncpg"] = MagicMock()
sys.modules["sqlalchemy.ext.asyncio"] = MagicMock()
sys.modules["ecofood_backend.database"] = MagicMock()
sys.modules["ecofood_backend.main"] = MagicMock()
sys.modules["ecofood_backend.routers"] = MagicMock()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from ecofood_backend.agent.a2a.agents import CO2EstimatorAgent, PlanSynthesisAgent
from ecofood_backend.agent.a2a.context import SessionContext

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_co2_agent():
    logger.info("Verifying CO2EstimatorAgent...")
    
    # Mock context
    ctx = SessionContext(session_id="test-session")
    
    # Mock plan
    plan = [
        {
            "day": "Mon",
            "meal": "Dinner",
            "title": "Beef Burger",
            "ingredients": [{"name": "Beef patty", "quantity": "1", "unit": "pc"}]
        }
    ]
    
    # Run agent
    agent = CO2EstimatorAgent()
    try:
        result = await agent.run(ctx, plan)
        logger.info(f"Agent result: {result.payload}")
        
        estimates = result.payload.get("estimates", [])
        if not estimates:
            logger.error("No estimates returned!")
            return
            
        est = estimates[0]
        if est["meal"] == "Dinner" and est["co2_per_person"] is not None:
            logger.info("SUCCESS: CO2EstimatorAgent returned an estimate.")
        else:
            logger.error(f"FAILURE: Invalid estimate: {est}")
            
    except Exception as e:
        logger.error(f"Agent failed: {e}")
        return

    return result.payload

async def verify_synthesis_merge(carbon_review):
    logger.info("Verifying PlanSynthesisAgent merging...")
    
    ctx = SessionContext(session_id="test-session")
    
    plan = [
        {
            "day": "Mon",
            "meal": "Dinner",
            "title": "Beef Burger",
            "ingredients": [{"name": "Beef patty", "quantity": "1", "unit": "pc"}],
            "calories_per_person": 800
        }
    ]
    
    nutrition_review = {"analysis": "Good"}
    pantry_review = {"suggestions": []}
    
    agent = PlanSynthesisAgent()
    
    # Mock shopping/calendar tools to avoid external calls if possible, 
    # but they are initialized in __init__. 
    # We'll just let them run or fail - if they fail due to missing env vars we might need to mock them.
    # Assuming they are safe or we can ignore errors if they don't block the merge logic.
    # Actually, PlanSynthesisAgent calls self._shopping and self._calendar.
    # We might need to mock those.
    
    # Monkey patch tools for synthesis
    agent._shopping = lambda x: ["Shopping List"]
    agent._calendar = lambda x: "ICS Content"
    
    try:
        # Verify merging
        result = await agent.run(ctx, plan, nutrition_review, pantry_review, carbon_review)
        
        final_plan = result.payload.get("plan", [])
        stats = result.payload.get("stats", {})
        
        print(f"INFO:__main__:Stats: {stats}")

        if not final_plan:
            print("ERROR: Plan is empty")
            sys.exit(1)
            
        merged_item = final_plan[0]
        if merged_item.get("co2_per_person") == 3500:
            print(f"INFO:__main__:SUCCESS: co2_per_person merged: {merged_item['co2_per_person']}")
        else:
            print(f"ERROR: co2_per_person not merged correctly. Got: {merged_item.get('co2_per_person')}")
            sys.exit(1)

        # Verify stats
        if stats.get("mean_co2_per_person") == 3500 and stats.get("total_co2_per_person") == 3500:
            print("INFO:__main__:SUCCESS: Weekly stats computed correctly.")
        else:
            print(f"ERROR: Stats incorrect. Got: {stats}")
            sys.exit(1)
             
    except Exception as e:
        logger.error(f"Synthesis failed: {e}")

async def main():
    # Ensure API key is present
    if not os.getenv("GEMINI_API_KEY"):
        logger.error("GEMINI_API_KEY is missing. Cannot run verification.")
        return

    carbon_review = await verify_co2_agent()
    if carbon_review:
        await verify_synthesis_merge(carbon_review)

if __name__ == "__main__":
    asyncio.run(main())
