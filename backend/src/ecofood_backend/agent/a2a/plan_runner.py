from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

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
  aggregated_entries: List[Dict[str, Any]] = []
  aggregated_timeline: List[Dict[str, Any]] = []
  timeline_sequence = 0

  async with AsyncSessionFactory() as db:
    job = await plan_job_service.get_job(db, job_id)
    if job is None:
      logger.error("Planning job %s disappeared before execution", job_id)
      return
    household = await household_service.get_household_with_members(db, job.household_id)
    members_payload = [
      {
        "name": member.name,
        "role": member.role,
        "allergens": [allergen.label for allergen in member.allergens],
        "likes": [pref.label for pref in member.preferences],
      }
      for member in household.members
    ]
    kitchen_payload = [
      {
        "label": tool.label,
        "category": tool.category,
        "quantity": tool.quantity,
      }
      for tool in household.kitchen_tools
    ]
    slot_attendees = _build_slot_attendees(household)

  for day in DAY_ORDER:
    logger.info("Job %s planning %s", job_id, day)
    async with AsyncSessionFactory() as db:
      current_job = await plan_job_service.get_job(db, job_id)
      if current_job is None:
        logger.error("Planning job %s disappeared mid-run", job_id)
        await plan_job_service.mark_job_failed(db, job_id, error="Job missing mid-run")
        await plan_job_service.add_event(
          db,
          job_id,
          stage="error",
          message="Job missing while planning",
          payload={"day": day},
        )
        return
      if current_job.status == "cancelled":
        logger.info("Job %s cancelled before %s", job_id, day)
        await plan_job_service.add_event(
          db,
          job_id,
          stage="cancelled",
          message=f"Cancelled before {day}",
          payload={"day": day},
        )
        return
      await plan_job_service.add_event(
        db,
        job_id,
        stage="planning",
        message=f"Planning {day}",
        payload={"day": day, "phase": "start"},
      )

    session_id = f"job-{job_id}-{day}-{int(datetime.utcnow().timestamp())}"
    request = MealPlanRequest(
      session_id=session_id,
      members=members_payload,
      pantry_items=[],
      kitchen_tools=kitchen_payload,
      notes=job.notes,
      household_id=job.household_id,
      week_start=job.week_start,
      eco_friendly=job.eco_friendly,
      use_leftovers=job.use_leftovers,
      days=[day],
    )
    try:
      result = await workflow.generate(request)
    except Exception as exc:
      if _is_llm_empty_plan(exc):
        logger.warning("Job %s day %s received empty plan; retrying full week", job_id, day)
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
            days=None,
          )
          logger.info("Job %s fallback prompt preview (day=%s)", job_id, day)
          result = await workflow.generate(fallback_request)
        except Exception as fallback_exc:
          logger.exception("Job %s fallback failed for %s", job_id, day)
          async with AsyncSessionFactory() as db:
            await plan_job_service.mark_job_failed(db, job_id, error=str(fallback_exc))
            await plan_job_service.add_event(
              db,
              job_id,
              stage="error",
              message=f"{day} failed",
              payload={"error": str(fallback_exc)},
            )
          return
      else:
        logger.exception("Job %s failed while planning %s", job_id, day)
        async with AsyncSessionFactory() as db:
          await plan_job_service.mark_job_failed(db, job_id, error=str(exc))
          await plan_job_service.add_event(
            db,
            job_id,
            stage="error",
            message=f"{day} failed",
            payload={"error": str(exc)},
          )
        return
    day_entries = [entry for entry in result["final_plan"]["plan"] if entry.get("day") == day]
    primary_segment = _annotate_timeline(
      result.get("timeline", []),
      job_id=job_id,
      day=day,
      start_sequence=timeline_sequence,
      origin="primary",
    )
    timeline_sequence += len(primary_segment)
    annotated_segments = list(primary_segment)

    if not day_entries:
      logger.warning("Job %s received no entries for %s, running fallback week generation", job_id, day)
      async with AsyncSessionFactory() as db:
        await plan_job_service.add_event(
          db,
          job_id,
          stage="fallback",
          message=f"Fallback triggered for {day}",
          payload={"day": day},
        )
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
        days=None,
      )
      fallback_result = await workflow.generate(fallback_request)
      fallback_entries = [entry for entry in fallback_result["final_plan"]["plan"] if entry.get("day") == day]
      fallback_segment = _annotate_timeline(
        fallback_result.get("timeline", []),
        job_id=job_id,
        day=day,
        start_sequence=timeline_sequence,
        origin="fallback",
      )
      timeline_sequence += len(fallback_segment)
      annotated_segments.extend(fallback_segment)
      day_entries = fallback_entries
      if not day_entries:
        logger.error("Job %s fallback failed for %s", job_id, day)
        async with AsyncSessionFactory() as db:
          await plan_job_service.mark_job_failed(db, job_id, error=f"No meals for {day}")
          await plan_job_service.add_event(
            db,
            job_id,
            stage="error",
            message=f"No meals for {day}",
            payload={"day": day},
          )
        return

    aggregated_entries.extend(day_entries)
    aggregated_timeline.extend(annotated_segments)

    async with AsyncSessionFactory() as db:
      await plan_job_service.add_event(
        db,
        job_id,
        stage="planned",
        message=f"{day} planned",
        payload={"day": day, "entries": day_entries, "phase": "complete"},
      )

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
  start_sequence: int,
  origin: str,
) -> List[Dict[str, Any]]:
  annotated: List[Dict[str, Any]] = []
  for offset, raw in enumerate(segment or []):
    event = dict(raw)
    event["job_id"] = job_id
    event["day"] = day
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
  )
