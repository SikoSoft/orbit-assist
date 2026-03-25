from fastapi import APIRouter

from orbit_assist.api.routes.entity import router as entity_router
from orbit_assist.api.routes.entities import router as entities_router
from orbit_assist.api.routes.get_calendar_events import router as calendar_router
from orbit_assist.api.routes.add_calendar_event import router as add_event_router
from orbit_assist.api.routes.health import router as health_router
from orbit_assist.api.routes.jobs import router as jobs_router
from orbit_assist.api.routes.prompt import router as prompt_router

router = APIRouter()
router.include_router(entity_router)
router.include_router(health_router)
router.include_router(calendar_router)
router.include_router(add_event_router)
router.include_router(jobs_router)
router.include_router(prompt_router)
router.include_router(entities_router)
