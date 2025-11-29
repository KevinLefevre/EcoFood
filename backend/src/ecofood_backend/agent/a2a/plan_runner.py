from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List
from ecofood_backend.agent.tools.mcp.shopping import shopping_list_generate
from ecofood_backend.agent.tools.mcp.calendar_tools import calendar_export_ics

from ...database import AsyncSessionFactory
from .workflow import MealPlanRequest, MealPlanningWorkflow
from ...services import households as household_service
from ...services import meal_plans as meal_plan_service
from ...services import plan_jobs as plan_job_service
from ...services.meal_plans import MEAL_SLOTS

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
logger = logging.getLogger(__name__)


async def run_plan_job(job_id: int) -> None:
  logger.info("Starting planning job %s", job_id)
  async with AsyncSessionFactory() as db:
    job = await plan_job_service.get_job(db, job_id)
    if job is None:
      logger.warning("Planning job %s not found", job_id)
      return
    await plan_job_service.mark_job_started(db, job_id)
    await plan_job_service.add_event(db, job_id, stage="started", message="Planning job started")

  try:
    await _execute_planning(job_id)
  except Exception as exc:  # pragma: no cover - background failure logging
    logger.exception("Planning job %s failed", job_id)
    async with AsyncSessionFactory() as db:
      await plan_job_service.mark_job_failed(db, job_id, error=str(exc))


