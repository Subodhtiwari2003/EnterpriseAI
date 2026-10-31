from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Message(BaseModel):
    id: str
    conversation_id: str
    owner_id: str
    role: Literal["user", "assistant"]
    content: str
    timestamp: datetime
