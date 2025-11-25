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

  aggregated: Dict[tuple, Dict[str, Any]] = {}

  for item in plan_items:
    for ing in item.get("ingredients", []):
      if isinstance(ing, str):
        # Legacy fallback
        name = ing.strip()
        key = (name.lower(), "")
        if key not in aggregated:
          aggregated[key] = {"name": name, "quantity": 0, "unit": "", "count": 0}
        aggregated[key]["count"] += 1
        continue
        
      name = (ing.get("name") or "Unknown").strip()
      unit = (ing.get("unit") or "").strip().lower()
      qty_val = ing.get("quantity")
      
      try:
        qty = float(qty_val) if qty_val is not None else 0.0
      except (ValueError, TypeError):
        qty = 0.0

      # Unit normalization and conversion
      # Convert volumes to ml, weights to g, others normalized
      if unit in ["g", "gram", "grams"]:
        unit = "g"
      elif unit in ["kg", "kilogram", "kilograms"]:
        qty *= 1000
        unit = "g"
      elif unit in ["ml", "milliliter", "milliliters"]:
        unit = "ml"
      elif unit in ["l", "liter", "liters"]:
        qty *= 1000
        unit = "ml"
      elif unit in ["tbsp", "tablespoon", "tablespoons"]:
        qty *= 15
        unit = "ml"
      elif unit in ["tsp", "teaspoon", "teaspoons"]:
        qty *= 5
        unit = "ml"
      elif unit in ["cup", "cups"]:
        qty *= 240
        unit = "ml"
      elif unit in ["pc", "pcs", "piece", "pieces"]:
        unit = "pc"
      elif unit in ["clove", "cloves"]:
        unit = "clove"
      elif unit in ["can", "cans"]:
        unit = "can"
      elif unit in ["slice", "slices"]:
        unit = "slice"
      elif unit in ["head", "heads"]:
        unit = "head"
      elif unit in ["pinch", "pinches"]:
        unit = "pinch"

      key = (name.lower(), unit)
      if key not in aggregated:
        aggregated[key] = {"name": name, "quantity": 0.0, "unit": unit, "count": 0}
      
      aggregated[key]["quantity"] += qty
      aggregated[key]["count"] += 1

  def classify(name: str) -> str:
    lowered = name.lower()
    if any(k in lowered for k in ["lettuce", "spinach", "kale", "carrot", "onion", "garlic", "pepper", "tomato", "cucumber", "broccoli", "potato", "zucchini", "mushroom", "avocado", "herb", "parsley", "cilantro", "basil", "dill"]):
      return "fresh_produce"
    if any(k in lowered for k in ["chicken", "beef", "pork", "salmon", "tofu", "tempeh", "egg", "fish", "tuna", "shrimp", "meat"]):
      return "protein"
    if any(k in lowered for k in ["rice", "quinoa", "pasta", "noodles", "bread", "tortilla", "oat", "flour", "couscous", "barley"]):
      return "grains"
    if any(k in lowered for k in ["milk", "yogurt", "cheese", "butter", "cream", "feta", "mozzarella", "parmesan"]):
      return "dairy"
    if any(k in lowered for k in ["oil", "vinegar", "soy sauce", "spice", "cumin", "paprika", "salt", "pepper", "sugar", "honey", "syrup", "sauce", "mayo", "mustard", "ketchup", "stock", "broth", "can"]):
      return "pantry_and_condiments"
    if any(k in lowered for k in ["apple", "banana", "berry", "orange", "grape", "lemon", "lime", "fruit"]):
      return "fruit"
    return "other"

  groups: Dict[str, List[str]] = {}
  
  for data in aggregated.values():
    name = data["name"]
    qty = data["quantity"]
    unit = data["unit"]
    count = data["count"]
    
    # Format output
    if qty > 0:
      # Round to reasonable decimals
      qty_display = f"{qty:.1f}".rstrip("0").rstrip(".")
      display_str = f"{qty_display} {unit} {name}"
    else:
      # If no quantity, maybe just show count if > 1, or just name
      if count > 1:
        display_str = f"{count}x {name}"
      else:
        display_str = name
        
    category = classify(name)
    groups.setdefault(category, []).append(display_str)

  for cat in groups:
    groups[cat].sort()

  all_items = sorted({item for sublist in groups.values() for item in sublist})

  return {"groups": groups, "all": all_items}


TOOLS: Dict[str, Any] = {
  "shopping-list.generate": shopping_list_generate,
}

