from pydantic import BaseModel, Field


class CreateThumbnailRequest(BaseModel):
    width: int = Field(..., gt=0, description="Thumbnail width (must be > 0)")
    height: int = Field(..., gt=0, description="Thumbnail height (must be > 0)")
