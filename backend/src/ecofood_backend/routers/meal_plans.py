from __future__ import annotations

from datetime import date
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.a2a import MealPlanningWorkflow
from ..agent.a2a.workflow import MealPlanRequest
from ..database import get_session
from ..schemas import (
  MealPlanEntryResponse,
  MealPlanEntryUpdate,
  MealPlanResponse,
  MealPlanSummaryResponse,
  PlanWeekRequest,
)
from ..services import households as household_service
from ..services import meal_plans as meal_plan_service

router = APIRouter(tags=["meal-plans"])
workflow = MealPlanningWorkflow()


async def _ensure_household(db: AsyncSession, household_id: int):
  household = await household_service.get_household_with_members(db, household_id)
  if household is None:
    raise HTTPException(status_code=404, detail="Household not found")
  await household_service.list_kitchen_tools(db, household_id)
  await db.refresh(household, attribute_names=["kitchen_tools"])
  return household


@router.get(
  "/households/{household_id}/plans",
  response_model=List[MealPlanSummaryResponse],
)
async def list_household_plans(
  household_id: int = Path(..., gt=0),
  db: AsyncSession = Depends(get_session),
) -> List[MealPlanSummaryResponse]:
  await _ensure_household(db, household_id)
  return await meal_plan_service.list_week_summaries(db, household_id)


@router.get(
  "/households/{household_id}/plans/{week_start}",
  response_model=MealPlanResponse,
)
async def get_plan_for_week(
  household_id: int = Path(..., gt=0),
  week_start: date = Path(...),
  db: AsyncSession = Depends(get_session),
) -> MealPlanResponse:
  await _ensure_household(db, household_id)
  plan = await meal_plan_service.get_plan_by_week(db, household_id, week_start)
  if plan is None:
    raise HTTPException(status_code=404, detail="Meal plan not found")
  return plan


@router.post(
  "/households/{household_id}/plans",
  response_model=MealPlanResponse,
  status_code=201,
)
async def create_week_plan(
  payload: PlanWeekRequest,
  household_id: int = Path(..., gt=0),
  db: AsyncSession = Depends(get_session),
) -> MealPlanResponse:
  household = await _ensure_household(db, household_id)
  if not household.members:
    raise HTTPException(
      status_code=400,
      detail="Add at least one member to the household before planning meals.",
    )

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

  session_id = f"plan-{household_id}-{payload.week_start.isoformat()}-{uuid4().hex[:8]}"

  workflow_request = MealPlanRequest(
    session_id=session_id,
    members=members_payload,
    pantry_items=[],  # Pantry integration will populate this later.
    kitchen_tools=kitchen_payload,
    notes=payload.notes,
    household_id=household_id,
    week_start=payload.week_start,
    eco_friendly=payload.eco_friendly,
    use_leftovers=payload.use_leftovers,
  )
  workflow_result = await workflow.generate(workflow_request)

  plan = await meal_plan_service.save_plan(
    db,
    household_id=household_id,
    week_start=payload.week_start,
    session_id=workflow_result["session_id"],
    plan_items=workflow_result["final_plan"]["plan"],
    timeline=workflow_result["timeline"],
    eco_friendly=payload.eco_friendly,
    use_leftovers=payload.use_leftovers,
    notes=payload.notes,
  )
  return plan


@router.delete("/households/{household_id}/plans/{week_start}", status_code=204)
async def delete_week_plan(
  household_id: int = Path(..., gt=0),
  week_start: date = Path(...),
  db: AsyncSession = Depends(get_session),
) -> None:
  await _ensure_household(db, household_id)
  await meal_plan_service.delete_plan_for_week(db, household_id, week_start)
  return None


@router.patch(
  "/meal-plan-entries/{entry_id}",
  response_model=MealPlanEntryResponse,
)
async def update_meal_plan_entry(
  payload: MealPlanEntryUpdate,
  entry_id: int = Path(..., gt=0),
  db: AsyncSession = Depends(get_session),
) -> MealPlanEntryResponse:
  if payload.title is None and payload.summary is None:
    raise HTTPException(status_code=400, detail="No fields provided for update.")
  entry = await meal_plan_service.update_entry(db, entry_id, payload)
  if entry is None:
    raise HTTPException(status_code=404, detail="Meal plan entry not found")
  return entry
