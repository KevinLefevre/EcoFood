from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.dialog.household_assistant import HouseholdAssistant
from ..database import get_session
from ..schemas import (
  AssistantMessageRequest,
  AssistantMessageResponse,
  HouseholdCreate,
  HouseholdResponse,
  KitchenToolCreate,
  KitchenToolResponse,
  KitchenToolUpdate,
  MemberCreate,
  MemberMealsUpdate,
  MemberResponse,
)
from ..services import households as household_service

router = APIRouter(prefix="/households", tags=["households"])
assistant = HouseholdAssistant()


@router.get("", response_model=List[HouseholdResponse])
async def get_households(db: AsyncSession = Depends(get_session)) -> List[HouseholdResponse]:
  return await household_service.list_households(db)


@router.post("", response_model=HouseholdResponse, status_code=201)
async def create_household(
  payload: HouseholdCreate,
  db: AsyncSession = Depends(get_session),
) -> HouseholdResponse:
  return await household_service.create_household(db, payload)


@router.post("/{household_id}/members", response_model=MemberResponse, status_code=201)
async def add_member(
  payload: MemberCreate,
  household_id: int = Path(..., gt=0),
  db: AsyncSession = Depends(get_session),
) -> MemberResponse:
  return await household_service.create_member(db, household_id, payload)


@router.delete("/{household_id}/members/{member_id}", status_code=204)
async def remove_member(
  household_id: int = Path(..., gt=0),
  member_id: int = Path(..., gt=0),
  db: AsyncSession = Depends(get_session),
) -> None:
  await household_service.delete_member(db, household_id, member_id)
  return None


@router.patch(
  "/{household_id}/members/{member_id}/meals",
  response_model=MemberResponse,
)
async def update_member_meals(
  payload: MemberMealsUpdate,
  household_id: int = Path(..., gt=0),
  member_id: int = Path(..., gt=0),
  db: AsyncSession = Depends(get_session),
) -> MemberResponse:
  member = await household_service.update_member_meals(
    db,
    household_id=household_id,
    member_id=member_id,
    meals=payload.meals,
    schedule=payload.schedule,
  )
  if member is None:
    raise HTTPException(status_code=404, detail="Household member not found")
  return member


@router.post("/{household_id}/assistant", response_model=AssistantMessageResponse)
async def household_assistant(
  household_id: int,
  payload: AssistantMessageRequest,
  db: AsyncSession = Depends(get_session),
) -> AssistantMessageResponse:
  response = await assistant.handle_message(
    db=db,
    household_id=household_id,
    session_id=payload.session_id,
    user_message=payload.message,
  )
  if response is None:
    raise HTTPException(status_code=400, detail="Unable to process assistant message")
  return response


@router.get("/{household_id}/kitchen", response_model=List[KitchenToolResponse])
async def list_kitchen_tools(
  household_id: int,
  db: AsyncSession = Depends(get_session),
) -> List[KitchenToolResponse]:
  if await household_service.get_household_with_members(db, household_id) is None:
    raise HTTPException(status_code=404, detail="Household not found")
  return await household_service.list_kitchen_tools(db, household_id)


@router.post(
  "/{household_id}/kitchen",
  response_model=KitchenToolResponse,
  status_code=201,
)
async def add_kitchen_tool(
  payload: KitchenToolCreate,
  household_id: int,
  db: AsyncSession = Depends(get_session),
) -> KitchenToolResponse:
  if await household_service.get_household_with_members(db, household_id) is None:
    raise HTTPException(status_code=404, detail="Household not found")
  return await household_service.add_kitchen_tool(db, household_id, payload)


@router.patch(
  "/{household_id}/kitchen/{tool_id}",
  response_model=KitchenToolResponse,
)
async def update_kitchen_tool(
  payload: KitchenToolUpdate,
  household_id: int,
  tool_id: int,
  db: AsyncSession = Depends(get_session),
) -> KitchenToolResponse:
  if payload.quantity is None and payload.label is None and payload.category is None:
    raise HTTPException(status_code=400, detail="No fields provided for update.")
  tool = await household_service.update_kitchen_tool(db, household_id, tool_id, payload)
  if tool is None:
    raise HTTPException(status_code=404, detail="Kitchen tool not found")
  return tool


@router.delete("/{household_id}/kitchen/{tool_id}", status_code=204)
async def delete_kitchen_tool(
  household_id: int,
  tool_id: int,
  db: AsyncSession = Depends(get_session),
) -> None:
  await household_service.delete_kitchen_tool(db, household_id, tool_id)
  return None
