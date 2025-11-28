from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
from typing import Any, Dict, List, Literal, Optional, Set

from ..tools.mcp import get_tool_set
from ..cache import profile_cache
from .context import SessionContext


AgentKind = Literal["sequential", "parallel"]

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
  agent: str
  stage: str
  payload: Dict[str, Any]


class BaseAgent:
  """
  Base class for specialized agents participating in the workflow.
  """

  def __init__(self, name: str, kind: AgentKind):
    self.name = name
    self.kind = kind

  async def run(self, ctx: SessionContext, **kwargs: Any) -> AgentResult:
    raise NotImplementedError


class HouseholdProfilerAgent(BaseAgent):
  def __init__(self) -> None:
    super().__init__("household-profiler", kind="sequential")
    tools = get_tool_set("household")
    self._profile = tools["household.profile"]

  async def run(self, ctx: SessionContext, members: List[Dict[str, Any]]) -> AgentResult:
    cached = profile_cache.get(members)
    if cached:
      logger.info("[HouseholdProfiler] Using cached profile")
      profile = cached
    else:
      profile = self._profile(members)
      profile_cache.set(members, profile)
      
    ctx.set("household_profile", profile)
    return AgentResult(self.name, "profile.ready", {"profile": profile})


class MealArchitectAgent(BaseAgent):
  def __init__(self) -> None:
    super().__init__("meal-architect", kind="sequential")
    self._plans = get_tool_set("plans")["plans.save-and-tag"]
    chef_tools = get_tool_set("chef")
    self._llm_plan = chef_tools.get("chef.plan-week")

  MEAL_SLOTS: List[str] = ["Breakfast", "Lunch", "Dinner"]

  async def run(
    self,
    ctx: SessionContext,
    profile: Dict[str, Any],
    notes: Optional[str] = None,
    eco_friendly: bool = False,
    kitchen_tools: Optional[List[Dict[str, Any]]] = None,
    days: Optional[List[str]] = None,
    calories_target: Optional[int] = None,
    leftover_notes: Optional[str] = None,
    mood: Optional[int] = None,
  ) -> AgentResult:
    if self._llm_plan is None:
      raise RuntimeError(
        "chef.plan-week tool unavailable. Install the gemini extra and set GEMINI_API_KEY."
      )

    try:
      llm_payload = await self._llm_plan(
        profile=profile,
        notes=notes,
        eco_friendly=eco_friendly,
        kitchen_tools=kitchen_tools,
        days=days,
        calories_target=calories_target,
        leftover_notes=leftover_notes,
        mood=mood,
      )
    except Exception as exc:  # pragma: no cover - ensure visibility
      raise RuntimeError(f"Gemini menu generation failed: {exc}") from exc

    logger.info(
      "[MealArchitect] plan request days=%s first-lines=%s",
      days or self.MEAL_SLOTS,
      (llm_payload.get("prompt") or "").splitlines()[0:4],
    )
    prompt_text = llm_payload.get("prompt") or ""
    if prompt_text:
      logger.info("[MealArchitect] prompt body (len=%s)>>>\n%s", len(prompt_text), prompt_text)

    plan: List[Dict[str, Any]] = llm_payload.get("plan") or []
    if not plan:
      prompt_preview = (llm_payload.get("prompt") or "")[:240]
      logger.error(
        "Gemini returned an empty plan (days=%s). Prompt preview: %s",
        ",".join(days or self.MEAL_SLOTS),
        prompt_preview,
      )
      raise RuntimeError("Gemini did not return a plan; cannot proceed.")

    try:
      plan_preview = json.dumps(plan[:3], ensure_ascii=False)
    except Exception:
      plan_preview = str(plan[:3])
    logger.info("[MealArchitect] plan preview=%s", plan_preview[:1200])

    stored = self._plans({"week": plan, "notes": notes or ""}, tags=["draft"])
    ctx.set("plan_draft", {"items": plan, "storage": stored})

    payload = {
      "plan": plan,
      "plan_id": stored["plan_id"],
      "notes": notes,
      "source": "gemini",
      "llm": {
        "model": llm_payload.get("model"),
        "prompt": llm_payload.get("prompt"),
        "raw_text": llm_payload.get("raw_text"),
      },
    }

    return AgentResult(self.name, "plan.candidate", payload)


class ChefCurationAgent(BaseAgent):
  def __init__(self) -> None:
    super().__init__("chef-curator", kind="sequential")
    self._chef = get_tool_set("chef")["chef.build-menu"]

  async def run(
    self,
    ctx: SessionContext,
    plan: List[Dict[str, Any]],
    profile: Dict[str, Any],
    notes: Optional[str] = None,
  ) -> AgentResult:
    curated = self._chef(plan=plan, profile=profile, notes=notes)
    ctx.set("chef_menu", curated)
    return AgentResult(
      self.name,
      "plan.enhanced",
      curated,
    )


class NutritionReviewAgent(BaseAgent):
  def __init__(self) -> None:
    super().__init__("nutrition-reviewer", kind="parallel")
    self._nutrition = get_tool_set("nutrition")["nutrition.analyze"]

  async def run(self, ctx: SessionContext, plan: List[Dict[str, Any]]) -> AgentResult:
    description = "\n".join(item["summary"] for item in plan)
    analysis = self._nutrition(description)
    ctx.set("nutrition_review", analysis)
    return AgentResult(self.name, "plan.review.nutrition", {"analysis": analysis})


