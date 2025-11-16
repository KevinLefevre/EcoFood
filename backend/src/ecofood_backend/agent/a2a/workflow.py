from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

from .agents import (
  ChefCurationAgent,
  HouseholdProfilerAgent,
  MealArchitectAgent,
  NutritionReviewAgent,
  PantryReviewAgent,
  PlanSynthesisAgent,
  run_parallel,
)
from .context import SessionContext


@dataclass
class MealPlanRequest:
  session_id: str
  members: List[Dict[str, Any]]
  pantry_items: List[Dict[str, Any]]
  kitchen_tools: List[Dict[str, Any]]
  notes: Optional[str] = None
  household_id: Optional[int] = None
  week_start: Optional[date] = None
  eco_friendly: bool = False
  use_leftovers: bool = False


class MealPlanningWorkflow:
  """
  Coordinates sequential and parallel agent phases for plan generation.
  """

  def __init__(self) -> None:
    self.household_agent = HouseholdProfilerAgent()
    self.architect_agent = MealArchitectAgent()
    self.chef_agent = ChefCurationAgent()
    self.nutrition_agent = NutritionReviewAgent()
    self.pantry_agent = PantryReviewAgent()
    self.synthesis_agent = PlanSynthesisAgent()

  async def generate(self, request: MealPlanRequest) -> Dict[str, Any]:
    ctx = SessionContext(session_id=request.session_id)

    # Sequential phase 1: household profiling.
    profile_result = await self.household_agent.run(ctx, members=request.members)
    ctx.set("kitchen_tools", request.kitchen_tools)

    # Sequential phase 2: plan architect uses the profile.
    plan_result = await self.architect_agent.run(
      ctx,
      profile=profile_result.payload["profile"],
      notes=request.notes,
      eco_friendly=request.eco_friendly,
      kitchen_tools=request.kitchen_tools,
    )

    chef_result = await self.chef_agent.run(
      ctx,
      plan=plan_result.payload["plan"],
      profile=profile_result.payload["profile"],
      notes=request.notes,
    )

    plan_items = chef_result.payload["plan"]

    # Parallel phase: nutrition + pantry reviewers evaluate the same plan.
    nutrition_task = asyncio.create_task(
      self.nutrition_agent.run(ctx, plan=plan_items)
    )
    pantry_task = asyncio.create_task(
      self.pantry_agent.run(
        ctx,
        soon_expiring=request.pantry_items,
        plan=plan_items,
        use_leftovers=request.use_leftovers,
      )
    )
    review_results = await run_parallel(nutrition_task, pantry_task)

    nutrition_payload = next(
      res.payload for res in review_results if res.stage == "plan.review.nutrition"
    )
    pantry_payload = next(
      res.payload for res in review_results if res.stage == "plan.review.pantry"
    )

    # Sequential phase 3: synthesis agent merges everything.
    final_result = await self.synthesis_agent.run(
      ctx,
      plan=plan_items,
      nutrition_review=nutrition_payload["analysis"],
      pantry_review=pantry_payload,
    )

    return {
      "session_id": request.session_id,
      "timeline": [
        profile_result.__dict__,
        plan_result.__dict__,
        chef_result.__dict__,
        *[res.__dict__ for res in review_results],
        final_result.__dict__,
      ],
      "final_plan": final_result.payload,
      "context": ctx.snapshot(),
      "options": {
        "household_id": request.household_id,
        "week_start": request.week_start.isoformat() if request.week_start else None,
        "eco_friendly": request.eco_friendly,
        "use_leftovers": request.use_leftovers,
        "notes": request.notes,
      },
    }
