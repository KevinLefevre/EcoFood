from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import Recipe


def recipes_search(
  query: str,
  diet: Optional[str] = None,
  cuisine: Optional[str] = None,
  max_prep_minutes: Optional[int] = None,
  limit: int = 5,
) -> Dict[str, Any]:
  """
  Search for recipes matching a textual query and optional filters.

  This implementation uses a small, static catalogue so it is fully
  self-contained and deterministic for now. Later it can be wired to
  a real recipe API and/or the EcoFood database.
  """

  catalogue: List[Recipe] = [
    Recipe(
      id="salmon-bowl",
      title="Herb-Roasted Salmon Grain Bowl",
      summary="Roasted salmon over quinoa with crunchy vegetables and a citrus-herb dressing.",
      cuisine="Mediterranean",
      diet_tags=["high-protein", "omega-3", "gluten-free"],
      estimated_prep_minutes=35,
    ),
    Recipe(
      id="veg-bento",
      title="Rainbow Veggie Bento",
      summary="Colorful lunchbox with marinated tofu, rice, and crisp vegetables.",
      cuisine="Japanese-inspired",
      diet_tags=["vegetarian", "high-fiber"],
      estimated_prep_minutes=30,
    ),
    Recipe(
      id="oats-berries",
      title="Overnight Oats with Berries",
      summary="Creamy oats soaked overnight, topped with mixed berries and seeds.",
      cuisine="Global",
      diet_tags=["vegetarian", "quick", "breakfast"],
      estimated_prep_minutes=10,
    ),
    Recipe(
      id="veggie-chili",
      title="Smoky Three-Bean Chili",
      summary="Hearty bean chili with tomatoes, peppers, and warm spices.",
      cuisine="Tex-Mex",
      diet_tags=["vegan", "high-fiber", "batch-cooking"],
      estimated_prep_minutes=45,
    ),
  ]

  q = query.lower().strip()
  diet_filter = diet.lower().strip() if diet else None
  cuisine_filter = cuisine.lower().strip() if cuisine else None

  def matches(recipe: Recipe) -> bool:
    text_blob = " ".join(
      [
        recipe.title.lower(),
        recipe.summary.lower(),
        recipe.cuisine.lower(),
        " ".join(tag.lower() for tag in recipe.diet_tags),
      ]
    )
    if q and q not in text_blob:
      return False
    if diet_filter and not any(diet_filter in tag.lower() for tag in recipe.diet_tags):
      return False
    if cuisine_filter and cuisine_filter not in recipe.cuisine.lower():
      return False
    if max_prep_minutes is not None and recipe.estimated_prep_minutes > max_prep_minutes:
      return False
    return True

  results = [r.to_dict() for r in catalogue if matches(r)]
  return {"recipes": results[: max(limit, 1)]}


TOOLS: Dict[str, Any] = {
  "recipes.search": recipes_search,
}

