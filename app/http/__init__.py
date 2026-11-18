from app.http.attendance_router import router as attendance_router
from app.http.health_router import router as health_router
from app.http.media_router import router as media_router
from app.http.pto_router import router as pto_router
from app.http.translation_router import router as translation_router

api_router_registry = [
    attendance_router,
    media_router,
    pto_router,
    translation_router,
]

app_router_registry = [health_router]
