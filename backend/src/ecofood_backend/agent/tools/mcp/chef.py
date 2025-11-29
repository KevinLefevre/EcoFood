from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

from ...clients.gemini import GeminiClientError, generate_text_async

logger = logging.getLogger(__name__)

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
    "model": "rule-based",  # chef_build_menu is deterministic
  }


async def chef_plan_week(
  profile: Dict[str, Any],
  notes: Optional[str] = None,
  eco_friendly: bool = False,
  kitchen_tools: Optional[List[Dict[str, Any]]] = None,
  days: Optional[List[str]] = None,
  calories_target: Optional[int] = None,
  leftover_notes: Optional[str] = None,
  mood: Optional[int] = None,
  pantry_items: Optional[List[Dict[str, Any]]] = None,
  debug_return: bool = False,
) -> Dict[str, Any]:
  """
  Use Gemini to generate per-slot meals across the week (one meal per call).
  Runs all day/meal slots in parallel.
  """

  likes = ", ".join(like["name"] for like in profile.get("top_likes", []) if like.get("name"))
  allergens = ", ".join(allergen["name"] for allergen in profile.get("allergens", []) if allergen.get("name"))
  tool_labels = ", ".join(
    tool["label"] for tool in (kitchen_tools or []) if tool.get("label") and tool.get("quantity", 0)
  )

  target_days = days or DAY_LABELS
  meal_prompts: Dict[str, str] = {}
  meal_raw: Dict[str, str] = {}
  meal_finish: Dict[str, Any] = {}
  errors: Dict[str, str] = {}
  combined_plan: List[Dict[str, Any]] = []

  def build_day_prompt(day: str) -> str:
    attendees_lines = []
    for member in profile.get("members", []):
      member_likes = []
      for like in member.get("likes", []):
        if isinstance(like, dict) and like.get("name"):
          member_likes.append(like["name"])
        elif isinstance(like, str):
          member_likes.append(like)
      member_allergens = []
      for allergen in member.get("allergens", []):
        if isinstance(allergen, dict) and allergen.get("name"):
          member_allergens.append(allergen["name"])
        elif isinstance(allergen, str):
          member_allergens.append(allergen)

      attendees_lines.append(
        f"{member.get('name','Guest')} ({member.get('role','')}) "
        f"likes={','.join(member_likes) if member_likes else 'none'} "
        f"allergens={','.join(member_allergens) if member_allergens else 'none'} "
        f"energy_level={member.get('energy','medium')}"
      )
    attendees_text = "\n- ".join(attendees_lines) if attendees_lines else "None listed"

    tools_available = [
      tool["label"] for tool in (kitchen_tools or []) if tool.get("label") and tool.get("quantity", 0)
    ]
    tools_list = tools_available or ["Standard kitchen basics"]

    example_one = """
{
  "plan": [
    {
      "day": "Mon",
      "meal": "Breakfast",
      "title": "Savory Oatmeal with Greens",
      "summary": "Hearty oats with sautéed greens and a poached egg.",
      "ingredients": [
        {"name": "Rolled oats", "quantity": "80", "unit": "g", "notes": null},
        {"name": "Spinach", "quantity": "60", "unit": "g", "notes": "washed"},
        {"name": "Egg", "quantity": "1", "unit": "pc", "notes": "poached"},
        {"name": "Olive oil", "quantity": "1", "unit": "tbsp", "notes": null}
      ],
      "steps": [
        "Simmer oats in water until creamy.",
        "Sauté spinach in olive oil until wilted.",
        "Poach the egg.",
        "Assemble oats, top with spinach and egg. Season to taste."
      ],
      "prep_minutes": 5,
      "cook_minutes": 10,
      "calories_per_person": 450,
      "required_tools": ["pot", "pan"]
    },
    {
      "day": "Mon",
      "meal": "Lunch",
      "title": "Chickpea & Roasted Pepper Grain Bowl",
      "summary": "Protein-rich bowl with roasted peppers, chickpeas, and herbed yogurt.",
      "ingredients": [
        {"name": "Cooked brown rice", "quantity": "200", "unit": "g", "notes": "warm"},
        {"name": "Chickpeas", "quantity": "240", "unit": "g can", "notes": "drained, rinsed"},
        {"name": "Red bell pepper", "quantity": "1", "unit": "pc", "notes": "sliced"},
        {"name": "Zucchini", "quantity": "1", "unit": "pc", "notes": "sliced"},
        {"name": "Olive oil", "quantity": "2", "unit": "tbsp", "notes": null},
        {"name": "Greek yogurt", "quantity": "120", "unit": "g", "notes": "or dairy-free yogurt"},
        {"name": "Lemon", "quantity": "0.5", "unit": "pc", "notes": "juiced"},
        {"name": "Mint", "quantity": "1", "unit": "tbsp", "notes": "chopped"},
        {"name": "Cumin", "quantity": "0.5", "unit": "tsp", "notes": null},
        {"name": "Salt", "quantity": null, "unit": null, "notes": "to taste"},
        {"name": "Black pepper", "quantity": null, "unit": null, "notes": "to taste"}
      ],
      "steps": [
        "Roast peppers and zucchini with olive oil, salt, pepper, and cumin at 200°C for 15-18 minutes.",
        "Warm chickpeas in a pan with a pinch of salt and pepper.",
        "Stir yogurt with lemon juice and mint to make a sauce.",
        "Assemble bowls with warm rice, roasted vegetables, chickpeas, and drizzle with the herbed yogurt."
      ],
      "prep_minutes": 10,
      "cook_minutes": 20,
      "calories_per_person": 520,
      "required_tools": ["oven", "sheet pan", "small pan", "mixing bowl"]
    },
    {
      "day": "Mon",
      "meal": "Dinner",
      "title": "Roasted Lemon-Herb Chicken & Vegetables",
      "summary": "Sheet-pan chicken with potatoes and carrots finished with a bright herb dressing.",
      "ingredients": [
        {"name": "Chicken thighs", "quantity": "500", "unit": "g", "notes": "bone-in, skin-on"},
        {"name": "Potatoes", "quantity": "400", "unit": "g", "notes": "cut into 2cm chunks"},
        {"name": "Carrots", "quantity": "200", "unit": "g", "notes": "sliced into batons"},
        {"name": "Olive oil", "quantity": "2", "unit": "tbsp", "notes": null},
        {"name": "Garlic", "quantity": "3", "unit": "cloves", "notes": "minced"},
        {"name": "Lemon", "quantity": "1", "unit": "pc", "notes": "zest and juice"},
        {"name": "Parsley", "quantity": "2", "unit": "tbsp", "notes": "chopped"},
        {"name": "Salt", "quantity": null, "unit": null, "notes": "to taste"},
        {"name": "Black pepper", "quantity": null, "unit": null, "notes": "to taste"}
      ],
      "steps": [
        "Preheat oven to 200°C. Line a sheet pan with parchment.",
        "Toss potatoes and carrots with half the olive oil, salt, and pepper. Spread on pan.",
        "Place chicken on top, drizzle remaining oil, and season with salt and pepper. Roast 30-35 minutes until chicken is 74°C and vegetables are tender.",
        "Combine lemon zest, juice, parsley, and minced garlic for a dressing. Spoon over chicken and vegetables before serving."
      ],
      "prep_minutes": 12,
      "cook_minutes": 35,
      "calories_per_person": 620,
      "required_tools": ["oven", "sheet pan", "mixing bowl"]
    }
  ]
}"""

    calorie_hint = calories_target
    member_cals = [m.get("calories_per_day") for m in profile.get("members", []) if m.get("calories_per_day")]
    if member_cals and not calories_target:
      try:
        calorie_hint = int(sum(member_cals) / len(member_cals))
      except Exception:
        calorie_hint = calories_target
    calorie_line = (
      f"Calorie target: aim for ~{calorie_hint} kcal/person (+/- 10%)" if calorie_hint else ""
    )

    leftovers_line = f"Leftover ingredients to include: {leftover_notes}" if leftover_notes else ""

    mood_line = ""
    if mood is not None:
      mood_line = (
        f"Week mood slider: {mood} "
        "(0 = indulgent/comfort, 50 = balanced, 100 = lean/light/high-veg, lower fat)."
      )

    return f"""
You are EcoFood's executive chef creating a personalized daily meal plan for {day}.

HOUSEHOLD CONTEXT:
Members: {', '.join(f"{m['name']} ({m['role']})" for m in profile.get('members', []))}
Allergens to AVOID: {allergens or 'None'}
Favorite cuisines/foods: {likes or 'Open to anything'}
Available cooking tools: {', '.join(tools_list)}
Attendees:
- {attendees_text}
{leftovers_line}
{f"Pantry items/Notes: {notes}" if notes else ''}
{f"Directive: Prioritize plant-forward/eco-friendly options." if eco_friendly else ''}
{calorie_line}
{mood_line}

TASK: Create 3 meals (Breakfast, Lunch, Dinner) for {day}:
- Must be safe for ALL household members (strictly avoid allergens)
- Use ONLY the available cooking tools listed above
- Incorporate household preferences naturally
- Fit the time/energy level appropriate for each slot
- Should be distinct from each other
- Summaries: concise, <=18 words, no quotes.
- Steps: 4–6 steps per meal, each 1 sentence, concise but complete (include timing/heat if relevant).

OUTPUT FORMAT (STRICT JSON MATCHING THE SCHEMA BELOW — DO NOT ADD EXTRA KEYS). "
Wrap the entire response in one fenced block: ```json ... ``` and nothing else:
{{
  "plan": [
    {{
      "day": "{day}",
      "meal": "Breakfast",
      "title": "Descriptive meal name",
      "summary": "Brief description highlighting key flavors and techniques",
      "ingredients": [
        {{"name": "ingredient", "quantity": "amount", "unit": "measurement", "notes": "optional prep notes"}}
      ],
      "steps": ["Detailed step 1", "Detailed step 2"],
      "prep_minutes": 15,
      "cook_minutes": 20,
      "calories_per_person": 500,
      "required_tools": ["only tools from available list"]
    }},
    {{
      "day": "{day}",
      "meal": "Lunch",
      ...
    }},
    {{
      "day": "{day}",
      "meal": "Dinner",
      ...
    }}
  ]
}}

IMPORTANT: 
- Return ONLY JSON. No prose, no markdown, no trailing commas.
- If constraints are impossible, still return a valid JSON with simple, safe ingredients.
- Double-check allergen safety
- Only suggest tools that are available
- Make it interesting but achievable
- Provide clear, complete cooking instructions

FEW-SHOT EXAMPLES (follow structure, return all three meals for the day):
{example_one}
""".strip()

  tasks = target_days
  
  # Rate limiting
  max_concurrent = int(os.getenv("GEMINI_MAX_CONCURRENT", "10"))
  semaphore = asyncio.Semaphore(max_concurrent)

  async def generate_with_limit(day: str) -> tuple[str, dict]:
    async with semaphore:
      prompt = build_day_prompt(day)
      key = day
      meal_prompts[key] = prompt
      try:
        # Use "meal_planning" task type for the complex model
        result = await generate_text_async(prompt, task_type="meal_planning")
        return key, result
      except Exception as exc:
        logger.error("Failed to generate %s: %s", key, exc)
        return key, exc

  # Execute all tasks
  results = await asyncio.gather(
    *[generate_with_limit(day) for day in tasks],
    return_exceptions=True,
  )

  for result in results:
    if isinstance(result, Exception):
      # Task-level failure (e.g., config/network)
      errors[f"task_error_{len(errors)+1}"] = str(result)
      continue  # Skip failed tasks
    if isinstance(result, tuple) and len(result) == 2:
      key, response = result
      if isinstance(response, Exception):
        errors[key] = str(response)
        continue
        
      meal_raw[key] = response.get("text", "")
      meal_finish[key] = response.get("finish_reason")
      try:
        plan_data = _extract_plan_from_text(response["text"])
        # key is the day string (e.g. "Mon")
        normalized = _normalize_plan(plan_data, target_days, calories_target=calories_target, day_context=key)
        combined_plan.extend(normalized)
      except Exception as exc:
        logger.error(
          "Failed to parse plan for %s: %s | finish=%s len=%s text=%s",
          key,
          exc,
          response.get("finish_reason"),
          len(response.get("text", "")),
          response.get("text", "")[:1200],
        )
        errors[key] = f"parse_error: {exc}"

  if not combined_plan:
    logger.error(
      "Gemini returned no usable meals. Raw snippets: %s | errors=%s",
      {k: v[:300] for k, v in meal_raw.items()},
      errors,
    )
    if debug_return:
      return {
        "plan": [],
        "model": "gemini-hybrid",
        "prompt_map": meal_prompts,
        "raw_text_map": meal_raw,
        "finish_reason_map": meal_finish,
        "error_map": errors,
      }
    raise RuntimeError("Gemini failed to generate any valid meals.")

  # Preserve original day order and meal order.
  day_order = {d: idx for idx, d in enumerate(target_days)}
  combined_plan.sort(
    key=lambda item: (
      day_order.get(item.get("day"), len(day_order)),
      MEAL_SLOTS.index(item.get("meal", MEAL_SLOTS[0])) if item.get("meal") in MEAL_SLOTS else 0,
    )
  )

  # Extract model name from the first successful response
  model_name = "gemini-hybrid"
  for result in results:
      if isinstance(result, tuple) and len(result) == 2:
          _, response = result
          if isinstance(response, dict) and response.get("model"):
              model_name = response.get("model")
              break

  combined_prompt = "\n\n".join(f"[{key}]\n{prompt}" for key, prompt in meal_prompts.items())
  combined_raw = "\n\n".join(f"[{key}]\n{text}" for key, text in meal_raw.items())

  return {
    "plan": combined_plan,
    "model": model_name,
    "prompt": combined_prompt,
    "raw_text": combined_raw,
    "prompt_map": meal_prompts,
    "raw_text_map": meal_raw,
    "finish_reason_map": meal_finish,
    "error_map": errors,
  }


