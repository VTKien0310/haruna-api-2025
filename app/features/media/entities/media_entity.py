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
            id=str(data["id"]),
            name=str(data["name"]),
            type=MediaType(data["type"]),
            storage_path=str(data["storage_path"]),
            thumbnail_path=str(data["thumbnail_path"])
            if data["thumbnail_path"]
            else None,
        )

    @property
    def is_video(self) -> bool:
        return self.type == MediaType.VIDEO

    @property
    def is_image(self) -> bool:
        return self.type == MediaType.IMAGE
