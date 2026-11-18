from pydantic import BaseModel
from fastapi import APIRouter


class HealthStatus(BaseModel):
    status: str


router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "",
    summary="GET /health",
    description=(
        "Lightweight liveness check for the API process. Returns 200 with "
        '{"status": "ok"} as long as the service can serve requests. No '
        "authentication is required so that external monitors and platform "
        "probes can reach the endpoint. The global response envelope wraps "
        'the body as {"ok": true, "content": {"status": "ok"}}. '
        "No request body, query string, or path parameters are accepted.\n\n"
        "Responses:\n"
        "- 200: success with status ok"
    ),
)
async def get_health() -> HealthStatus:
    return HealthStatus(status="ok")