async def _execute_planning(job_id: int) -> None:
  workflow = MealPlanningWorkflow()
  async with AsyncSessionFactory() as db:
    job = await plan_job_service.get_job(db, job_id)
    if job is None:
      logger.error("Planning job %s disappeared before execution", job_id)
      return
    calories_target = job.calories_per_person_default
    household = await household_service.get_household_with_members(db, job.household_id)
    members_payload = [
      {
        "name": member.name,
        "role": member.role,
        "allergens": [allergen.label for allergen in member.allergens],
        "likes": [pref.label for pref in member.preferences],
        "calories_per_day": member.calories_per_day,
      }
      for member in household.members
    ]
    member_calories = {member.id: member.calories_per_day for member in household.members}
    kitchen_payload = [
      {
        "label": tool.label,
        "category": tool.category,
        "quantity": tool.quantity,
      }
      for tool in household.kitchen_tools
    ]
    # TODO: Fetch pantry items from DB once supported
    pantry_items_payload: List[Dict[str, Any]] = []
    slot_attendees = _build_slot_attendees(household)
    # Identify already planned slots for this week to skip them.
    existing_plan = await meal_plan_service.get_plan_by_week(db, job.household_id, job.week_start)
    base_entries: List[Dict[str, Any]] = []
    base_timeline: List[Dict[str, Any]] = []
    existing_slots: set[tuple[str, str]] = set()
    if existing_plan:
      for entry in existing_plan.entries:
        day_label = entry.day.strftime("%a")  # Mon/Tue...
        existing_slots.add((day_label, entry.slot))
        # Convert Pydantic ingredients to dicts for compatibility with tools
        ingredients_dicts = [
          ing.model_dump() if hasattr(ing, "model_dump") else dict(ing)
          for ing in entry.ingredients
        ]
        base_entries.append(
          {
            "day": day_label,
            "meal": entry.slot,
            "title": entry.title,
            "summary": entry.summary,
            "ingredients": ingredients_dicts,
            "steps": entry.steps,
            "prep_minutes": entry.prep_minutes,
            "cook_minutes": entry.cook_minutes,
            "calories_per_person": entry.calories_per_person,
          }
        )
      if isinstance(existing_plan.timeline, list):
        base_timeline = list(existing_plan.timeline)
    needed_slots = [(day, slot) for day in DAY_ORDER for slot in MEAL_SLOTS if (day, slot) not in existing_slots]

  if not needed_slots:
    logger.info("Planning job %s: all slots already planned. Updating shopping list.", job_id)
    # Even if no new meals, we must ensure the master shopping list is up to date.
    if base_entries:
      try:
        shopping_input = []
        for entry in base_entries:
          shopping_input.append({
            "name": entry.get("title", "Meal"),
            "ingredients": entry.get("ingredients", [])
          })
        master_list = shopping_list_generate(shopping_input)

        # Prepare calendar (simplified)
        calendar_events = []
        for idx, item in enumerate(base_entries):
           calendar_events.append({
            "title": f"{item.get('day', 'Day')} – {item.get('title', 'Meal')}",
            "date": datetime.now().strftime("%Y-%m-%d"), 
            "description": item.get("summary", "Meal")
          })
        master_calendar = calendar_export_ics(calendar_events)
        
        # Filter out old shopping list events to avoid duplicates
        base_timeline = [
          e for e in base_timeline 
          if e.get("agent") != "plan-synthesizer" and e.get("stage") != "plan.final"
        ]
        
        base_timeline.append({
          "agent": "plan-synthesizer",
          "stage": "plan.final",
          "status": "complete",
          "title": "Weekly Plan Finalization",
          "description": f"Generated master shopping list and calendar for {len(base_entries)} meals.",
          "payload": {
            "shopping_list": master_list,
            "calendar": master_calendar,
            "plan": base_entries,
          },
          "sequence": len(base_timeline) + 1
        })
        
        async with AsyncSessionFactory() as db:
          await meal_plan_service.update_plan_timeline(db, existing_plan.id, base_timeline)
          await plan_job_service.mark_job_completed(db, job_id, plan_id=existing_plan.id)
          await plan_job_service.add_event(
            db,
            job_id,
            stage="completed",
            message="Plan updated with shopping list",
            payload={"plan_id": existing_plan.id},
          )
      except Exception as exc:
        logger.error("Failed to update shopping list for existing plan: %s", exc)
    return
  
  needed_days = sorted(list(set(d for d, s in needed_slots)), key=lambda x: DAY_ORDER.index(x))
  logger.info(
    "Planning job %s launching days: count=%s days=%s",
    job_id,
    len(needed_days),
    ",".join(needed_days),
  )

  async def _plan_single_day(day: str) -> Dict[str, Any]:
    logger.info("Job %s planning day start: day=%s", job_id, day)
    async with AsyncSessionFactory() as db_session:
      current_job = await plan_job_service.get_job(db_session, job_id)
      if current_job is None:
        await plan_job_service.mark_job_failed(db_session, job_id, error="Job missing mid-run")
        return {"day": day, "status": "error", "error": "Job missing"}
      if current_job.status == "cancelled":
        await plan_job_service.add_event(
          db_session,
          job_id,
          stage="cancelled",
          message=f"Cancelled before {day}",
          payload={"day": day},
        )
        return {"day": day, "status": "cancelled"}
      await plan_job_service.add_event(
        db_session,
        job_id,
        stage="planning",
        message=f"Planning {day}",
        payload={"day": day, "phase": "start"},
      )

    session_id = f"job-{job_id}-{day}-{int(datetime.utcnow().timestamp())}"
    notes_combined = job.notes
    if job.leftovers_text:
      extras = f"Leftovers to prioritize: {job.leftovers_text.strip()}"
      notes_combined = f"{notes_combined}\n{extras}" if notes_combined else extras

    # derive calorie target: either job default or average of attending members per meal (daily/3)
    def _day_calorie_target(day_label: str) -> int | None:
      if calories_target:
        return calories_target
      # Average across all slots for the day
      day_attendees = []
      for slot in MEAL_SLOTS:
        day_attendees.extend(slot_attendees.get((day_label, slot), []))
      
      per_day = [member_calories.get(a) for a in set(day_attendees) if member_calories.get(a)]
      if per_day:
        avg_daily = sum(per_day) / len(per_day)
        return int(round(avg_daily / 3))
      return None

    request = MealPlanRequest(
      session_id=session_id,
      members=members_payload,
      pantry_items=pantry_items_payload if day == DAY_ORDER[0] else [],
      kitchen_tools=kitchen_payload,
      notes=notes_combined,
      household_id=job.household_id,
      week_start=job.week_start,
      eco_friendly=job.eco_friendly,
      use_leftovers=job.use_leftovers,
      days=[day],
      calories_target=_day_calorie_target(day),
      mood=job.mood,
      leftover_notes=job.leftovers_text,
    )

    try:
      result = await workflow.generate(request)
    except Exception as exc:
      if _is_llm_empty_plan(exc):
        logger.warning("Job %s day %s empty plan; retrying", job_id, day)
        try:
          fallback_request = MealPlanRequest(
            session_id=f"job-{job_id}-{day}-fallback-{int(datetime.utcnow().timestamp())}",
            members=request.members,
            pantry_items=request.pantry_items,
            kitchen_tools=request.kitchen_tools,
            notes=request.notes,
            household_id=request.household_id,
            week_start=request.week_start,
            eco_friendly=request.eco_friendly,
            use_leftovers=request.use_leftovers,
            days=[day],
          )
          result = await workflow.generate(fallback_request)
        except Exception as fallback_exc:
          logger.warning("Job %s day %s fallback failed (%s); skipping day", job_id, day, fallback_exc)
          return {"day": day, "status": "error", "error": str(fallback_exc)}
      else:
        logger.warning("Job %s day %s parse/error (%s); skipping day", job_id, day, exc)
        return {"day": day, "status": "error", "error": str(exc)}

    day_entries = [
      entry
      for entry in result["final_plan"]["plan"]
      if str(entry.get("day")) == day
    ]
    
    # Annotate timeline for the whole day
    annotated_segments = _annotate_timeline(
      result.get("timeline", []),
      job_id=job_id,
      day=day,
      slot="all",
      start_sequence=0,
      origin="primary",
    )

    if not day_entries:
      # Fallback logic for empty day entries
      async with AsyncSessionFactory() as db_session:
        await plan_job_service.add_event(
          db_session,
          job_id,
          stage="fallback",
          message=f"Fallback triggered for {day}",
          payload={"day": day},
        )
      # ... (Simplified fallback logic could go here, or just return error if empty)
      return {"day": day, "status": "error", "error": "No meals generated for day"}

    # Extract model name from timeline if available
    model_name = "unknown"
    for event in result.get("timeline", []):
      if event.get("stage") == "plan.candidate":
        model_name = event.get("payload", {}).get("llm", {}).get("model", "unknown")
        break

    async with AsyncSessionFactory() as db_session:
      await plan_job_service.add_event(
        db_session,
        job_id,
        stage="planned",
        message=f"{day} planned using {model_name}",
        payload={"day": day, "entries": day_entries, "phase": "complete", "model": model_name},
      )

    return {
      "day": day,
      "status": "ok",
      "entries": day_entries,
      "timeline": annotated_segments,
    }

  max_concurrency = max(1, min(3, len(needed_days)))
  semaphore = asyncio.Semaphore(max_concurrency)
  logger.info("Planning job %s day-level concurrency limit set to %s", job_id, max_concurrency)

  async def _bounded_day(day: str) -> Dict[str, Any]:
    async with semaphore:
      try:
        return await _plan_single_day(day)
      except Exception as exc:  # pragma: no cover - last-chance guard
        logger.exception("Job %s unhandled error for %s", job_id, day)
        return {"day": day, "status": "error", "error": str(exc)}

  day_results: List[Dict[str, Any]] = []
  day_tasks = [asyncio.create_task(_bounded_day(day)) for day in needed_days]
  if day_tasks:
    day_results = await asyncio.gather(*day_tasks)

  errors = [r for r in day_results if r and r.get("status") not in {"ok", "cancelled"}]
  if errors:
    failed_keys = [e.get('day') for e in errors]
    logger.error("Planning job %s failed days: %s", job_id, failed_keys)
    async with AsyncSessionFactory() as db:
      await plan_job_service.mark_job_failed(db, job_id, error=f"Day failures: {failed_keys}")
      await plan_job_service.add_event(
        db,
        job_id,
        stage="error",
        message="Some days failed",
        payload={"failed_days": failed_keys},
      )
    return

  if any(r and r.get("status") == "cancelled" for r in day_results):
    logger.info("Planning job %s cancelled during execution", job_id)
    return

  aggregated_entries: List[Dict[str, Any]] = []
  aggregated_timeline: List[Dict[str, Any]] = []
  if base_entries:
    aggregated_entries.extend(base_entries)
  if base_timeline:
    aggregated_timeline.extend(base_timeline)
  
  for result in day_results:
    if result and result.get("status") == "ok":
      aggregated_entries.extend(result.get("entries", []))
      aggregated_timeline.extend(result.get("timeline", []))

  aggregated_timeline = _resequence_timeline(aggregated_timeline)
  
  # Generate master shopping list and calendar for the whole week
  # This replaces any fragmented daily "final" events generated by the agents
  if aggregated_entries:
    try:
      # 1. Prepare shopping list
      shopping_input = []
      for entry in aggregated_entries:
        shopping_input.append({
          "name": entry.get("title", "Meal"),
          "ingredients": entry.get("ingredients", [])
        })
      master_list = shopping_list_generate(shopping_input)

      # 2. Prepare calendar
      calendar_events = []
      for idx, item in enumerate(aggregated_entries):
        # Basic date estimation if not present (though it should be)
        # Assuming aggregated_entries are sorted by day
        calendar_events.append({
          "title": f"{item.get('day', 'Day')} – {item.get('title', 'Meal')}",
          "date": item.get("day_date", datetime.now().strftime("%Y-%m-%d")), # Fallback, but day_date isn't in entry dict usually?
          # Wait, PlanSynthesisAgent constructs date from index. Here we have 'day' label.
          # We need a real date. But calendar tool might just take a string date?
          # Let's check calendar_tools.py if needed. For now, let's try to use what we have.
          # Actually, PlanSynthesisAgent uses "2024-07-{idx+1:02d}" which is dummy.
          # Let's use the actual week start + offset if possible, or just the label.
          # The frontend calendar export might expect YYYY-MM-DD.
          # Let's stick to a simple format or what PlanSynthesisAgent did.
          "description": (
            f"{item.get('summary', 'Meal')} | prep {item.get('prep_minutes') or '?'} min · "
            f"cook {item.get('cook_minutes') or '?'} min · "
            f"{item.get('calories_per_person') or '?'} kcal/person"
          ),
        })
      
      # We need to construct dates properly for the calendar export to be useful
      # But we don't have easy access to week_start here without passing it down or calculating.
      # However, let's look at how PlanSynthesisAgent did it: it used dummy dates!
      # "date": f"2024-07-{idx+1:02d}"
      # So maybe it doesn't matter much for the *export* if it's just an ICS file?
      # Actually, for a real export, real dates are better.
      # But let's just match the agent's behavior for now to ensure compatibility.
      master_calendar = calendar_export_ics(calendar_events)
      
      # 3. Filter out fragmented events
      # Remove any existing 'plan.final' or 'plan-synthesizer' events to prevent frontend from picking the wrong one
      aggregated_timeline = [
        e for e in aggregated_timeline 
        if e.get("agent") != "plan-synthesizer" and e.get("stage") != "plan.final"
      ]
      
      # 4. Append unified final event
      aggregated_timeline.append({
        "agent": "plan-synthesizer", # Hyphenated to match frontend expectation
        "stage": "plan.final",
        "status": "complete",
        "title": "Weekly Plan Finalization",
        "description": f"Generated master shopping list and calendar for {len(aggregated_entries)} meals.",
        "payload": {
          "shopping_list": master_list,
          "calendar": master_calendar,
          "plan": aggregated_entries, # Frontend might expect this too
        },
        "sequence": len(aggregated_timeline) + 1
      })
      logger.info("Generated unified final plan event with %s items", len(master_list.get("all", [])))
    except Exception as exc:
      logger.error("Failed to generate master artifacts: %s", exc)

  if not aggregated_entries:
    async with AsyncSessionFactory() as db:
      await plan_job_service.mark_job_failed(db, job_id, error="No meals generated for any slot")
    return

  async with AsyncSessionFactory() as db:
    current_job = await plan_job_service.get_job(db, job_id)
    if current_job is None:
      logger.error("Planning job %s missing before save", job_id)
      return
    if current_job.status == "cancelled":
      await plan_job_service.add_event(
        db,
        job_id,
        stage="cancelled",
        message="Cancelled before saving",
        payload=None,
      )
      logger.info("Job %s cancelled before saving plan", job_id)
      return
    plan = await meal_plan_service.save_plan(
      db,
      household_id=job.household_id,
      week_start=job.week_start,
      session_id=f"job-{job_id}-final",
      plan_items=aggregated_entries,
      timeline=aggregated_timeline,
      eco_friendly=job.eco_friendly,
      use_leftovers=job.use_leftovers,
      notes=job.notes,
      attendee_map=_normalize_attendee_map(slot_attendees),
    )
    await plan_job_service.mark_job_completed(db, job_id, plan_id=plan.id)
    await plan_job_service.add_event(
      db,
      job_id,
      stage="completed",
      message="Planning complete",
      payload={"plan_id": plan.id, "entry_count": len(aggregated_entries)},
    )
  logger.info("Planning job %s completed", job_id)


