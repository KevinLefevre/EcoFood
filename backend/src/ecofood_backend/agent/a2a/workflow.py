from __future__ import annotations

import asyncio
from dataclasses import dataclass
import logging
import time
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
  days: Optional[List[str]] = None


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
    self._logger = logging.getLogger(__name__)

  async def generate(self, request: MealPlanRequest) -> Dict[str, Any]:
    ctx = SessionContext(session_id=request.session_id)

    # Sequential phase 1: household profiling.
    household_inputs = self._describe_inputs(members=request.members)
    self._logger.info("[Workflow] %s input=%s", self.household_agent.name, household_inputs)
    profile_timer = time.perf_counter()
    profile_result = await self.household_agent.run(ctx, members=request.members)
    self._log_agent(profile_result, time.perf_counter() - profile_timer, household_inputs)
    ctx.set("kitchen_tools", request.kitchen_tools)

    # Sequential phase 2: plan architect uses the profile.
    architect_inputs = self._describe_inputs(
      profile=profile_result.payload["profile"],
      notes=request.notes,
      eco_friendly=request.eco_friendly,
      kitchen_tools=request.kitchen_tools,
      days=request.days,
    )
    self._logger.info("[Workflow] %s input=%s", self.architect_agent.name, architect_inputs)
    architect_timer = time.perf_counter()
    plan_result = await self.architect_agent.run(
      ctx,
      profile=profile_result.payload["profile"],
      notes=request.notes,
      eco_friendly=request.eco_friendly,
      kitchen_tools=request.kitchen_tools,
      days=request.days,
    )
    self._log_agent(plan_result, time.perf_counter() - architect_timer, architect_inputs)

    chef_inputs = self._describe_inputs(
      plan=plan_result.payload["plan"],
      profile=profile_result.payload["profile"],
      notes=request.notes,
    )
    self._logger.info("[Workflow] %s input=%s", self.chef_agent.name, chef_inputs)
    chef_timer = time.perf_counter()
    chef_result = await self.chef_agent.run(
      ctx,
      plan=plan_result.payload["plan"],
      profile=profile_result.payload["profile"],
      notes=request.notes,
    )
    self._log_agent(chef_result, time.perf_counter() - chef_timer, chef_inputs)

    plan_items = chef_result.payload["plan"]

    # Parallel phase: nutrition + pantry reviewers evaluate the same plan.
    nutrition_inputs = self._describe_inputs(plan=plan_items)
    self._logger.info("[Workflow] %s input=%s", self.nutrition_agent.name, nutrition_inputs)
    nutrition_task = asyncio.create_task(
      self.nutrition_agent.run(ctx, plan=plan_items)
    )
    pantry_inputs = self._describe_inputs(
      soon_expiring=request.pantry_items,
      plan=plan_items,
      use_leftovers=request.use_leftovers,
    )
    self._logger.info("[Workflow] %s input=%s", self.pantry_agent.name, pantry_inputs)
    pantry_task = asyncio.create_task(
      self.pantry_agent.run(
        ctx,
        soon_expiring=request.pantry_items,
        plan=plan_items,
        use_leftovers=request.use_leftovers,
      )
    )
    review_results = await run_parallel(nutrition_task, pantry_task)
    for review in review_results:
      self._log_agent(
        review,
        0.0,
        nutrition_inputs if review.agent == self.nutrition_agent.name else pantry_inputs,
      )

    nutrition_payload = next(
      res.payload for res in review_results if res.stage == "plan.review.nutrition"
    )
    pantry_payload = next(
      res.payload for res in review_results if res.stage == "plan.review.pantry"
    )

    # Sequential phase 3: synthesis agent merges everything.
    synthesis_inputs = self._describe_inputs(
      plan=plan_items,
      nutrition_review=nutrition_payload["analysis"],
      pantry_review=pantry_payload,
    )
    self._logger.info("[Workflow] %s input=%s", self.synthesis_agent.name, synthesis_inputs)
    synthesis_timer = time.perf_counter()
    final_result = await self.synthesis_agent.run(
      ctx,
      plan=plan_items,
      nutrition_review=nutrition_payload["analysis"],
      pantry_review=pantry_payload,
    )
    self._log_agent(final_result, time.perf_counter() - synthesis_timer, synthesis_inputs)

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

  def _log_agent(self, result: AgentResult, elapsed: float, inputs_summary: str | None = None) -> None:
    payload_keys = ",".join(sorted(result.payload.keys())) if isinstance(result.payload, dict) else "payload"
    extra_details = ""
    if result.stage == "plan.candidate" and isinstance(result.payload, dict):
      plan_items = result.payload.get("plan")
      extra_details = f" plan_items={len(plan_items) if isinstance(plan_items, list) else 0}"
      llm = result.payload.get("llm")
      if isinstance(llm, dict) and llm.get("prompt"):
        prompt = llm.get("prompt") or ""
        extra_details += f" prompt_len={len(prompt)}"
    elif result.stage == "plan.final" and isinstance(result.payload, dict):
      plan_items = result.payload.get("plan")
      extra_details = f" plan_items={len(plan_items) if isinstance(plan_items, list) else 0}"
    self._logger.info(
      "[Workflow] %s finished %s in %.2fs inputs=%s payload=%s%s",
      result.agent,
      result.stage,
      elapsed,
      inputs_summary or "-",
      payload_keys,
      extra_details,
    )

  def _describe_inputs(self, **kwargs: Any) -> str:
    parts: List[str] = []
    for key, value in kwargs.items():
      parts.append(f"{key}={self._summarize_value(value)}")
    return "; ".join(parts)

  def _summarize_value(self, value: Any) -> str:
    if isinstance(value, list):
      return f"list(len={len(value)})"
    if isinstance(value, dict):
      return f"dict(keys={len(value)})"
    if isinstance(value, str):
      return value if len(value) <= 80 else value[:77] + "..."
    if value is None:
      return "None"
    return str(value)
