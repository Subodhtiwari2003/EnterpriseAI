from datetime import datetime, timezone
from uuid import uuid4

from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.interfaces.conversation_repo import IConversationRepository
from app.domain.models.chat import ChatMessage, ChatReply
from app.domain.models.message_model import Message


class SendChatMessage:
    def __init__(
        self,
        llm_provider: LLMProvider,
        conversation_repo: IConversationRepository,
    ) -> None:
        self.llm_provider = llm_provider
        self.conversation_repo = conversation_repo

    async def execute(
        self,
        owner_id: str,
        content: str,
        request_id: str,
        conversation_id: str | None = None,
    ) -> ChatReply:
        if conversation_id is None:
            conversation_id = await self.conversation_repo.create_conversation(owner_id)

        history = await self.conversation_repo.get_history(
            conversation_id=conversation_id,
            owner_id=owner_id,
        )
        message = ChatMessage(
            id=str(uuid4()),
            owner_id=owner_id,
            content=content,
            timestamp=datetime.now(timezone.utc),
            conversation_id=conversation_id,
        )
        await self.conversation_repo.save_message(
            Message(
                id=message.id,
                conversation_id=conversation_id,
                owner_id=owner_id,
                role="user",
                content=content,
                timestamp=message.timestamp,
            )
        )

        reply = await self.llm_provider.generate_chat_reply(
            message,
            request_id,
            history,
        )
        reply.conversation_id = conversation_id
        await self.conversation_repo.save_message(
            Message(
                id=reply.id,
                conversation_id=conversation_id,
                owner_id=owner_id,
                role="assistant",
                content=reply.content,
                timestamp=reply.timestamp,
            )
        )

        return reply

    async def get_history(
        self, conversation_id: str, owner_id: str
    ) -> list[Message]:
        return await self.conversation_repo.get_history(
            conversation_id=conversation_id,
            owner_id=owner_id,
        )
