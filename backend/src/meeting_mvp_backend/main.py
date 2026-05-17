import asyncio
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Annotated, cast
from uuid import UUID

import structlog
from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    WebSocket,
    status,
)
from pydantic import BaseModel, ConfigDict

from meeting_mvp_backend.anonymous_clients import (
    AnonymousClientInitialization,
    AnonymousClientService,
)
from meeting_mvp_backend.archives import (
    ArchiveAccessDenied,
    ArchiveEventRequest,
    ArchiveKeySentenceUpdateRequest,
    ArchiveResponse,
    ArchiveSegmentResponse,
    ArchiveService,
    SQLAlchemyArchiveRepository,
)
from meeting_mvp_backend.config import AppEnv, Settings, load_settings, settings_status
from meeting_mvp_backend.db.session import create_engine, create_session_factory
from meeting_mvp_backend.exports import (
    ArchiveExportConfigurationError,
    ArchiveExportEmpty,
    ArchiveExportRequest,
    ArchiveExportResponse,
    ArchiveExportService,
    ArchiveExportUnavailable,
    SQLAlchemyExportFileRepository,
    create_tencent_cos_storage_from_settings,
)
from meeting_mvp_backend.quota import create_quota_service_from_settings
from meeting_mvp_backend.stt_providers import (
    create_qwen_realtime_asr_provider_from_settings,
)
from meeting_mvp_backend.translation_providers import (
    create_qwen_final_translation_provider_from_settings,
    create_qwen_interim_translation_provider_from_settings,
)
from meeting_mvp_backend.translation_retries import (
    SQLAlchemyTranslationRetryRepository,
    TranslationRetryProcessor,
    TranslationRetryWorker,
    create_redis_translation_retry_queue_from_settings,
)
from meeting_mvp_backend.usage_dashboard import (
    SQLAlchemyUsageDashboardRepository,
    UsageDashboardResponse,
    UsageDashboardService,
)
from meeting_mvp_backend.usage_events import SQLAlchemyUsageEventRecorder
from meeting_mvp_backend.ws_sessions import (
    SQLAlchemyMeetingSessionRepository,
    WebSocketSessionOrchestrator,
)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = load_settings()
    app.state.settings = settings
    if settings.database_url:
        engine = create_engine(settings.database_url)
        app.state.db_engine = engine
        app.state.db_session_factory = create_session_factory(engine)
    if _should_start_translation_retry_worker(settings) and hasattr(
        app.state,
        "db_session_factory",
    ):
        retry_queue = create_redis_translation_retry_queue_from_settings(settings)
        app.state.translation_retry_queue = retry_queue
        retry_processor = TranslationRetryProcessor(
            final_translation_provider_factory=(
                lambda: create_qwen_final_translation_provider_from_settings(settings)
            ),
            queue=retry_queue,
            repository=SQLAlchemyTranslationRetryRepository(
                app.state.db_session_factory,
            ),
            usage_event_recorder=SQLAlchemyUsageEventRecorder(
                session_factory=app.state.db_session_factory,
            ),
        )
        retry_worker = TranslationRetryWorker(
            processor=retry_processor,
            queue=retry_queue,
        )
        app.state.translation_retry_worker_task = asyncio.create_task(
            retry_worker.run_forever(),
        )
    logger.info("settings_loaded", settings=settings_status(settings))
    try:
        yield
    finally:
        if hasattr(app.state, "translation_retry_worker_task"):
            retry_task = app.state.translation_retry_worker_task
            retry_task.cancel()
            with suppress(asyncio.CancelledError):
                await retry_task
        if hasattr(app.state, "translation_retry_queue"):
            await app.state.translation_retry_queue.close()
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
        usage_event_recorder=SQLAlchemyUsageEventRecorder(
            session_factory=request.app.state.db_session_factory,
        ),
    )


