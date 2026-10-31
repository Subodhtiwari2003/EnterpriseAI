from dataclasses import dataclass
from datetime import datetime


@dataclass
class ChatMessage:
    id: str
    owner_id: str
    content: str
    timestamp: datetime
    conversation_id: str


@dataclass
class ChatReply:
    id: str
    message_id: str
    chat_id: str
    content: str
    timestamp: datetime
    conversation_id: str
    evaluation_score: float | None = None
