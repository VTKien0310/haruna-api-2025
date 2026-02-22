import json
from fastapi import Request, FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class WrapResponseMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if "application/json" in response.headers.get("content-type", ""):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            original_data = json.loads(body)
            is_ok = response.status_code < 400
            wrapped = {"ok": is_ok, "content": original_data}

            return JSONResponse(
                content=wrapped,
                status_code=response.status_code,
            )

        return response


def apply_global_response_interface(app: FastAPI) -> None:
    app.add_middleware(WrapResponseMiddleware)
