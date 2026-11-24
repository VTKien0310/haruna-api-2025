from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import AsyncGenerator
from .core import (
    bootstrap_application,
    get_logger,
    init_basic_http_client,
    init_long_read_http_client,
    log_startup,
)
from .database import init_db_session_manager
from .http.middlewares import middleware_registry
from .http.routers import api_router_registry, app_router_registry


@asynccontextmanager
async def lifespan_handler(app: FastAPI) -> AsyncGenerator[None, None]:
    try:
        app.state.basic_http_client = init_basic_http_client()
        app.state.long_read_http_client = init_long_read_http_client()
        app.state.db_session_manager = init_db_session_manager()
        log_startup()
    except Exception:
        get_logger("core").exception("startup failed")
        raise

    try:
        yield
    finally:
        await app.state.db_session_manager.dispose()
        await app.state.basic_http_client.aclose()
        await app.state.long_read_http_client.aclose()


def create_app() -> FastAPI:
    return bootstrap_application(
        api_router_registry=api_router_registry,
        middleware_registry=middleware_registry,
        app_router_registry=app_router_registry,
        lifespan_handler=lifespan_handler,
    )
