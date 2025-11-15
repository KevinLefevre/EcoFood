from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

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

  async def run(
    self,
    ctx: SessionContext,
    profile: Dict[str, Any],
    notes: Optional[str] = None,
    eco_friendly: bool = False,
    kitchen_tools: Optional[List[Dict[str, Any]]] = None,
  ) -> AgentResult:
    preferences = profile.get("top_likes", [])
    primary = preferences[0]["name"] if preferences else "balanced"
    if eco_friendly:
      primary = f"plant-based {primary}"
    tools = [
      tool["label"]
      for tool in (kitchen_tools or [])
      if tool.get("quantity", 0) and tool.get("label")
    ]

    recipes = self._recipes(query=primary, limit=5)["recipes"]
    if not recipes:
      recipes = self._recipes(query="", limit=5)["recipes"]

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    plan = []
    for idx, day in enumerate(days):
      recipe = recipes[idx % len(recipes)]
      tool_hint = tools[idx % len(tools)] if tools else "basic cookware"
      plan.append(
        {
          "day": day,
          "meal": "Dinner",
          "recipe_id": recipe["id"],
          "title": recipe["title"],
          "summary": f"{recipe['summary']} (Tool: {tool_hint})",
        }
      )

    stored = self._plans({"week": plan, "notes": notes or ""}, tags=["draft"])
    ctx.set("plan_draft", {"items": plan, "storage": stored})

    return AgentResult(
      self.name,
      "plan.candidate",
      {"plan": plan, "plan_id": stored["plan_id"], "notes": notes},
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
    plan_items = [
      {
        "name": item["title"],
        "ingredients": [
          f"{item['summary']} (placeholder ingredient list)",
        ],
      }
      for item in plan
    ]
    shopping = self._shopping(plan_items)

    events = [
      {
        "title": f"{item['day']} – {item['title']}",
        "date": f"2024-07-{idx+1:02d}",
        "description": item["summary"],
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
