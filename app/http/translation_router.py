from typing import Annotated
from fastapi import APIRouter, Depends
from app.features.auth.guards import AuthenticatedGuardDep, CurrentAuthenticatedUserDep
from app.features.translation.entities import Language
from app.features.translation.requests import TranslateRequest
from app.features.translation.services import (
    TranslateService,
    ListLanguagesServiceDep,
)

router = APIRouter(
    prefix="/translation", tags=["translation"], dependencies=[AuthenticatedGuardDep]
)


@router.post("/translate")
async def translate(
    request: TranslateRequest,
    user: CurrentAuthenticatedUserDep,
    translate_service: Annotated[TranslateService, Depends()],
) -> None:
    await translate_service.handle(
        user=user,
        source_text=request.source_text,
        source_language=request.source_language,
        target_language=request.target_language,
    )


@router.get("/languages")
async def get_languages(
    languages_service: ListLanguagesServiceDep,
) -> list[Language]:
    return languages_service.handle()
