from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_session as get_db
from ..schemas import StatsResponse
from ..services import meal_plans as meal_plan_service

router = APIRouter(prefix="/households/{household_id}/stats", tags=["stats"])


@router.get("", response_model=StatsResponse)
async def get_stats(
  household_id: int,
  db: AsyncSession = Depends(get_db),
) -> StatsResponse:
  """
  Get aggregated statistics for a household.
  """
  return await meal_plan_service.get_household_stats(db, household_id)


@router.post("/insights", response_model=dict)
async def get_stats_insight(
  household_id: int,
  db: AsyncSession = Depends(get_db),
) -> dict:
  stats = await meal_plan_service.get_household_stats(db, household_id)
  insight = await meal_plan_service.generate_stats_insight(stats)
  return {"insight": insight}
