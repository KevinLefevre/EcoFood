from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from ...clients.gemini import generate_text_async

logger = logging.getLogger(__name__)

async def carbon_estimate_meal(
    meal_title: str,
    ingredients: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Estimates the CO2 footprint (in grams) for a single meal per person.
    """
    
    ingredients_text = "\n".join(
        f"- {ing.get('quantity', '')} {ing.get('unit', '')} {ing.get('name', 'ingredient')}"
        for ing in ingredients
    )

    prompt = f"""
    You are an environmental impact expert. Estimate the carbon footprint (CO2e) for the following meal (PER PERSON).

    Meal: {meal_title}
    Ingredients (approximate for one serving):
    {ingredients_text}

    Task:
    1. Analyze the ingredients and cooking implications.
    2. Estimate the total CO2e in grams for one serving.
    3. Provide a brief reasoning (1 sentence).
    4. Rate the eco-impact (Low, Medium, High).

    Output JSON ONLY:
    {{
        "co2_grams": 1200,
        "rating": "Medium",
        "reasoning": "Beef has a high footprint, but portion is small."
    }}
    """

    try:
        # Use default/fast model
        response = await generate_text_async(prompt, task_type="default")
        text = response.get("text", "")
        
        # Extract JSON
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            json_str = text[start : end + 1]
            data = json.loads(json_str)
            return {
                "co2_grams": data.get("co2_grams"),
                "rating": data.get("rating"),
                "reasoning": data.get("reasoning"),
                "model": response.get("model"),
            }
        else:
            logger.error(f"Could not parse JSON from carbon estimate: {text}")
            return {"co2_grams": None, "rating": "Unknown", "reasoning": "Parse error"}

    except Exception as e:
        logger.error(f"Carbon estimation failed: {e}")
        return {"co2_grams": None, "rating": "Unknown", "reasoning": str(e)}

TOOLS: Dict[str, Any] = {
    "carbon.estimate-meal": carbon_estimate_meal,
}
