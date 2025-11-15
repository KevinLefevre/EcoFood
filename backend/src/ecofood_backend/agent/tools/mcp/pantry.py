from __future__ import annotations

from typing import Any, Dict, List

from .models import PantryItemUsage


def pantry_suggest_usage(items: List[Dict[str, Any]]) -> Dict[str, Any]:
  """
  Given a list of soon-to-expire items, suggest 2–3 meals that use them.

  Expected item shape:
  {
    "name": str,
    "quantity": float | None,
    "unit": str | None,
    "days_until_expiry": int | None
  }

  The suggestions are heuristic and template based for now.
  """

  parsed_items: List[PantryItemUsage] = []
  for raw in items:
    parsed_items.append(
      PantryItemUsage(
        name=str(raw.get("name", "")).strip(),
        quantity=raw.get("quantity"),
        unit=raw.get("unit"),
        days_until_expiry=raw.get("days_until_expiry"),
      )
    )

  focus_items = [i for i in parsed_items if i.name]
  focus_items.sort(key=lambda i: (i.days_until_expiry or 9999, i.name))

  names = [i.name for i in focus_items]

  if not names:
    return {"suggestions": [], "note": "No valid items provided."}

  primary = names[:3]
  extra = names[3:6]

  def join_list(values: List[str]) -> str:
    if not values:
      return ""
    if len(values) == 1:
      return values[0]
    return ", ".join(values[:-1]) + f" and {values[-1]}"

  suggestions = []

  # Suggestion 1 – one-pan or sheet-pan meal
  suggestions.append(
    {
      "title": f"Sheet-pan dinner with {primary[0]}",
      "description": (
        f"Roast {primary[0]} together with {join_list(primary[1:]) or 'mixed vegetables'} "
        "on a single tray. Add olive oil, herbs, and a starch (e.g. potatoes or grains) "
        "to build a complete, low-effort dinner."
      ),
      "uses": primary,
      "style": "one-pan",
    }
  )

  # Suggestion 2 – soup, stew, or curry style
  if len(primary) >= 2:
    suggestions.append(
      {
        "title": f"Comfort stew using {join_list(primary[:2])}",
        "description": (
          f"Combine {join_list(primary[:2])} in a pot with onions, garlic, and stock. "
          "Simmer into a stew or curry. Serve over rice or with crusty bread."
        ),
        "uses": primary[:2] + extra,
        "style": "stew",
      }
    )

  # Suggestion 3 – bowl / salad / grain bowl
  suggestions.append(
    {
      "title": f"Next-day lunch bowls featuring {primary[0]}",
      "description": (
        f"Turn leftover {join_list(primary)} into cold or warm grain bowls. "
        "Pair with greens, a grain (rice, quinoa, bulgur), and a simple dressing "
        "to get an easy, balanced lunch."
      ),
      "uses": primary + extra,
      "style": "bowl",
    }
  )

  return {"suggestions": suggestions}


TOOLS: Dict[str, Any] = {
  "pantry.suggest-usage": pantry_suggest_usage,
}

