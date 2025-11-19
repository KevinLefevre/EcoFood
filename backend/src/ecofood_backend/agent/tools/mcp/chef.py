from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from ...clients.gemini import GeminiClientError, generate_text

CULINARY_THEMES = [
  "Garden-to-table",
  "Fire-roasted",
  "Umami-forward",
  "Market brunch",
  "Wellness tonic",
  "Weeknight bistro",
  "Sunset mezze",
  "Chef's tasting",
]

TECHNIQUES = [
  "charred then glazed",
  "slow-poached",
  "fermented garnish",
  "crispy shallot crumble",
  "citrus-cured finish",
  "smoked spice dusting",
  "herb-infused oil drizzle",
  "pickled accent",
]

PAIRINGS = [
  "sparkling yuzu water",
  "cold brew hibiscus tea",
  "cucumber-mint spritz",
  "ginger & lime kefir",
  "charred lemon seltzer",
  "roasted barley iced tea",
  "cacao nib cold brew",
  "citrus hop tonic",
]

TEXTURE_NOTES = [
  "contrast velvety purées with crisp toppings",
  "balance acidity with a touch of honey",
  "layer smoky elements against something bright",
  "fold in toasted seeds for crunch",
  "build a chilled-warm temperature duet",
  "finish with aromatic herbs right before serving",
]

DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MEAL_SLOTS = ["Breakfast", "Lunch", "Dinner"]


def chef_build_menu(
  plan: List[Dict[str, Any]],
  profile: Optional[Dict[str, Any]] = None,
  notes: Optional[str] = None,
) -> Dict[str, Any]:
  """
  Give the base plan a chef-driven treatment: name tweaks, plating ideas,
  pairings, and textural prompts.
  """

  favorites = []
  if profile:
    favorites = [like["name"] for like in profile.get("top_likes", []) if isinstance(like, dict)]

  curated_plan: List[Dict[str, Any]] = []
  story_snippets: List[str] = []
  used_titles: set[str] = set()

  for index, item in enumerate(plan):
    base_title = item.get("title") or f"{item.get('meal', 'Meal')} idea"
    theme = CULINARY_THEMES[index % len(CULINARY_THEMES)]
    technique = TECHNIQUES[index % len(TECHNIQUES)]
    pairing = PAIRINGS[index % len(PAIRINGS)]
    texture = TEXTURE_NOTES[index % len(TEXTURE_NOTES)]

    if favorites:
      inspo = favorites[index % len(favorites)]
      theme_label = f"{theme} · inspired by {inspo.title()}"
    else:
      theme_label = theme

    composed_title = base_title
    if theme.split()[0] not in base_title:
      composed_title = f"{theme.split()[0]} {base_title}"
    if composed_title in used_titles:
      composed_title = f"{composed_title} ({item.get('meal', 'Chef')})"
    used_titles.add(composed_title)

    summary = item.get("summary") or ""
    chef_summary = f"{summary} Finish {technique}, {texture}. Pair with {pairing}."

    curated_plan.append(
      {
        **item,
        "title": composed_title,
        "summary": chef_summary.strip(),
        "chef_theme": theme_label,
        "chef_pairing": pairing,
        "chef_technique": technique,
      }
    )
    story_snippets.append(f"{item.get('day', 'Day')} {item.get('meal', 'Meal')}: {theme_label}")

  menu_story = "; ".join(story_snippets)
  if notes:
    menu_story = f"{menu_story}. Guest notes: {notes.strip()}."

  return {
    "plan": curated_plan,
    "themes": story_snippets,
    "menu_story": menu_story,
  }