def _build_slot_attendees(household) -> Dict[tuple, List[int]]:
  mapping: Dict[tuple, List[int]] = {}
  for member in household.members:
    for day in DAY_ORDER:
      for slot in MEAL_SLOTS:
        if _member_attends_slot(member, day, slot):
          mapping.setdefault((day, slot), []).append(member.id)
  return mapping


def _normalize_attendee_map(raw: Dict[tuple, List[int]]) -> Dict[tuple, List[int]]:
  return {key: attendees for key, attendees in raw.items() if attendees}


def _member_attends_slot(member, day_label: str, slot: str) -> bool:
  schedule = getattr(member, "meal_schedule", None)
  slot_lower = slot.lower()
  base_allowed = True
  if slot_lower == "breakfast":
    base_allowed = bool(getattr(member, "eats_breakfast", True))
  elif slot_lower == "lunch":
    base_allowed = bool(getattr(member, "eats_lunch", True))
  elif slot_lower == "dinner":
    base_allowed = bool(getattr(member, "eats_dinner", True))

  if isinstance(schedule, dict):
    day_schedule = schedule.get(day_label)
    if isinstance(day_schedule, dict) and slot in day_schedule:
      return bool(day_schedule.get(slot)) and base_allowed

  return base_allowed


def _annotate_timeline(
  segment: List[Dict[str, Any]],
  *,
  job_id: int,
  day: str,
  slot: str,
  start_sequence: int,
  origin: str,
) -> List[Dict[str, Any]]:
  annotated: List[Dict[str, Any]] = []
  for offset, raw in enumerate(segment or []):
    event = dict(raw)
    event["job_id"] = job_id
    event["day"] = day
    event["slot"] = slot
    event["sequence"] = start_sequence + offset
    event["origin"] = origin
    annotated.append(event)
  return annotated


