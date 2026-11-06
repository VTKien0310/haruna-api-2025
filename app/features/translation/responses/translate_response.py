from pydantic import BaseModel, Field


class TranslateResponse(BaseModel):
    translated_text: str = Field(
        ..., description="Text translated into the target language"
    )