def chef_plan_week(
  profile: Dict[str, Any],
  notes: Optional[str] = None,
  eco_friendly: bool = False,
  kitchen_tools: Optional[List[Dict[str, Any]]] = None,
  days: Optional[List[str]] = None,
) -> Dict[str, Any]:
  """
  Use Gemini to generate a 7-day (3 meals per day) plan with structured recipes.
  """

  likes = ", ".join(like["name"] for like in profile.get("top_likes", []) if like.get("name"))
  allergens = ", ".join(allergen["name"] for allergen in profile.get("allergens", []) if allergen.get("name"))
  tool_labels = ", ".join(
    tool["label"] for tool in (kitchen_tools or []) if tool.get("label") and tool.get("quantity", 0)
  )

  directives = [
    "Avoid repeating the same primary dish twice in the week.",
    "Use varied cuisines and textures to keep meals interesting.",
  ]
  if likes:
    directives.append(f"Lean into household favorites: {likes}.")
  if eco_friendly:
    directives.append("Prioritize plant-forward or low-impact proteins.")
  if allergens:
    directives.append(f"Never include allergens: {allergens}.")
  if tool_labels:
    directives.append(f"Prefer cookware available: {tool_labels}.")
  if notes:
    directives.append(f"Additional notes from the household: {notes.strip()}.")

  target_days = days or DAY_LABELS
  day_clause = ", ".join(target_days)

  prompt = f"""
You are EcoFood's executive chef. Design menus for these days: {day_clause}.
Each listed day must include BREAKFAST, LUNCH, and DINNER. You must output STRICT JSON following
this schema:
{{
  "plan": [
    {{
      "day": "Mon",
      "meal": "Breakfast",
      "title": "...",
      "summary": "...",
      "ingredients": [{{"name": "...", "quantity": "...", "unit": "...", "notes": "..."}}],
      "steps": ["...", "..."],
      "prep_minutes": 0,
      "cook_minutes": 0,
      "calories_per_person": 0,
      "required_tools": ["pan", "oven"]
    }}
  ]
}}

Constraints:
- Exactly {len(target_days) * 3} meals (3 meals per listed day) sorted by day then meal (Breakfast/Lunch/Dinner).
- Avoid dish repetition within the week.
- Include at least one adventurous or unexpected element each day.
- Keep instructions concise but descriptive enough to cook.
- Honor dietary notes and tool availability if provided.

Directives:
{chr(10).join(f"- {directive}" for directive in directives)}

Return only JSON. No commentary.
""".strip()

  try:
    response = generate_text(prompt)
  except GeminiClientError as exc:
    raise RuntimeError(f"Gemini menu generation failed: {exc}") from exc

  raw_text = response["text"]
  plan_data = _extract_plan_from_text(raw_text)
  normalized_plan = _normalize_plan(plan_data, target_days)

  return {
    "plan": normalized_plan,
    "model": response.get("model", "gemini"),
    "prompt": prompt,
    "raw_text": raw_text,
  }


def _extract_plan_from_text(text: str) -> List[Dict[str, Any]]:
  json_match = re.search(r"\{[\s\S]*\}", text)
  if not json_match:
    raise RuntimeError("Gemini response did not contain JSON.")
  try:
    parsed = json.loads(json_match.group(0))
  except json.JSONDecodeError as exc:
    raise RuntimeError("Unable to parse Gemini JSON.") from exc
  plan = parsed.get("plan")
  if not isinstance(plan, list):
    raise RuntimeError("Gemini JSON missing 'plan' list.")
  return plan


def _normalize_plan(plan: List[Dict[str, Any]], target_days: List[str]) -> List[Dict[str, Any]]:
  normalized: List[Dict[str, Any]] = []
  day_map = {
    "monday": "Mon",
    "tuesday": "Tue",
    "wednesday": "Wed",
    "thursday": "Thu",
    "friday": "Fri",
    "saturday": "Sat",
    "sunday": "Sun",
  }
  allowed_days = {day_map.get(day.strip().lower(), day[:3].title()) for day in target_days}

  for index, entry in enumerate(plan):
    day_value = entry.get("day") or DAY_LABELS[index // len(MEAL_SLOTS) % len(DAY_LABELS)]
    day_key = day_value.strip().lower()[:3]
    day = day_map.get(day_value.strip().lower(), day_map.get(day_key, DAY_LABELS[index // len(MEAL_SLOTS) % len(DAY_LABELS)]))
    if allowed_days and day not in allowed_days:
      continue
    meal_value = entry.get("meal") or MEAL_SLOTS[index % len(MEAL_SLOTS)]
    meal = meal_value.capitalize()
    if meal not in MEAL_SLOTS:
      meal = MEAL_SLOTS[index % len(MEAL_SLOTS)]

    ingredients_raw = entry.get("ingredients") or []
    ingredients: List[Dict[str, Any]] = []
    for ingredient in ingredients_raw:
      if isinstance(ingredient, dict):
        ingredients.append(
          {
            "name": ingredient.get("name") or "Ingredient",
            "quantity": ingredient.get("quantity"),
            "unit": ingredient.get("unit"),
            "notes": ingredient.get("notes"),
          }
        )
      elif isinstance(ingredient, str):
        ingredients.append({"name": ingredient})

    steps_raw = entry.get("steps") or []
    steps = [str(step).strip() for step in steps_raw if str(step).strip()]

    normalized.append(
      {
        "day": day,
        "meal": meal,
        "title": entry.get("title") or f"{meal} inspiration",
        "summary": entry.get("summary") or "Chef-inspired idea.",
        "ingredients": ingredients,
        "steps": steps or ["Gather ingredients and cook to taste."],
        "prep_minutes": _safe_int(entry.get("prep_minutes"), default=10),
        "cook_minutes": _safe_int(entry.get("cook_minutes"), default=15),
        "calories_per_person": _safe_int(entry.get("calories_per_person"), default=450),
        "required_tools": entry.get("required_tools") or [],
      }
    )
  return normalized


def _safe_int(value: Any, default: int) -> int:
  try:
    return int(value)
  except (TypeError, ValueError):
    return default


TOOLS: Dict[str, Any] = {
  "chef.build-menu": chef_build_menu,
  "chef.plan-week": chef_plan_week,
}
