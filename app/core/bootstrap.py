from typing import Callable, List, AsyncContextManager
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from .config import settings
from .error import register_error_handlers
from .logging import apply_log_level_for_application
from .openapi import apply_openapi_schema
from .response import apply_global_response_interface


def bootstrap_application(
    api_router_registry: List[APIRouter],
    middleware_registry: List[type[BaseHTTPMiddleware]],
    lifespan_handler: Callable[[FastAPI], AsyncContextManager[None]] | None = None,
    app_router_registry: List[APIRouter] | None = None,
) -> FastAPI:
    apply_log_level_for_application()
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.APP_ENABLE_DOCS else None,
        redoc_url="/redoc" if settings.APP_ENABLE_DOCS else None,
        openapi_url="/openapi.json" if settings.APP_ENABLE_DOCS else None,
        lifespan=lifespan_handler,
    )

    apply_global_response_interface(app)
    register_error_handlers(app)

    _config_cors(app)
    _load_middlewares(app, middleware_registry)
    _load_routes(app, api_router_registry, app_router_registry)
    apply_openapi_schema(app)

    return app


def _config_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.API_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Process-Time"],
    )


def _load_middlewares(
    app: FastAPI, middleware_registry: List[type[BaseHTTPMiddleware]]
) -> None:
    for middleware in middleware_registry:
        app.add_middleware(middleware)


def _load_routes(
    app: FastAPI,
    api_router_registry: List[APIRouter],
    app_router_registry: List[APIRouter] | None,
) -> None:
    for router in api_router_registry:
        app.include_router(router, prefix=settings.API_PREFIX)
    for router in app_router_registry or []:
        app.include_router(router)
