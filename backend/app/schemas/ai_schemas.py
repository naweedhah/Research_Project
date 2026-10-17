from typing import Optional

from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)

    district: Optional[str] = None
    year: Optional[int] = Field(default=None, ge=2026, le=2030)
    month: Optional[int] = Field(default=None, ge=1, le=12)


class AIChatResponse(BaseModel):
    answer: str
    intent: str
    district: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None