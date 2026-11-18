from pydantic import BaseModel, Field


class CreateThumbnailResponse(BaseModel):
    thumbnail_signed_url: str = Field(
        ...,
        description="Short-lived signed URL for the generated JPEG thumbnail",
        examples=["https://example.com/storage/v1/object/sign/resized/100x100.jpeg"],
    )
