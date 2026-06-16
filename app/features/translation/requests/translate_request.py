from pydantic import BaseModel, Field


class TranslateRequest(BaseModel):
    source_text: str = Field(..., min_length=1, description="Text to translate")
    source_language: str = Field(..., min_length=2, description="Source language code")
    target_language: str = Field(..., min_length=2, description="Target language code")
