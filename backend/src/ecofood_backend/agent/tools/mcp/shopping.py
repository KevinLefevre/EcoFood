from __future__ import annotations

from typing import Any, Dict, List


def shopping_list_generate(plan_items: List[Dict[str, Any]]) -> Dict[str, Any]:
  """
  Generate a consolidated shopping list from plan items.

  Expected plan item shape:
  {
    "name": str,  # meal name
    "ingredients": [str]  # free-text ingredient lines
  }
  """

  raw_ingredients: List[str] = []
  for item in plan_items:
    for ing in item.get("ingredients", []):
      text = str(ing).strip()
      if text:
        raw_ingredients.append(text)

  if not raw_ingredients:
    return {"groups": {}, "all": []}

  def classify(ingredient: str) -> str:
    lowered = ingredient.lower()
    if any(k in lowered for k in ["lettuce", "spinach", "kale", "carrot", "onion", "garlic", "pepper", "tomato", "cucumber", "broccoli"]):
      return "fresh_produce"
    if any(k in lowered for k in ["chicken", "beef", "pork", "salmon", "tofu", "tempeh", "egg"]):
      return "protein"
    if any(k in lowered for k in ["rice", "quinoa", "pasta", "noodles", "bread", "tortilla"]):
      return "grains"
    if any(k in lowered for k in ["milk", "yogurt", "cheese", "butter"]):
      return "dairy"
    if any(k in lowered for k in ["olive oil", "oil", "vinegar", "soy sauce", "spice", "cumin", "paprika", "salt"]):
      return "pantry_and_condiments"
    if any(k in lowered for k in ["apple", "banana", "berry", "orange", "grape"]):
      return "fruit"
    return "other"

  groups: Dict[str, List[str]] = {}

  for ing in raw_ingredients:
    category = classify(ing)
    groups.setdefault(category, []).append(ing)

  for cat in groups:
    unique_sorted = sorted({v for v in groups[cat]})
    groups[cat] = unique_sorted

  all_items = sorted({v for values in groups.values() for v in values})

  return {"groups": groups, "all": all_items}


TOOLS: Dict[str, Any] = {
  "shopping-list.generate": shopping_list_generate,
}

