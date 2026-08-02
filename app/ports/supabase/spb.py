from functools import lru_cache
from supabase import create_client, Client
from app.core import settings
from typing import Annotated
from fastapi import Depends


@lru_cache()
def _get_supabase_client() -> Client:
    """Create and cache a single Supabase client instance."""
    return create_client(
        supabase_url=settings.SUPABASE_URL,
        supabase_key=settings.SUPABASE_SERVICE_ROLE_KEY,
    )


class SupabasePort:
    def __init__(self):
        self.__client = _get_supabase_client()

    def storage_media(self):
        return self.__client.storage.from_("medias")

    def storage_resized(self):
        return self.__client.storage.from_("resized")

    def storage_thumbnails(self):
        return self.__client.storage.from_("thumbnails")

    def table_media(self):
        return self.__client.table("medias")

    def table_translation_history(self):
        return self.__client.table("translation_histories")

    def auth(self):
        return self.__client.auth


SupabasePortDep = Annotated[SupabasePort, Depends()]
