from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

DEFAULT_MEMBER_MEALS = ["Breakfast", "Lunch", "Dinner"]


MealSchedule = Dict[str, Dict[str, bool]]


class MemberBase(BaseModel):
  name: str
  role: str = "Adult"
  allergens: List[str] = Field(default_factory=list)
  likes: List[str] = Field(default_factory=list)
  meals: List[str] = Field(default_factory=lambda: list(DEFAULT_MEMBER_MEALS))
  meal_schedule: Optional[MealSchedule] = None


class MemberCreate(MemberBase):
  pass


class MemberResponse(MemberBase):
  id: int

  class Config:
    from_attributes = True


class HouseholdBase(BaseModel):
  name: str = "My Household"


class HouseholdCreate(HouseholdBase):
  members: List[MemberCreate] = Field(default_factory=list)


class HouseholdResponse(HouseholdBase):
  id: int
  created_at: datetime
  members: List[MemberResponse] = Field(default_factory=list)
  kitchen_tools: List["KitchenToolResponse"] = Field(default_factory=list)

  class Config:
    from_attributes = True


class AssistantMessageRequest(BaseModel):
  session_id: str
  message: Optional[str] = None


class AssistantMessageResponse(BaseModel):
  session_id: str
  stage: str
  agent_message: str
  completed: bool = False
  member: Optional[MemberResponse] = None


class MealPlanEntryResponse(BaseModel):
  id: int
  plan_id: int
  day: date
  slot: str
  title: Optional[str] = None
  summary: Optional[str] = None
  ingredients: List["RecipeIngredient"] = Field(default_factory=list)
  steps: List[str] = Field(default_factory=list)
  prep_minutes: Optional[int] = None
  cook_minutes: Optional[int] = None
  calories_per_person: Optional[int] = None
  attendee_ids: List[int] = Field(default_factory=list)
  guest_count: int = 0

  class Config:
    from_attributes = True


class MealPlanResponse(BaseModel):
  id: int
  household_id: int
  week_start: date
  eco_friendly: bool
  use_leftovers: bool
  notes: Optional[str] = None
  timeline: Optional[Any] = None
  entries: List[MealPlanEntryResponse] = Field(default_factory=list)

  class Config:
    from_attributes = True


class MealPlanSummaryResponse(BaseModel):
  id: int
  household_id: int
  week_start: date
  eco_friendly: bool
  use_leftovers: bool
  created_at: datetime

  class Config:
    from_attributes = True


class PlanWeekRequest(BaseModel):
  week_start: date
  eco_friendly: bool = False
  use_leftovers: bool = False
  notes: Optional[str] = None


class MealPlanEntryUpdate(BaseModel):
  title: Optional[str] = None
  summary: Optional[str] = None
  attendee_ids: Optional[List[int]] = None
  guest_count: Optional[int] = None


class KitchenToolBase(BaseModel):
  label: str
  category: Optional[str] = None
  quantity: int = 0


class KitchenToolCreate(KitchenToolBase):
  pass


class KitchenToolUpdate(BaseModel):
  label: Optional[str] = None
  category: Optional[str] = None
  quantity: Optional[int] = None


class KitchenToolResponse(KitchenToolBase):
  id: int

  class Config:
    from_attributes = True


class RecipeIngredient(BaseModel):
  name: str
  quantity: Optional[str | float] = None
  unit: Optional[str] = None
  notes: Optional[str] = None


class MemberMealsUpdate(BaseModel):
  meals: Optional[List[str]] = None
  schedule: Optional[MealSchedule] = None
