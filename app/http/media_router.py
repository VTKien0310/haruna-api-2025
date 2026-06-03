from typing import Annotated
from fastapi import APIRouter, Path, Depends, status

from app.core import AppException
from app.features.auth.guards import AuthenticatedGuardDep
from app.features.media.data import FindMediaByIdReaderDep
from app.features.media.requests import CreateThumbnailRequest
from app.features.media.services import CreateMediaThumbnailService

router = APIRouter(
    prefix="/medias", tags=["medias"], dependencies=[AuthenticatedGuardDep]
)


@router.post("/videos")
async def create_video_media():
    pass


@router.post("/{media_id}/thumbnails")
async def create_thumbnail(
    media_id: Annotated[
        str, Path(title="ID of the media file to create a thumbnail from")
    ],
    request: CreateThumbnailRequest,
    find_reader: FindMediaByIdReaderDep,
    create_thumbnail_service: Annotated[CreateMediaThumbnailService, Depends()],
):
    media = find_reader.handle(media_id)
    if media is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            code="media_not_found",
            message=f"Media with ID '{media_id}' not found",
        )

    return {
        "thumbnail_signed_url": create_thumbnail_service.handle(
            media, request.width, request.height
        )
    }