def _extract_plan_from_text(text: str) -> List[Dict[str, Any]]:
  """
  Robustly extract JSON from model output, handling code fences and preambles.
  """
  # Prefer fenced blocks ```json ... ```
  code_block = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
  if code_block:
    return _parse_json_blob(code_block.group(1))

  cursor = 0
  while True:
    start_index = text.find("{", cursor)
    if start_index == -1:
      break
    end_index = text.rfind("}")
    if end_index == -1 or end_index < start_index:
      break
    candidate = text[start_index : end_index + 1]
    try:
      return _parse_json_blob(candidate)
    except Exception:
      cursor = start_index + 1
      continue

  logger.error("No JSON extracted from model output (len=%s). Preview: %s", len(text), text[:300])
  raise RuntimeError("Gemini response did not contain valid JSON.")


def _parse_json_blob(blob: str) -> List[Dict[str, Any]]:
  try:
    parsed = _loads_with_repair(blob)
  except Exception as exc:
    logger.warning("Primary JSON parse failed, attempting salvage: %s", exc)
    salvaged = _salvage_plan_objects(blob)
    if salvaged:
      return salvaged
    raise

  plan = parsed.get("plan") if isinstance(parsed, dict) else None
  # Salvage: some responses might be a raw list of meals already
  if plan is None and isinstance(parsed, list):
    plan = parsed
  if not isinstance(plan, list):
    raise RuntimeError("Gemini JSON missing 'plan' list.")
  return plan


