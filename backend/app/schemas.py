"""Pydantic request/response schemas."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str
    system_prompt: str | None = Field(default=None, max_length=4000)

    @field_validator("session_id")
    @classmethod
    def _strip_session_id(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("session_id must not be empty")
        return v

    @field_validator("message")
    @classmethod
    def _validate_message(cls, v: str) -> str:
        v = v.strip()
        if not 1 <= len(v) <= 4000:
            raise ValueError("message must be between 1 and 4000 characters after trimming")
        return v


class ChatMetadata(BaseModel):
    resolution_source: Literal["LIVE_INFERENCE", "LLM_CACHE"]
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    key_id: str | None
    fallback_attempts: int


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    metadata: ChatMetadata


class StoredMessage(BaseModel):
    id: int
    session_id: str
    role: str
    content: str
    metadata: dict | None = None
    created_at: datetime
