from __future__ import annotations

from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import (
  Household,
  HouseholdMember,
  KitchenTool,
  MemberAllergen,
  MemberPreference,
)
from ..schemas import (
  DEFAULT_MEMBER_MEALS,
  HouseholdCreate,
  HouseholdResponse,
  KitchenToolCreate,
  KitchenToolResponse,
  KitchenToolUpdate,
  MemberCreate,
  MemberResponse,
  MealSchedule,
)

DEFAULT_KITCHEN_TOOLS: List[KitchenToolCreate] = [
  KitchenToolCreate(label="Small pan", category="Pan"),
  KitchenToolCreate(label="Medium pan", category="Pan"),
  KitchenToolCreate(label="Large pan", category="Pan"),
  KitchenToolCreate(label="Medium casserole", category="Casserole"),
  KitchenToolCreate(label="Large casserole", category="Casserole"),
  KitchenToolCreate(label="Cake mold", category="Bakeware"),
  KitchenToolCreate(label="Tart mold", category="Bakeware"),
]


async def list_households(db: AsyncSession) -> List[HouseholdResponse]:
  result = await db.execute(
    select(Household).options(
      selectinload(Household.members)
      .selectinload(HouseholdMember.allergens),
      selectinload(Household.members)
      .selectinload(HouseholdMember.preferences),
      selectinload(Household.kitchen_tools),
    )
  )
  households = result.scalars().unique().all()
  return [await _to_household_response(db, household) for household in households]


async def create_household(db: AsyncSession, payload: HouseholdCreate) -> HouseholdResponse:
  household = Household(name=payload.name)
  db.add(household)
  await db.flush()

  for member_payload in payload.members:
    await _create_member(db, household.id, member_payload)
  await _ensure_default_kitchen_tools(db, household.id)

  await db.commit()
  await db.refresh(household)
  return await _to_household_response(db, household)


async def create_member(db: AsyncSession, household_id: int, payload: MemberCreate) -> MemberResponse:
  member = await _create_member(db, household_id, payload)
  await db.commit()
  await db.refresh(member)
  return await _to_member_response(db, member)


async def delete_member(db: AsyncSession, household_id: int, member_id: int) -> None:
  result = await db.execute(
    select(HouseholdMember).where(
      HouseholdMember.id == member_id,
      HouseholdMember.household_id == household_id,
    )
  )
  member = result.scalar_one_or_none()
  if member is None:
    return
  await db.delete(member)
  await db.commit()


async def _create_member(db: AsyncSession, household_id: int, payload: MemberCreate) -> HouseholdMember:
  member = HouseholdMember(
    household_id=household_id,
    name=payload.name,
    role=payload.role,
    **_meals_to_flags(payload.meals),
    meal_schedule=_normalize_schedule(payload.meal_schedule),
  )
  db.add(member)
  await db.flush()

  for label in payload.allergens:
    if not label:
      continue
    db.add(MemberAllergen(member_id=member.id, label=label))
  for label in payload.likes:
    if not label:
      continue
    db.add(MemberPreference(member_id=member.id, label=label))

  return member


async def _to_household_response(db: AsyncSession, household: Household) -> HouseholdResponse:
  if "kitchen_tools" not in household.__dict__:
    await db.refresh(household, attribute_names=["kitchen_tools"])
  members = [await _to_member_response(db, member) for member in household.members]
  tools = (
    [KitchenToolResponse.model_validate(tool) for tool in household.kitchen_tools]
    if household.kitchen_tools
    else await list_kitchen_tools(db, household.id)
  )
  data = {
    "id": household.id,
    "name": household.name,
    "created_at": household.created_at,
    "members": members,
    "kitchen_tools": tools,
  }
  return HouseholdResponse(**data)


async def _to_member_response(db: AsyncSession, member: HouseholdMember) -> MemberResponse:
  if "allergens" not in member.__dict__:
    await db.refresh(member, attribute_names=["allergens"])
  if "preferences" not in member.__dict__:
    await db.refresh(member, attribute_names=["preferences"])
  data = {
    "id": member.id,
    "name": member.name,
    "role": member.role,
    "allergens": [a.label for a in member.allergens],
    "likes": [p.label for p in member.preferences],
    "meals": _flags_to_meals(member),
    "meal_schedule": member.meal_schedule,
  }
  return MemberResponse(**data)


async def get_household_with_members(db: AsyncSession, household_id: int) -> Household | None:
  result = await db.execute(
    select(Household)
    .options(
      selectinload(Household.members)
      .selectinload(HouseholdMember.allergens),
      selectinload(Household.members)
      .selectinload(HouseholdMember.preferences),
      selectinload(Household.kitchen_tools),
    )
    .where(Household.id == household_id)
  )
  return result.scalar_one_or_none()


