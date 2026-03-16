import psycopg
from fastapi import APIRouter, Depends

from orbit_assist.db.pool import get_db
from orbit_assist.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(db: psycopg.AsyncConnection = Depends(get_db)) -> HealthResponse:
    await db.execute("SELECT 1")
    return HealthResponse(status="ok")
