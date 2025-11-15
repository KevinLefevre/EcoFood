from __future__ import annotations

import os
from typing import AsyncGenerator

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
