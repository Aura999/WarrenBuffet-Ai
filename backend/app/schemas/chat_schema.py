from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str
    ticker: Optional[str] = None
    document_ids: Optional[list[str]] = None


class ChatResponse(BaseModel):
    success: bool
    query: str
    answer: str
    sources: list[Any] = Field(default_factory=list)
    visuals: Optional[dict[str, Any]] = None
