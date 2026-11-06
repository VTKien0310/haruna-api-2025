from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from app.core import AppException, error_response
from app.features.auth.guards import AuthenticatedGuardDep
from app.features.media.data import FindMediaByIdReaderDep
from app.features.media.requests import CreateThumbnailRequest
from app.features.media.responses import CreateThumbnailResponse
from app.features.media.services import CreateMediaThumbnailService

router = APIRouter(
    prefix="/medias", tags=["medias"], dependencies=[AuthenticatedGuardDep]
)


@router.post(
    "/videos",
    summary="POST /api/medias/videos",
    description=(
        "Reserved for creating a video media record. The handler is not implemented and returns no body.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Responses:\n"
        "- 200: empty body\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
    ),
)
async def create_video_media() -> None:
    pass


@router.post(
    "/{media_id}/thumbnails",
    summary="POST /api/medias/{media_id}/thumbnails",
    description=(
        "Return a short-lived signed URL for a JPEG thumbnail of the media. "
        "The URL grants temporary read access to the resized object.\n\n"
        "Auth: bearer token via AuthenticatedGuardDep.\n\n"
        "Path: media_id selects the media. Body: width and height in pixels, both greater than 0. "
        "An existing thumbnail of that size is reused; otherwise one is generated.\n\n"
        "Responses:\n"
        "- 200: thumbnail_signed_url\n"
        "- 401: unauthorized when the bearer token is missing or rejected\n"
        "- 404: media_not_found when no media has that id\n"
        "- 422: validation_error when width or height is missing or not a positive integer\n"
    ),
    responses={
        status.HTTP_404_NOT_FOUND: error_response(
            "No media exists for media_id (media_not_found).",
            "media_not_found",
        ),
    },
)
async def create_thumbnail(
    media_id: Annotated[str, Path(description="ID of the media file")],
    request: CreateThumbnailRequest,
    find_reader: FindMediaByIdReaderDep,
    create_thumbnail_service: Annotated[CreateMediaThumbnailService, Depends()],
) -> CreateThumbnailResponse:
    media = find_reader.handle(media_id)
    if media is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="media_not_found",
            message=f"Media with ID '{media_id}' not found",
        )

    return CreateThumbnailResponse(
        thumbnail_signed_url=create_thumbnail_service.handle(
            media, request.width, request.height
        )
    )
