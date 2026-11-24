from .request_timing_middleware import (
    RequestTimingMiddleware as RequestTimingMiddleware,
)

middleware_registry = [RequestTimingMiddleware]