def get_archive_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ArchiveService:
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is required to view archives",
        )

    if not hasattr(request.app.state, "db_session_factory"):
        engine = create_engine(settings.database_url)
        request.app.state.db_engine = engine
        request.app.state.db_session_factory = create_session_factory(engine)

    return ArchiveService(
        repository=SQLAlchemyArchiveRepository(
            request.app.state.db_session_factory,
        ),
        usage_event_recorder=SQLAlchemyUsageEventRecorder(
            session_factory=request.app.state.db_session_factory,
        ),
    )


def get_archive_export_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> ArchiveExportService:
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is required to export archives",
        )

    if not hasattr(request.app.state, "db_session_factory"):
        engine = create_engine(settings.database_url)
        request.app.state.db_engine = engine
        request.app.state.db_session_factory = create_session_factory(engine)

    try:
        storage = create_tencent_cos_storage_from_settings(settings)
    except ArchiveExportConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Archive export storage is not configured",
        ) from exc

    return ArchiveExportService(
        archive_repository=SQLAlchemyArchiveRepository(
            request.app.state.db_session_factory,
        ),
        export_prefix=settings.tencent_cos_export_prefix or "exports/",
        export_repository=SQLAlchemyExportFileRepository(
            request.app.state.db_session_factory,
        ),
        signed_url_ttl_seconds=settings.cos_signed_url_ttl_seconds,
        storage=storage,
        usage_event_recorder=SQLAlchemyUsageEventRecorder(
            session_factory=request.app.state.db_session_factory,
        ),
    )


def authorize_usage_dashboard_admin(
    settings: Annotated[Settings, Depends(get_app_settings)],
    authorization: str | None = Header(default=None),
) -> None:
    admin_token = settings.dashboard_admin_token
    if admin_token is None or admin_token.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Usage dashboard is not configured",
        )
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard admin token",
        )
    provided_token = authorization.removeprefix("Bearer ").strip()
    if provided_token == "" or not secrets.compare_digest(
        provided_token,
        admin_token,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid dashboard admin token",
        )


def get_usage_dashboard_service(
    request: Request,
    settings: Annotated[Settings, Depends(get_app_settings)],
) -> UsageDashboardService:
    if (
        settings.dashboard_admin_token is None
        or settings.dashboard_admin_token.strip() == ""
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Usage dashboard is not configured",
        )
    if not settings.database_url:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URL is required to view usage dashboard",
        )

    if not hasattr(request.app.state, "db_session_factory"):
        engine = create_engine(settings.database_url)
        request.app.state.db_engine = engine
        request.app.state.db_session_factory = create_session_factory(engine)

    return UsageDashboardService(
        repository=SQLAlchemyUsageDashboardRepository(
            request.app.state.db_session_factory,
        ),
        settings=settings,
    )


def get_websocket_settings(websocket: WebSocket) -> Settings:
    if hasattr(websocket.app.state, "settings"):
        return cast(Settings, websocket.app.state.settings)
    settings = load_settings()
    websocket.app.state.settings = settings
    return settings


def get_websocket_session_orchestrator(
    websocket: WebSocket,
) -> WebSocketSessionOrchestrator:
    settings = get_websocket_settings(websocket)
    missing_configuration: list[str] = []
    if not settings.database_url:
        missing_configuration.append("DATABASE_URL")
    if not settings.redis_url:
        missing_configuration.append("REDIS_URL")

    if missing_configuration:
        return WebSocketSessionOrchestrator(
            repository=None,
            quota_service=None,
            settings=settings,
            configuration_error=(
                "Missing required configuration: "
                + ", ".join(sorted(missing_configuration))
            ),
        )

    database_url = settings.database_url
    assert database_url is not None
    if not hasattr(websocket.app.state, "db_session_factory"):
        engine = create_engine(database_url)
        websocket.app.state.db_engine = engine
        websocket.app.state.db_session_factory = create_session_factory(engine)

    return WebSocketSessionOrchestrator(
        repository=SQLAlchemyMeetingSessionRepository(
            websocket.app.state.db_session_factory,
        ),
        quota_service=create_quota_service_from_settings(settings),
        settings=settings,
        stt_provider_factory=(
            None
            if settings.app_env is AppEnv.LOCAL
            else lambda: create_qwen_realtime_asr_provider_from_settings(settings)
        ),
        final_translation_provider_factory=(
            None
            if settings.app_env is AppEnv.LOCAL
            else lambda: create_qwen_final_translation_provider_from_settings(settings)
        ),
        translation_retry_queue=getattr(
            websocket.app.state,
            "translation_retry_queue",
            None,
        ),
        translation_provider_factory=(
            (lambda: create_qwen_interim_translation_provider_from_settings(settings))
            if settings.app_env is not AppEnv.LOCAL and settings.qwen_interim_enabled
            else None
        ),
        usage_event_recorder=SQLAlchemyUsageEventRecorder(
            session_factory=websocket.app.state.db_session_factory,
        ),
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


@app.get("/api/archives/{session_id}")
async def view_archive(
    session_id: UUID,
    service: Annotated[ArchiveService, Depends(get_archive_service)],
    token: str | None = Query(default=None),
) -> ArchiveResponse:
    if token is None or token.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Archive token is required",
        )
    try:
        return await service.view_archive(session_id=session_id, token=token)
    except ArchiveAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive not found or expired",
        ) from exc


