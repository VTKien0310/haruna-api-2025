import logging
import time

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.request")


class _RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            _log_request(request, 500, _elapsed_ms(started))
            raise

        elapsed_ms = _elapsed_ms(started)
        response.headers["X-Process-Time"] = f"{elapsed_ms / 1000:.6f}"
        _log_request(request, response.status_code, elapsed_ms)
        return response


def apply_request_timing(app: FastAPI) -> None:
    app.add_middleware(_RequestTimingMiddleware)


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000


def _log_request(request: Request, status_code: int, elapsed_ms: float) -> None:
    logger.info(
        "request method=%s path=%s status=%s duration_ms=%.1f",
        request.method,
        request.url.path,
        status_code,
        elapsed_ms,
    )