def _salvage_plan_objects(blob: str) -> List[Dict[str, Any]]:
  """
  Last-resort parser: extract individual meal objects that include day/meal keys
  when the full JSON is truncated. Returns empty list if nothing can be salvaged.
  """
  meals: List[Dict[str, Any]] = []
  # First pass: fully closed objects.
  closed_obj = re.compile(r"\{[^{}]*\"day\"\s*:\s*\"[^\"']+\"[^{}]*\"meal\"\s*:\s*\"[^\"']+\"[^{}]*\}", re.DOTALL)
  for match in closed_obj.finditer(blob):
    candidate = match.group(0)
    try:
      parsed = _loads_with_repair(candidate)
      if isinstance(parsed, dict):
        meals.append(parsed)
    except Exception:
      continue
  if meals:
    return meals

  # Second pass: attempt to repair truncated segments from each \"day\": occurrence.
  anchors = [m.start() for m in re.finditer(r'"day"\s*:\s*"', blob)]
  anchors.append(len(blob))
  for i in range(len(anchors) - 1):
    segment = blob[anchors[i]:anchors[i + 1]]
    candidate = "{" + segment
    try:
      parsed = _loads_with_repair(candidate)
      if isinstance(parsed, dict) and parsed.get("day") and parsed.get("meal"):
        meals.append(parsed)
    except Exception:
      continue
  return meals