@app.post(
    "/api/archives/{session_id}/events",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def record_archive_event(
    session_id: UUID,
    event: ArchiveEventRequest,
    service: Annotated[ArchiveService, Depends(get_archive_service)],
    token: str | None = Query(default=None),
) -> Response:
    if token is None or token.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Archive token is required",
        )
    try:
        await service.record_archive_event(
            session_id=session_id,
            token=token,
            event=event,
        )
    except ArchiveAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive not found or expired",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.patch("/api/archives/{session_id}/segments/{segment_id}/key-sentence")
async def update_archive_segment_key_sentence(
    session_id: UUID,
    segment_id: UUID,
    payload: ArchiveKeySentenceUpdateRequest,
    service: Annotated[ArchiveService, Depends(get_archive_service)],
    token: str | None = Query(default=None),
) -> ArchiveSegmentResponse:
    if token is None or token.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Archive token is required",
        )
    try:
        return await service.set_segment_key_sentence(
            session_id=session_id,
            segment_id=segment_id,
            token=token,
            request=payload,
        )
    except ArchiveAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive not found or expired",
        ) from exc


@app.post(
    "/api/archives/{session_id}/exports",
    status_code=status.HTTP_201_CREATED,
)
async def create_archive_export(
    session_id: UUID,
    payload: ArchiveExportRequest,
    service: Annotated[ArchiveExportService, Depends(get_archive_export_service)],
    token: str | None = Query(default=None),
) -> ArchiveExportResponse:
    if token is None or token.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Archive token is required",
        )
    try:
        return await service.create_export(
            request=payload,
            session_id=session_id,
            token=token,
        )
    except ArchiveAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archive not found or expired",
        ) from exc
    except ArchiveExportEmpty as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Archive has no exportable final segments",
        ) from exc
    except ArchiveExportUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Archive export is temporarily unavailable",
        ) from exc


@app.get("/api/admin/usage-dashboard")
async def view_usage_dashboard(
    _admin: Annotated[None, Depends(authorize_usage_dashboard_admin)],
    service: Annotated[
        UsageDashboardService,
        Depends(get_usage_dashboard_service),
    ],
    days: int = Query(default=30, ge=1, le=90),
) -> UsageDashboardResponse:
    return await service.build_dashboard(days=days)


@app.websocket("/ws")
async def websocket_session_endpoint(
    websocket: WebSocket,
    orchestrator: Annotated[
        WebSocketSessionOrchestrator,
        Depends(get_websocket_session_orchestrator),
    ],
) -> None:
    await orchestrator.handle(websocket)


def _should_start_translation_retry_worker(settings: Settings) -> bool:
    return (
        settings.app_env is not AppEnv.LOCAL
        and settings.database_url is not None
        and settings.redis_url is not None
        and settings.qwen_api_key is not None
        and settings.qwen_api_key.strip() != ""
        and settings.qwen_base_url is not None
        and settings.qwen_base_url.strip() != ""
        and settings.qwen_final_model.strip() != ""
    )
