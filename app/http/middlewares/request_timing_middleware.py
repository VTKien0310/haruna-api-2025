import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core import get_logger

_logger = get_logger("request")


class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            self.__log_request(request, 500, self.__elapsed_ms(started))
            raise

        elapsed_ms = self.__elapsed_ms(started)
        response.headers["X-Process-Time"] = f"{elapsed_ms / 1000:.6f}"
        self.__log_request(request, response.status_code, elapsed_ms)
        return response

    @classmethod
    def __elapsed_ms(cls, started: float) -> float:
        return (time.perf_counter() - started) * 1000

    @classmethod
    def __log_request(
        cls, request: Request, status_code: int, elapsed_ms: float
    ) -> None:
        _logger.info(
            "request method=%s path=%s status=%s duration_ms=%.1f",
            request.method,
            request.url.path,
            status_code,
            elapsed_ms,
        )