def _loads_with_repair(payload: str) -> Dict[str, Any]:
  try:
    return json.loads(payload)
  except json.JSONDecodeError as exc:
    repaired = _repair_json(payload)
    if repaired == payload:
      raise RuntimeError("Unable to parse Gemini JSON.") from exc
    try:
      parsed = json.loads(repaired)
      logger.warning("Repaired malformed Gemini JSON (error=%s)", exc)
      return parsed
    except json.JSONDecodeError as final_exc:
      raise RuntimeError("Unable to parse Gemini JSON after repair.") from final_exc


def _repair_json(payload: str) -> str:
  fixed = payload
  # Insert missing commas between adjacent objects/arrays.
  fixed = re.sub(r"}(\s*){", r"},\1{", fixed)
  fixed = re.sub(r"\](\s*){", r"],\1{", fixed)
  fixed = re.sub(r"}(\s*)\[", r"},\1[", fixed)
  # Insert missing colons between quoted keys and quoted/string values.
  fixed = re.sub(r'"([^"]+)"\s+"', r'"\1": "', fixed)
  fixed = re.sub(r'"([^"]+)"\s+(-?\d)', r'"\1": \2', fixed)
  # Remove dangling commas before closing braces/brackets.
  fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
  # Close an unterminated string if there is an odd number of quotes.
  if fixed.count('"') % 2 != 0:
    fixed = fixed + '"'
  # Balance brackets/braces if the model stopped early.
  brace_diff = fixed.count("{") - fixed.count("}")
  if brace_diff > 0:
    fixed = fixed + ("}" * brace_diff)
  bracket_diff = fixed.count("[") - fixed.count("]")
  if bracket_diff > 0:
    fixed = fixed + ("]" * bracket_diff)
  return fixed


