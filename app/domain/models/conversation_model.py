from app.domain.models.message_model import Message
from pydantic import BaseModel
from pydantic import Field


class Conversation(BaseModel):
    id: str
    owner_id: str
    messages: list[Message] = Field(default_factory=list)