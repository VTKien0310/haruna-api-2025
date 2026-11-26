from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.core.config import settings


class DbSessionManager:
    def __init__(self, engine: AsyncEngine) -> None:
        self.__engine = engine
        self.__session_maker = async_sessionmaker(
            bind=self.__engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.__session_maker() as session:
            yield session

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.__session_maker() as session:
            async with session.begin():
                yield session

    async def dispose(self) -> None:
        await self.__engine.dispose()


def _get_async_db_url() -> URL:
    return URL.create(
        drivername="postgresql+asyncpg",
        username=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME,
    )


def init_db_session_manager() -> DbSessionManager:
    # server_settings is intentionally omitted. asyncpg sends it as PostgreSQL
    # startup parameters, and Supavisor or PgBouncer in transaction mode rejects
    # untracked ones such as statement_timeout. command_timeout is client-side
    # and still bounds pool_pre_ping on a dead socket. asyncpg also has no
    # connect() argument for TCP keepalives, so those are not set here.
    engine = create_async_engine(
        _get_async_db_url(),
        pool_pre_ping=True,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
        connect_args={
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "timeout": settings.DB_CONNECT_TIMEOUT_SECONDS,
            "command_timeout": settings.DB_COMMAND_TIMEOUT_SECONDS,
        },
    )
    return DbSessionManager(engine)


def get_db_session_manager(request: Request) -> DbSessionManager:
    return request.app.state.db_session_manager


DbSessionManagerDep = Annotated[
    DbSessionManager,
    Depends(get_db_session_manager),
]
