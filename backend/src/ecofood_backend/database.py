from __future__ import annotations

import os
from typing import AsyncGenerator

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


def _build_database_url() -> str:
  raw_url = os.getenv("DATABASE_URL") or "sqlite+aiosqlite:///./ecofood.db"
  if raw_url.startswith("postgres://"):
    return raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
  if raw_url.startswith("postgresql://"):
    return raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
  if raw_url.startswith("sqlite://") and "+aiosqlite" not in raw_url:
    return raw_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
  return raw_url


DATABASE_URL = _build_database_url()


class Base(DeclarativeBase):
  pass


engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
  async with AsyncSessionFactory() as session:
    yield session


async def init_db() -> None:
  from . import models  # noqa: F401 ensures models are registered

  async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
    await conn.run_sync(_ensure_meal_plan_entry_columns)
    await conn.run_sync(_ensure_household_member_columns)


def _ensure_meal_plan_entry_columns(sync_conn) -> None:
  """
  Add newer recipe detail columns to `meal_plan_entries` when running without schema migrations.
  """

  inspector = inspect(sync_conn)
  if "meal_plan_entries" not in inspector.get_table_names():
    return

  existing = {column["name"] for column in inspector.get_columns("meal_plan_entries")}
  dialect = sync_conn.dialect.name

  def add_column(name: str, ddl_postgres: str, ddl_default: str) -> None:
    if name in existing:
      return
    statement = ddl_postgres if dialect == "postgresql" else ddl_default
    sync_conn.execute(text(statement))

  add_column(
    "ingredients",
    "ALTER TABLE meal_plan_entries ADD COLUMN ingredients JSONB",
    "ALTER TABLE meal_plan_entries ADD COLUMN ingredients JSON",
  )
  add_column(
    "steps",
    "ALTER TABLE meal_plan_entries ADD COLUMN steps JSONB",
    "ALTER TABLE meal_plan_entries ADD COLUMN steps JSON",
  )
  add_column(
    "prep_minutes",
    "ALTER TABLE meal_plan_entries ADD COLUMN prep_minutes INTEGER",
    "ALTER TABLE meal_plan_entries ADD COLUMN prep_minutes INTEGER",
  )
  add_column(
    "cook_minutes",
    "ALTER TABLE meal_plan_entries ADD COLUMN cook_minutes INTEGER",
    "ALTER TABLE meal_plan_entries ADD COLUMN cook_minutes INTEGER",
  )
  add_column(
    "calories_per_person",
    "ALTER TABLE meal_plan_entries ADD COLUMN calories_per_person INTEGER",
    "ALTER TABLE meal_plan_entries ADD COLUMN calories_per_person INTEGER",
  )
  add_column(
    "attendee_ids",
    "ALTER TABLE meal_plan_entries ADD COLUMN attendee_ids JSONB",
    "ALTER TABLE meal_plan_entries ADD COLUMN attendee_ids JSON",
  )
  add_column(
    "guest_count",
    "ALTER TABLE meal_plan_entries ADD COLUMN guest_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE meal_plan_entries ADD COLUMN guest_count INTEGER NOT NULL DEFAULT 0",
  )


def _ensure_household_member_columns(sync_conn) -> None:
  inspector = inspect(sync_conn)
  if "household_members" not in inspector.get_table_names():
    return

  existing = {column["name"] for column in inspector.get_columns("household_members")}

  def add_column(name: str) -> None:
    if name in existing:
      return
    sync_conn.execute(
      text(f"ALTER TABLE household_members ADD COLUMN {name} BOOLEAN NOT NULL DEFAULT true")
    )

  add_column("eats_breakfast")
  add_column("eats_lunch")
  add_column("eats_dinner")
  if "meal_schedule" not in existing:
    sync_conn.execute(
      text("ALTER TABLE household_members ADD COLUMN meal_schedule JSON")
    )
