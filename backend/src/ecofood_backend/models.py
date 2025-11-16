from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Household(Base):
  __tablename__ = "households"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  name: Mapped[str] = mapped_column(String(120))
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    server_default=func.now(),
  )

  members: Mapped[List["HouseholdMember"]] = relationship(
    back_populates="household",
    cascade="all, delete-orphan",
    passive_deletes=True,
  )
  meal_plans: Mapped[List["MealPlan"]] = relationship(
    back_populates="household",
    cascade="all, delete-orphan",
    passive_deletes=True,
  )
  kitchen_tools: Mapped[List["KitchenTool"]] = relationship(
    back_populates="household",
    cascade="all, delete-orphan",
    passive_deletes=True,
  )


class HouseholdMember(Base):
  __tablename__ = "household_members"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  household_id: Mapped[int] = mapped_column(
    ForeignKey("households.id", ondelete="CASCADE"),
    index=True,
  )
  name: Mapped[str] = mapped_column(String(120))
  role: Mapped[str] = mapped_column(String(50), default="Adult")
  eats_breakfast: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
  eats_lunch: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
  eats_dinner: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
  meal_schedule: Mapped[dict | None] = mapped_column(JSON, nullable=True)

  household: Mapped[Household] = relationship(back_populates="members")
  allergens: Mapped[List["MemberAllergen"]] = relationship(
    back_populates="member",
    cascade="all, delete-orphan",
  )
  preferences: Mapped[List["MemberPreference"]] = relationship(
    back_populates="member",
    cascade="all, delete-orphan",
  )


class MemberAllergen(Base):
  __tablename__ = "member_allergens"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  member_id: Mapped[int] = mapped_column(
    ForeignKey("household_members.id", ondelete="CASCADE"),
    index=True,
  )
  label: Mapped[str] = mapped_column(String(120))

  member: Mapped[HouseholdMember] = relationship(back_populates="allergens")


class MemberPreference(Base):
  __tablename__ = "member_preferences"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  member_id: Mapped[int] = mapped_column(
    ForeignKey("household_members.id", ondelete="CASCADE"),
    index=True,
  )
  label: Mapped[str] = mapped_column(String(120))

  member: Mapped[HouseholdMember] = relationship(back_populates="preferences")


class MealPlan(Base):
  __tablename__ = "meal_plans"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  household_id: Mapped[int] = mapped_column(
    ForeignKey("households.id", ondelete="CASCADE"), index=True
  )
  week_start: Mapped[Date] = mapped_column(Date, index=True)
  session_id: Mapped[str] = mapped_column(String(120), unique=True)
  eco_friendly: Mapped[bool] = mapped_column(Boolean, default=False)
  use_leftovers: Mapped[bool] = mapped_column(Boolean, default=False)
  notes: Mapped[str | None] = mapped_column(Text)
  timeline: Mapped[dict | list | None] = mapped_column(JSON)
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), server_default=func.now()
  )

  household: Mapped[Household] = relationship(back_populates="meal_plans")
  entries: Mapped[List["MealPlanEntry"]] = relationship(
    back_populates="plan",
    cascade="all, delete-orphan",
    passive_deletes=True,
  )


class MealPlanEntry(Base):
  __tablename__ = "meal_plan_entries"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  plan_id: Mapped[int] = mapped_column(
    ForeignKey("meal_plans.id", ondelete="CASCADE"), index=True
  )
  day: Mapped[Date] = mapped_column(Date, index=True)
  slot: Mapped[str] = mapped_column(String(40))
  title: Mapped[str | None] = mapped_column(String(200))
  summary: Mapped[str | None] = mapped_column(Text)
  ingredients: Mapped[list | None] = mapped_column(JSON)
  steps: Mapped[list | None] = mapped_column(JSON)
  prep_minutes: Mapped[int | None] = mapped_column(Integer)
  cook_minutes: Mapped[int | None] = mapped_column(Integer)
  calories_per_person: Mapped[int | None] = mapped_column(Integer)
  attendee_ids: Mapped[list | None] = mapped_column(JSON)
  guest_count: Mapped[int] = mapped_column(Integer, default=0)

  plan: Mapped[MealPlan] = relationship(back_populates="entries")


class KitchenTool(Base):
  __tablename__ = "kitchen_tools"

  id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
  household_id: Mapped[int] = mapped_column(
    ForeignKey("households.id", ondelete="CASCADE"), index=True
  )
  label: Mapped[str] = mapped_column(String(120))
  category: Mapped[str | None] = mapped_column(String(80))
  quantity: Mapped[int] = mapped_column(Integer, default=0)

  household: Mapped[Household] = relationship(back_populates="kitchen_tools")
