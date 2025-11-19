from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import PlanningJob, PlanningJobEvent


async def create_job(
  db: AsyncSession,
  *,
  household_id: int,
  week_start,
  eco_friendly: bool,
  use_leftovers: bool,
  notes: Optional[str],
) -> PlanningJob:
  job = PlanningJob(
    household_id=household_id,
    week_start=week_start,
    eco_friendly=eco_friendly,
    use_leftovers=use_leftovers,
    notes=notes,
    status="pending",
  )
  db.add(job)
  await db.commit()
  await db.refresh(job)
  return job


async def get_job(db: AsyncSession, job_id: int) -> PlanningJob | None:
  result = await db.execute(select(PlanningJob).where(PlanningJob.id == job_id))
  return result.scalar_one_or_none()


async def mark_job_started(db: AsyncSession, job_id: int) -> None:
  job = await get_job(db, job_id)
  if job is None:
    return
  job.status = "running"
  job.started_at = datetime.utcnow()
  await db.commit()


async def mark_job_completed(db: AsyncSession, job_id: int, *, plan_id: int) -> None:
  job = await get_job(db, job_id)
  if job is None:
    return
  job.status = "completed"
  job.plan_id = plan_id
  job.completed_at = datetime.utcnow()
  await db.commit()


async def mark_job_failed(db: AsyncSession, job_id: int, *, error: str) -> None:
  job = await get_job(db, job_id)
  if job is None:
    return
  job.status = "failed"
  job.completed_at = datetime.utcnow()
  await db.commit()
  await add_event(db, job_id, stage="error", message=error)


async def cancel_job(db: AsyncSession, job_id: int, *, reason: str | None = None) -> PlanningJob | None:
  job = await get_job(db, job_id)
  if job is None:
    return None
  if job.status in {"completed", "failed", "cancelled"}:
    return job
  job.status = "cancelled"
  job.completed_at = datetime.utcnow()
  await db.commit()
  await add_event(db, job_id, stage="cancelled", message=reason or "Cancelled")
  return job


async def add_event(
  db: AsyncSession,
  job_id: int,
  *,
  stage: str,
  message: str,
  payload: dict | list | None = None,
) -> PlanningJobEvent:
  event = PlanningJobEvent(job_id=job_id, stage=stage, message=message, payload=payload)
  db.add(event)
  await db.commit()
  await db.refresh(event)
  return event


async def list_events_since(
  db: AsyncSession,
  job_id: int,
  last_event_id: int,
) -> List[PlanningJobEvent]:
  result = await db.execute(
    select(PlanningJobEvent)
    .where(
      PlanningJobEvent.job_id == job_id,
      PlanningJobEvent.id > last_event_id,
    )
    .order_by(PlanningJobEvent.id.asc())
  )
  return result.scalars().all()
