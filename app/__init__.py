from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .routes import router_registry


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs_url="/docs" if settings.APP_ENABLE_DOCS else None,
        redoc_url="/redoc" if settings.APP_ENABLE_DOCS else None,
        openapi_url="/openapi.json" if settings.APP_ENABLE_DOCS else None,
    )

    _load_routes(app)

    _configure_cors(app)

    return app


def _load_routes(app: FastAPI) -> None:
    for router in router_registry:
        app.include_router(router, prefix=settings.API_PREFIX)


def _configure_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.API_ALLOW_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
