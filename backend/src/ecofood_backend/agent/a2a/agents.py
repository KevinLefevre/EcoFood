from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Set

from ..tools.mcp import get_tool_set
from .context import SessionContext


AgentKind = Literal["sequential", "parallel"]


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
    profile = self._profile(members)
    ctx.set("household_profile", profile)
    return AgentResult(self.name, "profile.ready", {"profile": profile})


class MealArchitectAgent(BaseAgent):
  def __init__(self) -> None:
    super().__init__("meal-architect", kind="sequential")
    self._recipes = get_tool_set("recipes")["recipes.search"]
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
  ) -> AgentResult:
    if self._llm_plan is None:
      raise RuntimeError(
        "chef.plan-week tool unavailable. Install the gemini extra and set GEMINI_API_KEY."
      )

    try:
      llm_payload = self._llm_plan(
        profile=profile,
        notes=notes,
        eco_friendly=eco_friendly,
        kitchen_tools=kitchen_tools,
      )
    except Exception as exc:  # pragma: no cover - ensure visibility
      raise RuntimeError(f"Gemini menu generation failed: {exc}") from exc

    plan: List[Dict[str, Any]] = llm_payload.get("plan") or []
    if not plan:
      raise RuntimeError("Gemini did not return a plan; cannot proceed.")

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
      ingredient_lines = [
        format_ingredient(ingredient)
        for ingredient in item.get("ingredients", [])
        if isinstance(ingredient, dict)
      ]
      if not ingredient_lines and item.get("summary"):
        ingredient_lines = [item["summary"]]
      plan_items.append({"name": item["title"], "ingredients": ingredient_lines})
    shopping = self._shopping(plan_items)

    events = [
      {
        "title": f"{item['day']} – {item['title']}",
        "date": f"2024-07-{idx+1:02d}",
        "description": (
          f"{item.get('summary', 'Meal')} | prep {item.get('prep_minutes') or '?'} min · "
          f"cook {item.get('cook_minutes') or '?'} min · "
          f"{item.get('calories_per_person') or '?'} kcal/person"
        ),
      }
      for idx, item in enumerate(plan)
    ]
    calendar = self._calendar(events)

    final_plan = {
      "plan": plan,
      "reviews": {
        "nutrition": nutrition_review,
        "pantry": pantry_review,
      },
      "shopping_list": shopping,
      "calendar": calendar,
    }

    ctx.set("final_plan", final_plan)
    return AgentResult(self.name, "plan.final", final_plan)


async def run_parallel(*tasks: "asyncio.Task[AgentResult]") -> List[AgentResult]:
  results = await asyncio.gather(*tasks)
  return list(results)
