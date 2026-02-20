from typing import Annotated
from fastapi import APIRouter, HTTPException, Path, Depends

from app.features.auth.guards import AuthenticatedGuardDep
from app.features.media.entities import MediaRepository
from app.features.media.requests import CreateThumbnailRequest
from app.features.media.services import CreateMediaThumbnailService

router = APIRouter(
    prefix="/medias", tags=["thumbnails"], dependencies=[AuthenticatedGuardDep]
)


@router.post("/{media_id}/thumbnails")
async def create_thumbnail(
    media_id: Annotated[
        str, Path(title="ID of the media file to create a thumbnail from")
    ],
    request: CreateThumbnailRequest,
    media_repo: Annotated[MediaRepository, Depends()],
    create_thumbnail_service: Annotated[CreateMediaThumbnailService, Depends()],
):
    media = media_repo.find_by_id(media_id)
    if media is None:
        raise HTTPException(
            status_code=404, detail=f"Media with ID '{media_id}' not found"
        )

    return {
        "thumbnail_signed_url": create_thumbnail_service.handle(
            media, request.width, request.height
        )
    }
