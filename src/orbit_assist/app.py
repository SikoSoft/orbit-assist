from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.requests import Request

from orbit_assist.api.router import router as api_router
from orbit_assist.clients.genai import create_genai_client
from orbit_assist.clients.http import create_jobs_client, create_orbit_client
from orbit_assist.core.config import get_settings
from orbit_assist.core.logging import setup_logging
from orbit_assist.db.pool import create_pool

logger = logging.getLogger(__name__)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(
        "Request validation failed for %s %s: %s",
        request.method,
        request.url.path,
        exc.errors(),
    )
    return await request_validation_exception_handler(request, exc)


def create_app() -> FastAPI:
    setup_logging()
    settings = get_settings()
    db_pool = create_pool(settings.database_url)
    logger.info("Creating application with settings: %s", settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.db_pool = db_pool
        app.state.orbit_client = create_orbit_client(settings.base_api_url)
        app.state.jobs_client = create_jobs_client(settings.jobs_api_url)
        app.state.genai_client = create_genai_client(settings.gemini_api_key)

        await db_pool.open()
        yield
        await app.state.orbit_client.aclose()
        await app.state.jobs_client.aclose()
        await db_pool.close()

    app = FastAPI(title=settings.app_title, version=settings.app_version, lifespan=lifespan)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(api_router)
    return app


app = create_app()
