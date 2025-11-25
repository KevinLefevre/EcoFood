#!/usr/bin/env python
"""
Quick CLI to exercise the meal planner without Docker.

Usage:
  python backend/scripts/meal_planner_test.py --days Mon Tue --calories 600 --mood 40
  python backend/scripts/meal_planner_test.py --profile my_profile.json
Running with another LLM provider:
- Set GEMINI_API_KEY (and optionally override GEMINI_COMPLEX_TASK_MODEL / GEMINI_FAST_TASK_MODEL).
- Ensure the venv is active: `source backend/.venv/bin/activate`
- Run with PYTHONPATH pointing to backend/src:
    PYTHONPATH=backend/src GEMINI_API_KEY=... python backend/scripts/meal_planner_test.py

The script:
  - Optionally loads a profile JSON from disk (see SAMPLE_PROFILE shape below).
  - Falls back to a small sample profile if none is provided.
  - Calls chef_plan_week (Gemini) for the requested days.
  - Prints a concise summary of the generated plan.

Requires GEMINI_API_KEY (and related Gemini env vars) to be set in your shell or .env.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
  from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover
  def load_dotenv():
    return None

from ecofood_backend.agent.tools.mcp.chef import chef_plan_week
from ecofood_backend.agent.tools.mcp.shopping import shopping_list_generate


SAMPLE_PROFILE: Dict[str, Any] = {
  "members": [
    {
      "name": "Alex",
      "role": "adult",
      "likes": [{"name": "Mediterranean"}, {"name": "chicken"}],
      "allergens": [{"name": "peanut"}],
      "energy": "medium",
      "calories_per_day": 2200,
    },
    {
      "name": "Jamie",
      "role": "adult",
      "likes": [{"name": "vegetarian"}, {"name": "pasta"}],
      "allergens": [],
      "energy": "low",
      "calories_per_day": 1900,
    },
  ],
  "top_likes": [{"name": "garlic"}, {"name": "herbs"}],
  "allergens": [{"name": "peanut"}],
}

SAMPLE_TOOLS: List[Dict[str, Any]] = [
  {"label": "oven", "quantity": 1},
  {"label": "stovetop", "quantity": 1},
  {"label": "pan", "quantity": 2},
  {"label": "pot", "quantity": 1},
  {"label": "sheet pan", "quantity": 1},
]


def load_profile(path: Optional[str]) -> Dict[str, Any]:
  if not path:
    return SAMPLE_PROFILE
  p = Path(path)
  with p.open("r", encoding="utf-8") as fh:
    return json.load(fh)


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="Run meal planner locally without Docker.")
  parser.add_argument("--profile", type=str, help="Path to JSON profile file.")
  parser.add_argument("--days", nargs="*", default=["Mon"], help="Subset of days to generate (default: Mon).")
  parser.add_argument("--calories", type=int, help="Calories target per person (approx).")
  parser.add_argument("--mood", type=int, help="Mood slider 0=comfy/indulgent, 100=healthy/light.")
  parser.add_argument("--eco", action="store_true", help="Prioritize eco-friendly options.")
  parser.add_argument("--leftovers", type=str, default=None, help="Notes about leftovers to include.")
  parser.add_argument(
    "--pantry",
    type=str,
    default=None,
    help="Comma-separated pantry items (for first-day lunch prioritization).",
  )
  return parser.parse_args()


def summarize(plan: List[Dict[str, Any]]) -> None:
  for meal in plan:
    day = meal.get("day")
    slot = meal.get("meal")
    title = meal.get("title")
    kcal = meal.get("calories_per_person")
    prep = meal.get("prep_minutes")
    cook = meal.get("cook_minutes")
    
    print(f"\n=== {day} {slot}: {title} ===")
    print(f"  Calories: {kcal} kcal/person | Prep: {prep}m | Cook: {cook}m")
    
    print("\n  Ingredients:")
    for ing in meal.get("ingredients", []):
      # Handle both string and dict ingredients (just in case)
      if isinstance(ing, dict):
        name = ing.get("name")
        qty = ing.get("quantity", "")
        unit = ing.get("unit", "")
        print(f"    - {qty} {unit} {name}".strip())
      else:
        print(f"    - {ing}")

    print("\n  Steps:")
    for i, step in enumerate(meal.get("steps", []), 1):
      print(f"    {i}. {step}")
    print("-" * 40)


async def main() -> None:
  load_dotenv()
  args = parse_args()
  profile = load_profile(args.profile)
  days = args.days if args.days else None
  pantry = []
  if args.pantry:
    pantry = [{"name": item.strip()} for item in args.pantry.split(",") if item.strip()]
  else:
    # Default pantry to exercise the code path
    pantry = [{"name": "Olive oil"}, {"name": "Salt"}, {"name": "Pepper"}]

  result = await chef_plan_week(
    profile=profile,
    notes=None,
    eco_friendly=bool(args.eco),
    kitchen_tools=SAMPLE_TOOLS,
    days=days,
    calories_target=args.calories,
    leftover_notes=args.leftovers,
    mood=args.mood,
    debug_return=True,
    pantry_items=pantry,
  )
  plan = result.get("plan", [])
  print("\nGenerated meals:")
  summarize(plan)
  
  print("\n=== Shopping List ===")
  # Adapt plan structure for shopping tool if needed, but it should handle it
  shopping = shopping_list_generate(plan)
  for category, items in shopping.get("groups", {}).items():
    print(f"\n[{category.replace('_', ' ').title()}]")
    for item in items:
      print(f"  - {item}")
  print("-" * 40)
  # Debug info for failures/truncation
  raw_map = result.get("raw_text_map", {})
  finish_map = result.get("finish_reason_map", {})
  error_map = result.get("error_map", {})
  if not plan or error_map:
    print("\n--- Debug info ---")
    print("Finish reasons:", finish_map)
    print("Errors:", error_map)
    for k, v in raw_map.items():
      print(f"[{k}] len={len(v)} snippet={v[:200]!r}")


if __name__ == "__main__":
  asyncio.run(main())
