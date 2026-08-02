from typing import Annotated

from fastapi import Depends

from app.features.translation.entities import Language


class ListLanguagesService:
    __supported_languages: list[dict[str, str]] = [
        {"code": "ar", "name": "Arabic"},
        {"code": "zh-CN", "name": "Chinese (Simplified)"},
        {"code": "zh-TW", "name": "Chinese (Traditional)"},
        {"code": "cs", "name": "Czech"},
        {"code": "da", "name": "Danish"},
        {"code": "nl", "name": "Dutch"},
        {"code": "en", "name": "English"},
        {"code": "fi", "name": "Finnish"},
        {"code": "fr", "name": "French"},
        {"code": "de", "name": "German"},
        {"code": "el", "name": "Greek"},
        {"code": "he", "name": "Hebrew"},
        {"code": "hi", "name": "Hindi"},
        {"code": "hu", "name": "Hungarian"},
        {"code": "id", "name": "Indonesian"},
        {"code": "it", "name": "Italian"},
        {"code": "ja", "name": "Japanese"},
        {"code": "ko", "name": "Korean"},
        {"code": "ms", "name": "Malay"},
        {"code": "no", "name": "Norwegian"},
        {"code": "pl", "name": "Polish"},
        {"code": "pt", "name": "Portuguese"},
        {"code": "ro", "name": "Romanian"},
        {"code": "ru", "name": "Russian"},
        {"code": "es", "name": "Spanish"},
        {"code": "sv", "name": "Swedish"},
        {"code": "th", "name": "Thai"},
        {"code": "tr", "name": "Turkish"},
        {"code": "vi", "name": "Vietnamese"},
    ]

    def handle(self) -> list[Language]:
        return [Language.from_dict(data) for data in self.__supported_languages]


ListLanguagesServiceDep = Annotated[ListLanguagesService, Depends()]
