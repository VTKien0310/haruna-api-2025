from fastapi import Request, HTTPException, status, FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.responses import PlainTextResponse

from .logging import get_logger

_logger = get_logger("error")


async def _http_exception_handler(request: Request, exc: HTTPException):
    error_code = {
        status.HTTP_401_UNAUTHORIZED: "unauthorized",
        status.HTTP_403_FORBIDDEN: "forbidden",
        status.HTTP_404_NOT_FOUND: "not_found",
        status.HTTP_409_CONFLICT: "conflict",
        status.HTTP_500_INTERNAL_SERVER_ERROR: "internal_server_error",
    }

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": error_code.get(exc.status_code, "unknown_error"),
                "message": exc.detail,
                "path": request.url.path,
            }
        },
    )


class AppException(HTTPException):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(status_code=status_code, detail=message)
        self.code = code


async def _app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.detail,
                "path": request.url.path,
            }
        },
    )


async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    error_details = list(
        map(
            lambda e: {"loc": e["loc"][-1], "msg": e["msg"], "type": e["type"]},
            exc.errors(),
        )
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "error": {
                "code": "validation_error",
                "message": "Invalid request body",
                "details": error_details,
                "path": request.url.path,
            }
        },
    )


async def _unhandled_exception_handler(
    request: Request, exc: Exception
) -> PlainTextResponse:
    # Starlette uses the Exception handler as the outermost server-error
    # handler. Return the same plain-text 500 it would send on its own.
    _logger.error(
        "unhandled exception method=%s path=%s error=%s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc_info=exc,
    )
    return PlainTextResponse("Internal Server Error", status_code=500)


def register_error_handlers(app: FastAPI):
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
