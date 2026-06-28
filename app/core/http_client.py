import httpx
from typing import Annotated
from fastapi import Request, Depends

app_user_agent = "haruna-api/2025"


def init_basic_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5, read=10, write=10, pool=5),
        limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        headers={"User-Agent": app_user_agent},
    )


def init_long_read_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(connect=5, read=60, write=10, pool=5),
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        headers={"User-Agent": app_user_agent},
    )


def get_basic_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.basic_http_client


def get_long_read_http_client(request: Request) -> httpx.AsyncClient:
    return request.app.state.long_read_http_client


BasicHttpClientDep = Annotated[httpx.AsyncClient, Depends(get_basic_http_client)]
LongReadHttpClientDep = Annotated[httpx.AsyncClient, Depends(get_long_read_http_client)]
