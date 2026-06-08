from fastapi import APIRouter, Query
from ..models.database import get_stats, get_timeseries_stats

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_statistics():
    return await get_stats()


@router.get("/stats/timeseries")
async def get_timeseries(period: str = Query("day", regex="^(day|week|month)$")):
    data = await get_timeseries_stats(period=period)
    return {"period": period, "data": data}
