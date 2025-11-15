from __future__ import annotations

from typing import Any, Dict


def nutrition_analyze(text: str) -> Dict[str, Any]:
  """
  Provide a coarse nutritional analysis of a meal or short meal plan.

  This is a heuristic, non-authoritative estimate meant to give
  agents a rough sense of balance for experimentation.
  """

  lowered = text.lower()

  score = {
    "calories_estimate": 550,
    "protein_g": 25,
    "carbs_g": 55,
    "fat_g": 20,
    "fiber_g": 8,
    "labels": set(),  # type: ignore[var-annotated]
  }

  if any(k in lowered for k in ["salmon", "chicken", "tofu", "lentil", "beans"]):
    score["protein_g"] += 10
    score["labels"].add("high-protein")
  if any(k in lowered for k in ["fried", "butter", "cream", "cheese"]):
    score["fat_g"] += 8
    score["labels"].add("rich")
  if any(k in lowered for k in ["whole grain", "quinoa", "brown rice", "oats"]):
    score["fiber_g"] += 3
    score["labels"].add("whole-grain")
  if any(k in lowered for k in ["broccoli", "spinach", "kale", "carrot", "pepper"]):
    score["fiber_g"] += 2
    score["labels"].add("veg-forward")

  labels = sorted(score["labels"])
  del score["labels"]

  return {
    "summary": "Coarse, heuristic nutrition estimate – not medical advice.",
    "estimate": score,
    "labels": labels,
  }


TOOLS: Dict[str, Any] = {
  "nutrition.analyze": nutrition_analyze,
}

