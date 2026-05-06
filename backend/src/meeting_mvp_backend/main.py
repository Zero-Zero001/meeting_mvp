from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated, cast
from uuid import UUID

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict

from meeting_mvp_backend.anonymous_clients import (
    AnonymousClientInitialization,
    AnonymousClientService,
)
from meeting_mvp_backend.config import Settings, load_settings, settings_status
from meeting_mvp_backend.db.session import create_engine, create_session_factory

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    app.state.settings = settings
    if settings.database_url:
        engine = create_engine(settings.database_url)
        app.state.db_engine = engine
        app.state.db_session_factory = create_session_factory(engine)
    logger.info("settings_loaded", settings=settings_status(settings))
    try:
        yield
    finally:
        if hasattr(app.state, "db_engine"):
            await app.state.db_engine.dispose()


app = FastAPI(title="Meeting MVP Backend", lifespan=lifespan)


class AnonymousClientCreateRequest(BaseModel):
    client_id: UUID


class AnonymousClientCreateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: UUID
    daily_free_seconds: int
    remaining_seconds_today: int
    is_new: bool


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


def get_app_settings(request: Request) -> Settings:
    if hasattr(request.app.state, "settings"):
        return cast(Settings, request.app.state.settings)
    settings = load_settings()
    request.app.state.settings = settings
    return settings


def get_anonymous_client_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> AnonymousClientService:
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is required to initialize anonymous clients",
        )

    if not hasattr(request.app.state, "db_session_factory"):
        engine = create_engine(settings.database_url)
        request.app.state.db_engine = engine
        request.app.state.db_session_factory = create_session_factory(engine)

    return AnonymousClientService(
        session_factory=request.app.state.db_session_factory,
        daily_free_seconds=settings.daily_free_seconds,
    )


@app.post("/api/anonymous-clients")
async def initialize_anonymous_client(
    payload: AnonymousClientCreateRequest,
    request: Request,
    service: Annotated[
        AnonymousClientService,
        Depends(get_anonymous_client_service),
    ],
) -> AnonymousClientCreateResponse:
    client_host = request.client.host if request.client else None
    result: AnonymousClientInitialization = await service.initialize_client(
        client_id=payload.client_id,
        ip_address=client_host,
        user_agent=request.headers.get("user-agent"),
    )
    return AnonymousClientCreateResponse.model_validate(result)
