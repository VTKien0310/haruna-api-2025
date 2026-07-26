from dataclasses import dataclass


@dataclass
class TranslationHistory:
    id: str
    owner_id: str
    source_language: str
    target_language: str
    source_text: str
    translation: str
    created_at: str

    @classmethod
    def from_spb_data(cls, data: dict[str, str | int]) -> TranslationHistory:
        return cls(
            id=str(data["id"]),
            owner_id=str(data["owner_id"]),
            source_language=str(data["source_language"]),
            target_language=str(data["target_language"]),
            source_text=str(data["source_text"]),
            translation=str(data["translation"]),
            created_at=str(data["created_at"]),
        )