def _normalize_plan(
  plan: List[Dict[str, Any]],
  target_days: List[str],
  *,
  calories_target: Optional[int] = None,
  day_context: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
    # If day_context is provided (from the prompt key), force it.
    # Otherwise try to read from entry, fallback to index-based is risky but kept as last resort.
    day_value = day_context or entry.get("day")
    if not day_value:
       # Fallback: try to infer from target_days if it's a single day request
       if len(target_days) == 1:
         day_value = target_days[0]
       else:
         day_value = DAY_LABELS[index // len(MEAL_SLOTS) % len(DAY_LABELS)]

    day_key = day_value.strip().lower()[:3]
    day = day_map.get(day_value.strip().lower(), day_map.get(day_key, day_value[:3].title()))
    
    if allowed_days and day not in allowed_days:
      # If we have a day_context, we should trust it and override the entry's day if it mismatches
      if day_context and day_context in allowed_days:
          day = day_context
      else:
          logger.warning("Skipping meal for day %s (allowed=%s)", day, allowed_days)
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
        "calories_per_person": _safe_int(entry.get("calories_per_person"), default=calories_target or 450),
        "required_tools": entry.get("required_tools") or [],
      }
    )
  return normalized


def _safe_int(value: Any, default: int) -> int:
  try:
    return int(value)
  except (TypeError, ValueError):
    return default