async def list_kitchen_tools(db: AsyncSession, household_id: int) -> List[KitchenToolResponse]:
  result = await db.execute(
    select(KitchenTool).where(KitchenTool.household_id == household_id).order_by(KitchenTool.id.asc())
  )
  tools = result.scalars().all()
  if not tools:
    await _ensure_default_kitchen_tools(db, household_id)
    await db.commit()
    tools = (
      await db.execute(
        select(KitchenTool)
        .where(KitchenTool.household_id == household_id)
        .order_by(KitchenTool.id.asc())
      )
    ).scalars().all()
  return [KitchenToolResponse.model_validate(tool) for tool in tools]


async def add_kitchen_tool(
  db: AsyncSession,
  household_id: int,
  payload: KitchenToolCreate,
) -> KitchenToolResponse:
  tool = KitchenTool(
    household_id=household_id,
    label=payload.label,
    category=payload.category,
    quantity=payload.quantity,
  )
  db.add(tool)
  await db.commit()
  await db.refresh(tool)
  return KitchenToolResponse.model_validate(tool)


async def update_kitchen_tool(
  db: AsyncSession,
  household_id: int,
  tool_id: int,
  payload: KitchenToolUpdate,
) -> KitchenToolResponse | None:
  result = await db.execute(
    select(KitchenTool).where(
      KitchenTool.id == tool_id,
      KitchenTool.household_id == household_id,
    )
  )
  tool = result.scalar_one_or_none()
  if tool is None:
    return None
  if payload.label is not None:
    tool.label = payload.label
  if payload.category is not None:
    tool.category = payload.category
  if payload.quantity is not None:
    tool.quantity = max(0, payload.quantity)
  await db.commit()
  await db.refresh(tool)
  return KitchenToolResponse.model_validate(tool)


async def delete_kitchen_tool(db: AsyncSession, household_id: int, tool_id: int) -> None:
  result = await db.execute(
    select(KitchenTool).where(
      KitchenTool.id == tool_id,
      KitchenTool.household_id == household_id,
    )
  )
  tool = result.scalar_one_or_none()
  if tool is None:
    return
  await db.delete(tool)
  await db.commit()


async def _ensure_default_kitchen_tools(db: AsyncSession, household_id: int) -> None:
  result = await db.execute(
    select(KitchenTool.id).where(KitchenTool.household_id == household_id)
  )
  if result.scalars().first() is not None:
    return
  for tool in DEFAULT_KITCHEN_TOOLS:
    db.add(
      KitchenTool(
        household_id=household_id,
        label=tool.label,
        category=tool.category,
        quantity=tool.quantity,
      )
    )
  await db.flush()


def _meals_to_flags(meals: List[str]) -> dict[str, bool]:
  normalized = {meal.lower() for meal in meals or []}
  return {
    "eats_breakfast": "breakfast" in normalized or not normalized,
    "eats_lunch": "lunch" in normalized or not normalized,
    "eats_dinner": "dinner" in normalized or not normalized,
  }


def _flags_to_meals(member: HouseholdMember) -> List[str]:
  meals: List[str] = []
  if member.eats_breakfast:
    meals.append("Breakfast")
  if member.eats_lunch:
    meals.append("Lunch")
  if member.eats_dinner:
    meals.append("Dinner")
  return meals


def _normalize_schedule(schedule: MealSchedule | None) -> MealSchedule | None:
  if not schedule:
    return None
  normalized: MealSchedule = {}
  for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
    day_schedule = schedule.get(day, {}) if isinstance(schedule, dict) else {}
    normalized[day] = {}
    for slot in DEFAULT_MEMBER_MEALS:
      slot_value = False
      if isinstance(day_schedule, dict):
        slot_value = bool(day_schedule.get(slot))
      normalized[day][slot] = slot_value
  return normalized


def _derive_meals_from_schedule(schedule: MealSchedule | None) -> List[str]:
  if not schedule:
    return []
  meals: List[str] = []
  for slot in DEFAULT_MEMBER_MEALS:
    if any(day_schedule.get(slot) for day_schedule in schedule.values()):
      meals.append(slot)
  return meals


async def update_member_meals(
  db: AsyncSession,
  household_id: int,
  member_id: int,
  meals: List[str] | None,
  schedule: MealSchedule | None,
) -> MemberResponse | None:
  result = await db.execute(
    select(HouseholdMember).where(
      HouseholdMember.id == member_id,
      HouseholdMember.household_id == household_id,
    )
  )
  member = result.scalar_one_or_none()
  if member is None:
    return None
  if schedule is not None:
    normalized_schedule = _normalize_schedule(schedule)
    member.meal_schedule = normalized_schedule
    if meals is None:
      meals = _derive_meals_from_schedule(normalized_schedule)
  if meals is not None:
    flags = _meals_to_flags(meals)
    member.eats_breakfast = flags["eats_breakfast"]
    member.eats_lunch = flags["eats_lunch"]
    member.eats_dinner = flags["eats_dinner"]
    if schedule is None:
      member.meal_schedule = None
  await db.commit()
  await db.refresh(member)
  return await _to_member_response(db, member)
