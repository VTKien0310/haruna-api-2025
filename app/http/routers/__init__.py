from .attendance_router import router as attendance_router
from .health_router import router as health_router
from .media_router import router as media_router
from .pto_router import router as pto_router
from .translation_router import router as translation_router

__all__ = [
    "api_router_registry",
    "app_router_registry",
]

api_router_registry = [
    attendance_router,
    media_router,
    pto_router,
    translation_router,
]

app_router_registry = [health_router]
