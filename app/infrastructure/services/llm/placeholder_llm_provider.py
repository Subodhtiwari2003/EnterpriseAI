from datetime import datetime, timezone
from uuid import uuid4
from collections.abc import Sequence

from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.models.chat import ChatMessage, ChatReply
from app.domain.models.message_model import Message


class PlaceholderLLMProvider(LLMProvider):
    def __init__(self, chat_id: str = "enterprise_ai") -> None:
        self.chat_id = chat_id

    async def generate_chat_reply(
        self,
        message: ChatMessage,
        request_id: str,
        history: Sequence[Message] = (),
    ) -> ChatReply:
        return ChatReply(
            id=str(uuid4()),
            message_id=message.id,
            chat_id=self.chat_id,
            content=(
                f"Echo from Chat: '{message.content}' "
                f"(Request ID: {request_id})"
            ),
            timestamp=datetime.now(timezone.utc),
            evaluation_score=None,
            conversation_id=message.conversation_id,
        )
