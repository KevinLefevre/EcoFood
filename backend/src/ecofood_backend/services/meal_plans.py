from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import MealPlan, MealPlanEntry
from ..schemas import (
  MealPlanEntryResponse,
  MealPlanEntryUpdate,
  MealPlanResponse,
  MealPlanSummaryResponse,
)

DAY_INDEX = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
MEAL_SLOTS = ["Breakfast", "Lunch", "Dinner"]


def _map_plan(plan: MealPlan) -> MealPlanResponse:
  entries = [
    MealPlanEntryResponse.model_validate(entry)
    for entry in sorted(plan.entries, key=lambda e: (e.day, MEAL_SLOTS.index(e.slot)))
  ]
  return MealPlanResponse(
    id=plan.id,
    household_id=plan.household_id,
    week_start=plan.week_start,
    eco_friendly=plan.eco_friendly,
    use_leftovers=plan.use_leftovers,
    notes=plan.notes,
    timeline=plan.timeline,
    entries=entries,
  )


async def list_week_summaries(db: AsyncSession, household_id: int) -> List[MealPlanSummaryResponse]:
  result = await db.execute(
    select(MealPlan)
    .where(MealPlan.household_id == household_id)
    .order_by(MealPlan.week_start.desc())
  )
  plans = result.scalars().all()
  return [MealPlanSummaryResponse.model_validate(plan) for plan in plans]


async def get_plan_by_week(
  db: AsyncSession,
  household_id: int,
  week_start: date,
) -> Optional[MealPlanResponse]:
  result = await db.execute(
    select(MealPlan)
    .options(selectinload(MealPlan.entries))
    .where(
      MealPlan.household_id == household_id,
      MealPlan.week_start == week_start,
    )
  )
  plan = result.scalar_one_or_none()
  if plan is None:
    return None
  return _map_plan(plan)


async def get_plan_by_id(db: AsyncSession, plan_id: int) -> Optional[MealPlanResponse]:
  result = await db.execute(
    select(MealPlan).options(selectinload(MealPlan.entries)).where(MealPlan.id == plan_id)
  )
  plan = result.scalar_one_or_none()
  if plan is None:
    return None
  return _map_plan(plan)


def _build_entry_map(plan_entries: Iterable[MealPlanEntry]) -> dict[tuple[date, str], MealPlanEntry]:
  return {(entry.day, entry.slot): entry for entry in plan_entries}


async def save_plan(
  db: AsyncSession,
  *,
  household_id: int,
  week_start: date,
  session_id: str,
  plan_items: List[dict],
  timeline: list,
  eco_friendly: bool,
  use_leftovers: bool,
  notes: Optional[str],
) -> MealPlanResponse:
  existing = await db.execute(
    select(MealPlan).where(
      MealPlan.household_id == household_id,
      MealPlan.week_start == week_start,
    )
  )
  existing_plan = existing.scalar_one_or_none()
  if existing_plan:
    await db.delete(existing_plan)
    await db.flush()

  plan = MealPlan(
    household_id=household_id,
    week_start=week_start,
    session_id=session_id,
    eco_friendly=eco_friendly,
    use_leftovers=use_leftovers,
    notes=notes,
    timeline=timeline,
  )
  db.add(plan)
  await db.flush()

  for item in plan_items:
    day_label = item.get("day", "Mon")
    slot = item.get("meal", "Dinner")
    day_offset = DAY_INDEX.get(day_label, 0)
    day_value = week_start + timedelta(days=day_offset)
    db.add(
      MealPlanEntry(
        plan_id=plan.id,
        day=day_value,
        slot=slot,
        title=item.get("title"),
        summary=item.get("summary"),
      )
    )

  await db.commit()
  await db.refresh(plan)
  return await get_plan_by_id(db, plan.id)


async def update_entry(
  db: AsyncSession,
  entry_id: int,
  payload: MealPlanEntryUpdate,
) -> Optional[MealPlanEntryResponse]:
  result = await db.execute(select(MealPlanEntry).where(MealPlanEntry.id == entry_id))
  entry = result.scalar_one_or_none()
  if entry is None:
    return None
  if payload.title is not None:
    entry.title = payload.title
  if payload.summary is not None:
    entry.summary = payload.summary
  await db.commit()
  await db.refresh(entry)
  return MealPlanEntryResponse.model_validate(entry)


async def delete_plan_for_week(
  db: AsyncSession,
  household_id: int,
  week_start: date,
) -> bool:
  result = await db.execute(
    select(MealPlan).where(
      MealPlan.household_id == household_id,
      MealPlan.week_start == week_start,
    )
  )
  plan = result.scalar_one_or_none()
  if plan is None:
    return False
  await db.delete(plan)
  await db.commit()
  return True