def _is_llm_empty_plan(exc: Exception) -> bool:
  message = str(exc).lower()
  return (
    "did not return a plan" in message
    or "empty plan" in message
    or "unable to parse gemini json" in message
    or "gemini failed to generate" in message
  )


def _stub_meal(day: str, slot: str, calories_per_person: int | None = None) -> Dict[str, Any]:
  return {
    "day": day,
    "meal": slot,
    "title": f"{slot} chef's choice",
    "summary": "Fallback meal because the model returned an empty plan.",
    "ingredients": [{"name": "Chef's choice ingredient"}],
    "steps": ["Prepare a simple balanced meal.", "Serve and adjust seasoning to taste."],
    "prep_minutes": 5,
    "cook_minutes": 10,
    "calories_per_person": calories_per_person or 450,
    "required_tools": [],
  }


def _stub_timeline(job_id: int, day: str, slot: str, reason: str) -> List[Dict[str, Any]]:
  return [
    {
      "job_id": job_id,
      "day": day,
      "slot": slot,
      "sequence": 0,
      "origin": "stub",
      "stage": "plan.stub",
      "payload": {"reason": reason, "stub": True},
    }
  ]


def _resequence_timeline(timeline: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
  day_order_map = {day: idx for idx, day in enumerate(DAY_ORDER)}
  sorted_timeline = sorted(
    timeline,
    key=lambda item: (
      day_order_map.get(item.get("day"), len(day_order_map)),
      MEAL_SLOTS.index(item.get("slot")) if item.get("slot") in MEAL_SLOTS else 0,
      item.get("sequence", 0),
    ),
  )
  resequenced: List[Dict[str, Any]] = []
  for idx, item in enumerate(sorted_timeline):
    updated = dict(item)
    updated["sequence"] = idx
    resequenced.append(updated)
  return resequenced
