from typing import List

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from .config import settings


def bootstrap_application(router_registry: List[APIRouter]) -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.APP_ENABLE_DOCS else None,
        redoc_url="/redoc" if settings.APP_ENABLE_DOCS else None,
        openapi_url="/openapi.json" if settings.APP_ENABLE_DOCS else None,
    )

    load_routes(app, router_registry)
    config_cors(app)

    return app


def config_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.API_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def load_routes(app: FastAPI, router_registry: List[APIRouter]) -> None:
    for router in router_registry:
        app.include_router(router, prefix=settings.API_PREFIX)
