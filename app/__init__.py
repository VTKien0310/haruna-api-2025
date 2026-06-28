from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import AsyncGenerator
from .core import (
    bootstrap_application,
    init_basic_http_client,
    init_long_read_http_client,
)
from .http import router_registry


@asynccontextmanager
async def lifespan_handler(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.basic_http_client = init_basic_http_client()
    app.state.long_read_http_client = init_long_read_http_client()

    yield

    await app.state.basic_http_client.aclose()
    await app.state.long_read_http_client.aclose()


def create_app() -> FastAPI:
    return bootstrap_application(router_registry, lifespan_handler=lifespan_handler)
