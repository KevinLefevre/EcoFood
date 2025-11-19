from __future__ import annotations

import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from fastapi.responses import StreamingResponse

from ..agent.a2a.plan_runner import run_plan_job
from ..database import AsyncSessionFactory, get_session
from ..schemas import PlanningJobCreate, PlanningJobEventResponse, PlanningJobResponse
from ..services import plan_jobs as plan_job_service

router = APIRouter(prefix="/plan-jobs", tags=["plan-jobs"])


@router.post("", response_model=PlanningJobResponse, status_code=202)
async def create_plan_job(
  payload: PlanningJobCreate,
  db=Depends(get_session),
) -> PlanningJobResponse:
  job = await plan_job_service.create_job(
    db,
    household_id=payload.household_id,
    week_start=payload.week_start,
    eco_friendly=payload.eco_friendly,
    use_leftovers=payload.use_leftovers,
    notes=payload.notes,
  )
  asyncio.create_task(run_plan_job(job.id))
  return PlanningJobResponse.model_validate(job)


@router.get("/{job_id}", response_model=PlanningJobResponse)
async def get_plan_job(job_id: int = Path(..., gt=0), db=Depends(get_session)) -> PlanningJobResponse:
  job = await plan_job_service.get_job(db, job_id)
  if job is None:
    raise HTTPException(status_code=404, detail="Planning job not found")
  return PlanningJobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=204)
async def cancel_plan_job(job_id: int = Path(..., gt=0), db=Depends(get_session)) -> Response:
  job = await plan_job_service.get_job(db, job_id)
  if job is None:
    raise HTTPException(status_code=404, detail="Planning job not found")
  if job.status in {"completed", "failed"}:
    raise HTTPException(status_code=409, detail=f"Cannot cancel a {job.status} job")
  await plan_job_service.cancel_job(db, job_id, reason="Cancelled via API")
  return Response(status_code=204)


@router.get("/{job_id}/events/stream")
async def stream_plan_job_events(job_id: int = Path(..., gt=0)) -> StreamingResponse:
  async def event_generator() -> AsyncGenerator[str, None]:
    last_event_id = 0
    terminal = False
    while True:
      async with AsyncSessionFactory() as db:
        job = await plan_job_service.get_job(db, job_id)
        if job is None:
          yield _format_sse({"error": "job_not_found"})
          break
        events = await plan_job_service.list_events_since(db, job_id, last_event_id)
        for event in events:
          payload = PlanningJobEventResponse.model_validate(event)
          last_event_id = event.id
          yield _format_sse(json.loads(payload.json()))
        if job.status in {"completed", "failed", "cancelled"} and not events:
          terminal = True
      if terminal:
        break
      await asyncio.sleep(1)

  return StreamingResponse(event_generator(), media_type="text/event-stream")


def _format_sse(data: dict | str) -> str:
  if isinstance(data, str):
    payload = data
  else:
    payload = json.dumps(data)
  return f"data: {payload}\n\n"
