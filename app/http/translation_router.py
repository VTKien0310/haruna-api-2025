from typing import Annotated

from fastapi import APIRouter, Depends

from app.features.auth.guards import AuthenticatedGuardDep
from app.features.translation.entities import Language
from app.features.translation.requests import TranslateRequest
from app.features.translation.services import (
    GetTranslationHistoryService,
    ListLanguagesService,
    TranslateService,
)

router = APIRouter(
    prefix="/translation", tags=["translation"], dependencies=[AuthenticatedGuardDep]
)


@router.post("/translate")
async def translate(
    request: TranslateRequest,
    translate_service: Annotated[TranslateService, Depends()],
) -> None:
    pass


@router.get("/histories")
async def get_histories(
    history_service: Annotated[GetTranslationHistoryService, Depends()],
) -> None:
    pass


@router.get("/languages")
async def get_languages(
    languages_service: Annotated[ListLanguagesService, Depends()],
) -> list[Language]:
    return languages_service.handle()
