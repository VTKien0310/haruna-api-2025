from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core import error_response
from app.features.auth.guards import AuthenticatedGuardDep, CurrentAuthenticatedUserDep
from app.features.translation.entities import Language
from app.features.translation.requests import TranslateRequest
from app.features.translation.responses import TranslateResponse
from app.features.translation.services import (
    TranslateService,
    ListLanguagesServiceDep,
)

router = APIRouter(
    prefix="/translation", tags=["translation"], dependencies=[AuthenticatedGuardDep]
)


@router.post(
    "/translate",
    summary="POST /api/translation/translate",
    description=(
        "Translate source text from one supported language into another and store the result "
        "in the caller's history.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Body: source_text, source_language, and target_language. Language codes must be supported "
        "codes from GET /api/translation/languages, and the two languages must differ.\n\n"
        "Responses:\n"
        "- 200: translated_text\n"
        "- 400: invalid_language when source or target is not a supported code; "
        "same_language when they are equal\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 422: validation_error when the body fails validation\n"
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: error_response(
            "Source or target is not a supported language (invalid_language), "
            "or they are the same (same_language).",
            "invalid_language",
            "same_language",
        ),
    },
)
async def translate(
    request: TranslateRequest,
    user: CurrentAuthenticatedUserDep,
    translate_service: Annotated[TranslateService, Depends()],
) -> TranslateResponse:
    translated_text = await translate_service.handle(
        user=user,
        source_text=request.source_text,
        source_language=request.source_language,
        target_language=request.target_language,
    )

    return TranslateResponse(translated_text=translated_text)


@router.get(
    "/languages",
    summary="GET /api/translation/languages",
    description=(
        "List the language codes this API can translate.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Each language has a code and a name. There is no query string or request body.\n\n"
        "Responses:\n"
        "- 200: the supported languages\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
    ),
)
async def get_languages(
    languages_service: ListLanguagesServiceDep,
) -> list[Language]:
    return languages_service.handle()
