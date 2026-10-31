from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.domain.models.chat import ChatMessage, ChatReply
from app.domain.models.message_model import Message


class LLMProvider(ABC):
    @abstractmethod
    async def generate_chat_reply(
        self, message: ChatMessage, request_id: str, history: Sequence[Message]
    ) -> ChatReply:
        raise NotImplementedError

    async def close(self) -> None:
        return None