class PantryReviewAgent(BaseAgent):
  def __init__(self) -> None:
    super().__init__("pantry-reviewer", kind="parallel")
    self._pantry = get_tool_set("pantry")["pantry.suggest-usage"]

  async def run(
    self,
    ctx: SessionContext,
    soon_expiring: List[Dict[str, Any]],
    plan: List[Dict[str, Any]],
    use_leftovers: bool = False,
  ) -> AgentResult:
    suggestions = self._pantry(soon_expiring if use_leftovers else [])
    annotated = []
    for idx, item in enumerate(plan):
      annotated.append(
        {
          **item,
          "pantry_hint": suggestions["suggestions"][idx % len(suggestions["suggestions"])]["title"]
          if suggestions.get("suggestions")
          else None,
        }
      )

    ctx.set("pantry_review", {"suggestions": suggestions, "annotated_plan": annotated})
    return AgentResult(
      self.name,
      "plan.review.pantry",
      {"suggestions": suggestions, "annotated_plan": annotated},
    )


class CO2EstimatorAgent(BaseAgent):
  def __init__(self) -> None:
    super().__init__("co2-estimator", kind="parallel")
    self._estimate = get_tool_set("carbon")["carbon.estimate-meal"]

  async def run(self, ctx: SessionContext, plan: List[Dict[str, Any]]) -> AgentResult:
    estimates = []
    for item in plan:
      result = await self._estimate(
        meal_title=item["title"],
        ingredients=item.get("ingredients", [])
      )
      estimates.append({
        "day": item.get("day"),
        "meal": item.get("meal"),
        "co2_per_person": result.get("co2_grams"),
        "rating": result.get("rating"),
        "reasoning": result.get("reasoning")
      })
    
    ctx.set("co2_estimates", estimates)
    return AgentResult(self.name, "plan.review.carbon", {"estimates": estimates})


class PlanSynthesisAgent(BaseAgent):
  def __init__(self) -> None:
    super().__init__("plan-synthesizer", kind="sequential")
    self._shopping = get_tool_set("shopping")["shopping-list.generate"]
    self._calendar = get_tool_set("calendar")["calendar.export-ics"]

  async def run(
    self,
    ctx: SessionContext,
    plan: List[Dict[str, Any]],
    nutrition_review: Dict[str, Any],
    pantry_review: Dict[str, Any],
    carbon_review: Optional[Dict[str, Any]] = None,
  ) -> AgentResult:
    def format_ingredient(ingredient: Dict[str, Any]) -> str:
      parts: List[str] = []
      quantity = ingredient.get("quantity")
      unit = ingredient.get("unit")
      name = ingredient.get("name")
      if quantity not in (None, ""):
        parts.append(str(quantity))
      if unit:
        parts.append(str(unit))
      if name:
        parts.append(str(name))
      text = " ".join(parts).strip() or (name or "ingredient")
      notes = ingredient.get("notes")
      if notes:
        text = f"{text} ({notes})"
      return text

    plan_items = []
    for item in plan:
      # Pass raw ingredients for better aggregation
      raw_ingredients = [
        ing for ing in item.get("ingredients", [])
        if isinstance(ing, dict)
      ]
      plan_items.append({"name": item["title"], "ingredients": raw_ingredients})
    shopping = self._shopping(plan_items)

    # Merge CO2 data back into plan items
    carbon_estimates = (carbon_review or {}).get("estimates", [])
    # Create a map for easy lookup: (day, meal) -> estimate
    co2_map = {
        (est.get("day"), est.get("meal")): est 
        for est in carbon_estimates
    }

    merged_plan = []
    for item in plan:
        key = (item.get("day"), item.get("meal"))
        est = co2_map.get(key)
        new_item = item.copy()
        if est and est.get("co2_per_person"):
            new_item["co2_per_person"] = est.get("co2_per_person")
            # We could also add rating/reasoning if the UI supported it
        merged_plan.append(new_item)

    events = [
      {
        "title": f"{item['day']} – {item['title']}",
        "date": f"2024-07-{idx+1:02d}",
        "description": (
          f"{item.get('summary', 'Meal')} | prep {item.get('prep_minutes') or '?'} min · "
          f"cook {item.get('cook_minutes') or '?'} min · "
          f"{item.get('calories_per_person') or '?'} kcal/person · "
          f"{item.get('co2_per_person') or '?'}g CO2/person"
        ),
      }
      for idx, item in enumerate(merged_plan)
    ]
    calendar = self._calendar(events)

    # Calculate weekly stats
    total_cals = 0
    count_cals = 0
    total_co2 = 0
    count_co2 = 0

    for item in merged_plan:
      cals = item.get("calories_per_person")
      if cals:
        total_cals += cals
        count_cals += 1
      
      co2 = item.get("co2_per_person")
      if co2:
        total_co2 += co2
        count_co2 += 1
    
    stats = {
      "mean_calories_per_person": round(total_cals / count_cals) if count_cals > 0 else 0,
      "mean_co2_per_person": round(total_co2 / count_co2) if count_co2 > 0 else 0,
      "total_co2_per_person": round(total_co2)
    }

    final_plan = {
      "plan": merged_plan,
      "stats": stats,
      "reviews": {
        "nutrition": nutrition_review,
        "pantry": pantry_review,
        "carbon": carbon_review,
      },
      "shopping_list": shopping,
      "calendar": calendar,
    }

    ctx.set("final_plan", final_plan)
    return AgentResult(self.name, "plan.final", final_plan)
