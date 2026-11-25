import logging
import re
from functools import lru_cache
from typing import Annotated

import httpx
from fastapi import Depends
from supabase import Client, create_client

from app.core import get_logger, logger_dependency, settings

_QUERY = re.compile(r"\?\S*")


@lru_cache()
def _get_supabase_client() -> Client:
    """Create and cache a single Supabase client instance."""
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )


def _log_supabase_http_failure(response: httpx.Response) -> None:
    try:
        if response.status_code < 400:
            return
        get_logger("supabase").warning(
            "supabase request failed method=%s url=%s status=%s",
            response.request.method,
            _QUERY.sub("", str(response.request.url)),
            response.status_code,
        )
    except Exception:
        return


def _watch_http_client(http_client: object) -> None:
    hooks = getattr(http_client, "event_hooks", None)
    if not isinstance(hooks, dict):
        return
    response_hooks = hooks.setdefault("response", [])
    if not isinstance(response_hooks, list):
        return
    if _log_supabase_http_failure not in response_hooks:
        response_hooks.append(_log_supabase_http_failure)


class SupabasePort:
    def __init__(
        self, logger: Annotated[logging.Logger, Depends(logger_dependency("supabase"))]
    ) -> None:
        # The httpx hook below cannot see this instance. It logs with
        # get_logger("supabase"), the same logger this dependency provides.
        self.__logger = logger
        self.__client = _get_supabase_client()
        self.__watch_external_calls()

    def storage_media(self):
        bucket = self.__client.storage.from_("medias")
        self.__watch_external_calls()
        return bucket

    def storage_resized(self):
        bucket = self.__client.storage.from_("resized")
        self.__watch_external_calls()
        return bucket

    def storage_thumbnails(self):
        bucket = self.__client.storage.from_("thumbnails")
        self.__watch_external_calls()
        return bucket

    def table_media(self):
        table = self.__client.table("medias")
        self.__watch_external_calls()
        return table

    def table_translation_history(self):
        table = self.__client.table("translation_histories")
        self.__watch_external_calls()
        return table

    def table_profile(self):
        table = self.__client.table("profiles")
        self.__watch_external_calls()
        return table

    def table_pto_bank(self):
        table = self.__client.table("pto_banks")
        self.__watch_external_calls()
        return table

    def auth(self):
        auth = self.__client.auth
        self.__watch_external_calls()
        return auth

    def __watch_external_calls(self) -> None:
        client = self.__client
        _watch_http_client(getattr(client.auth, "_http_client", None))
        postgrest = getattr(client, "_postgrest", None)
        if postgrest is not None:
            _watch_http_client(getattr(postgrest, "session", None))
        storage = getattr(client, "_storage", None)
        if storage is not None:
            _watch_http_client(getattr(storage, "session", None))


SupabasePortDep = Annotated[SupabasePort, Depends()]
