from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class ChatMessageRequest(BaseModel):
    content: str = Field(..., description="Message text for the user")
    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        description="Existing conversation to continue",
    )

    model_config = {"extra": "forbid"}

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        content = value.strip()
        if not content:
            raise ValueError("message cannot be empty")
        if len(content) > 500:
            raise ValueError("message cannot exceed 500 characters")
        return content


class ChatMessageResponse(BaseModel):
    id: str
    message_id: str
    conversation_id: str
    chat_id: str = Field(serialization_alias="assistant_id")
    content: str
    timestamp: datetime
    evaluation_score: float | None = None


class ChatHistoryMessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