async def chef_chat_analysis(
    current_plan: Dict[str, Any],
    chat_history: List[Dict[str, str]],
    user_message: str,
    memories: Optional[List[str]] = None,
    summary: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyzes the chat conversation to determine if the agent has enough information
    to update the meal plan.
    """
    memories_text = ""
    if memories:
        memories_text = "Long-Term Memories (User Preferences/Facts):\n" + "\n".join(f"- {m}" for m in memories)
        
    summary_text = ""
    if summary:
        summary_text = f"Previous Conversation Summary:\n{summary}\n"

    prompt = f"""
    You are a helpful and creative chef assistant. You are helping a user modify a specific meal in their plan.

    Current Meal Context:
    {json.dumps(current_plan, indent=2)}

    {memories_text}
    
    {summary_text}

    Chat History:
    {json.dumps(chat_history, indent=2)}

    User's Latest Message: "{user_message}"

    Your Goal:
    1. Understand what the user wants to change about this meal.
    2. If the user's request is vague or you need more details (e.g., dietary restrictions, specific ingredients), ask clarifying questions.
    3. If the user's request is clear and you have enough information to generate a new recipe, confirm what you will do.
    4. Set "ready" to true ONLY if you have enough information to proceed with the update.

    Output Format:
    Return a JSON object with the following fields:
    - "message": Your response to the user (string). Be conversational and helpful.
    - "ready": true or false (boolean).
    - "summary": If ready, a brief summary of the changes you will make (string). If not ready, null.
    """

    try:
        # Use default task_type which uses the fast model (gemini-2.0-flash-exp)
        response_data = await generate_text_async(prompt, task_type="default")
        response_text = response_data["text"]
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            logger.error(f"Failed to parse JSON from chat analysis response: {response_text}")
            return {
                "message": "I'm having trouble understanding. Could you rephrase that?",
                "ready": False,
                "summary": None,
            }
    except Exception as e:
        logger.error(f"Error in chef_chat_analysis: {e}")
        return {
            "message": "Sorry, I encountered an error processing your request.",
            "ready": False,
            "summary": None,
        }


async def chef_execute_update(
    current_plan: Dict[str, Any],
    chat_history: List[Dict[str, str]],
    memories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generates the updated meal details based on the conversation context.
    """
    memories_text = ""
    if memories:
        memories_text = "Long-Term Memories (User Preferences/Facts):\n" + "\n".join(f"- {m}" for m in memories)

    prompt = f"""
    You are a professional chef. You need to update a meal plan entry based on the user's request.

    Original Meal:
    {json.dumps(current_plan, indent=2)}

    {memories_text}

    Conversation History:
    {json.dumps(chat_history, indent=2)}

    Task:
    Generate a fully detailed meal entry that reflects the user's requested changes.
    Keep the same structure as the original meal but update the content (title, summary, ingredients, steps, etc.).
    Ensure the new recipe is creative, delicious, and accurate.

    Output Format:
    Return a JSON object matching the structure of a meal plan entry:
    {{
        "title": "New Meal Title",
        "summary": "Description of the new meal...",
        "ingredients": [
            {{ "name": "Ingredient 1", "amount": "1 cup", "category": "produce" }},
            ...
        ],
        "steps": ["Step 1", "Step 2", ...],
        "prep_minutes": 30,
        "cook_minutes": 45,
        "calories_per_person": 600
    }}
    """

    try:
        # Use default task_type for now. 
        # Ideally we'd use a more capable model but "meal_planning" task type enforces a full plan schema.
        response_data = await generate_text_async(prompt, task_type="default")
        response_text = response_data["text"]
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        else:
            logger.error(f"Failed to parse JSON from execute update response: {response_text}")
            raise ValueError("Failed to generate valid JSON for meal update")
    except Exception as e:
        logger.error(f"Error in chef_execute_update: {e}")
        raise


TOOLS: Dict[str, Any] = {
  "chef.build-menu": chef_build_menu,
  "chef.plan-week": chef_plan_week,
  "chef.chat-analysis": chef_chat_analysis,
  "chef.execute-update": chef_execute_update,
}
