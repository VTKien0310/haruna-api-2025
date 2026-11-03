from app.http.media_router import router as media_router
from app.http.pto_router import router as pto_router
from app.http.translation_router import router as translation_router

router_registry = [
    media_router,
    pto_router,
    translation_router,
]
