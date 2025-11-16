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

  MEAL_SLOTS: List[str] = ["Breakfast", "Lunch", "Dinner"]

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
    tool_categories = [
      tool["category"]
      for tool in (kitchen_tools or [])
      if tool.get("quantity", 0) and tool.get("category")
    ]

    def normalize(value: str) -> str:
      return value.lower().strip()

    normalized_labels = [normalize(label) for label in tools]
    normalized_categories = [normalize(cat) for cat in tool_categories]

    ubiquitous_tools = {"mixing bowl", "whisk", "knife", "cutting board"}

    def matches_available_tools(recipe: Dict[str, Any]) -> bool:
      requirements = recipe.get("required_tools") or []
      if not requirements:
        return True
      if not normalized_labels and not normalized_categories:
        return True
      for requirement in requirements:
        req = normalize(requirement)
        if req in ubiquitous_tools:
          continue
        label_ok = any(req in label or label in req for label in normalized_labels)
        category_ok = any(req in category or category in req for category in normalized_categories)
        if not label_ok and not category_ok:
          return False
      return True

    def pick_tool_hint(recipe: Dict[str, Any]) -> str:
      requirements = recipe.get("required_tools") or []
      for requirement in requirements:
        req = normalize(requirement)
        for label, normalized in zip(tools, normalized_labels):
          if req in normalized or normalized in req:
            return label
        for category, normalized in zip(tool_categories, normalized_categories):
          if req in normalized or normalized in req:
            return category
      if requirements:
        return requirements[0]
      if tools:
        return tools[0]
      if tool_categories:
        return tool_categories[0]
      return "basic cookware"

    recipe_cache: Dict[str, List[Dict[str, Any]]] = {}

    def get_recipes_for_query(query: str) -> List[Dict[str, Any]]:
      key = query.strip().lower()
      if key not in recipe_cache:
        recipe_cache[key] = self._recipes(query=query, limit=10)["recipes"]
      return recipe_cache[key]

    recipes = get_recipes_for_query(primary)
    if len(recipes) < 7:
      additional = get_recipes_for_query("")
      existing_ids = {recipe["id"] for recipe in recipes}
      recipes.extend([item for item in additional if item["id"] not in existing_ids])
    if not recipes:
      recipes = get_recipes_for_query("")

    matching_recipes = [recipe for recipe in recipes if matches_available_tools(recipe)]
    recipe_pool = matching_recipes or recipes

    slot_pools: Dict[str, List[Dict[str, Any]]] = {}
    slot_queries: Dict[str, List[str]] = {
      "Breakfast": [
        f"breakfast {primary}",
        f"breakfast seasonal {primary}",
        "creative breakfast",
        primary,
        "",
      ],
      "Lunch": [
        f"lunch {primary}",
        "vibrant lunch ideas",
        f"{primary} bowls",
        primary,
        "",
      ],
      "Dinner": [
        f"dinner {primary}",
        "chef inspired dinner",
        f"weeknight {primary}",
        primary,
        "",
      ],
    }

    def resolve_slot_pool(slot: str) -> List[Dict[str, Any]]:
      for query in slot_queries.get(slot, [primary, ""]):
        pool = [recipe for recipe in get_recipes_for_query(query) if matches_available_tools(recipe)]
        if pool:
          return pool
      return recipe_pool

    for slot in self.MEAL_SLOTS:
      slot_pools[slot] = resolve_slot_pool(slot)

    used_recipe_ids: set[str] = set()

    def pick_unique_recipe(
      slot: str,
      pool: List[Dict[str, Any]],
      day_index: int,
      slot_index: int,
    ) -> Dict[str, Any]:
      for recipe in pool:
        if recipe["id"] not in used_recipe_ids:
          used_recipe_ids.add(recipe["id"])
          return recipe
      for recipe in recipe_pool:
        if recipe["id"] not in used_recipe_ids:
          used_recipe_ids.add(recipe["id"])
          return recipe
      recipe = pool[(day_index * len(self.MEAL_SLOTS) + slot_index) % len(pool)]
      return recipe

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    plan: List[Dict[str, Any]] = []
    for day_index, day in enumerate(days):
      for slot_index, slot in enumerate(self.MEAL_SLOTS):
        pool = slot_pools.get(slot) or recipe_pool
        recipe = pick_unique_recipe(slot, pool, day_index, slot_index)
        tool_hint = pick_tool_hint(recipe)
        prep_minutes = recipe.get("prep_minutes")
        cook_minutes = recipe.get("cook_minutes")
        calories = recipe.get("calories_per_person")
        steps = recipe.get("steps") or [
          "Review recipe steps – data was missing, default instructions applied.",
        ]
        ingredients = recipe.get("ingredients") or []
        plan.append(
          {
            "day": day,
            "meal": slot,
            "recipe_id": recipe["id"],
            "title": recipe["title"],
            "summary": f"{slot}: {recipe['summary']} Tool focus: {tool_hint}.",
            "ingredients": ingredients,
            "steps": steps,
            "prep_minutes": prep_minutes,
            "cook_minutes": cook_minutes,
            "calories_per_person": calories,
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
