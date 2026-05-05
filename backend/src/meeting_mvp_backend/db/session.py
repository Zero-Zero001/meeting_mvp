from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from meeting_mvp_backend.config import Settings, SettingsError, get_settings


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


def create_session_factory_from_settings(
    settings: Settings | None = None,
) -> async_sessionmaker[AsyncSession]:
    resolved_settings = settings or get_settings()
    if not resolved_settings.database_url:
        raise SettingsError("DATABASE_URL is required to create database sessions")
    return create_session_factory(create_engine(resolved_settings.database_url))
