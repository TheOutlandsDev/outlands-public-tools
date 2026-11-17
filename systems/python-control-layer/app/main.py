import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.logging_config import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logging.getLogger(__name__).info(
        "application_started",
        extra={"app_version": settings.app_version},
    )
    yield
    logging.getLogger(__name__).info("application_stopped")


app = FastAPI(
    title="Python Data and Query Control Layer",
    version=get_settings().app_version,
    lifespan=lifespan,
)


@app.get("/health/live", tags=["health"])
def live() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def ready() -> dict[str, str]:
    # Milestone 0 has no mandatory external dependencies yet.
    return {"status": "ready"}
