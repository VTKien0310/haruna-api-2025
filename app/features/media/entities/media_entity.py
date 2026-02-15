from app.ports import SupabasePortDep
from dataclasses import dataclass
from enum import IntEnum


class MediaType(IntEnum):
    IMAGE = 0
    VIDEO = 1


@dataclass
class Media:
    id: str
    name: str
    type: MediaType
    storage_path: str
    thumbnail_path: str | None

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> Media:
        return cls(
            id=data["id"],
            name=data["name"],
            type=MediaType(data["type"]),
            storage_path=data["storage_path"],
            thumbnail_path=data.get("thumbnail_path"),
        )

    @property
    def is_video(self) -> bool:
        return self.type == MediaType.VIDEO

    @property
    def is_image(self) -> bool:
        return self.type == MediaType.IMAGE


class MediaRepository:
    def __init__(self, supabase: SupabasePortDep):
        self.__supabase = supabase

    def find_by_id(self, media_id: str) -> Media | None:
        result = (
            self.__supabase.table_media()
            .select()
            .eq("id", media_id)
            .single()
            .execute()
            .data
        )

        if result is None:
            return None

        return Media.from_spb_data(result)
