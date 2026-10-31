from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.interfaces.application_error import ApplicationError
from app.domain.interfaces.conversation_repo import IConversationRepository
from app.domain.models.message_model import Message
from app.infrastructure.orm.models import ConversationORM, MessageORM


class ConversationRepository(IConversationRepository):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    async def create_conversation(self, owner_id: str) -> str:
        conversation_id = str(uuid4())
        async with self.session_factory() as session:
            session.add(ConversationORM(id=conversation_id, owner_id=owner_id))
            await session.commit()
        return conversation_id

    async def save_message(self, message: Message) -> None:
        async with self.session_factory() as session:
            conversation = await session.get(
                ConversationORM, message.conversation_id
            )
            if conversation is None or conversation.owner_id != message.owner_id:
                raise ApplicationError(
                    "The conversation was not found.",
                    code="conversation_not_found",
                    status_code=404,
                )
            session.add(
                MessageORM(
                    id=message.id,
                    conversation_id=message.conversation_id,
                    owner_id=message.owner_id,
                    role=message.role,
                    content=message.content,
                    timestamp=message.timestamp,
                )
            )
            await session.commit()

    async def get_history(
        self, conversation_id: str, owner_id: str, limit: int = 20
    ) -> list[Message]:
        async with self.session_factory() as session:
            conversation = await session.get(ConversationORM, conversation_id)
            if conversation is None or conversation.owner_id != owner_id:
                raise ApplicationError(
                    "The conversation was not found.",
                    code="conversation_not_found",
                    status_code=404,
                )
            result = await session.scalars(
                select(MessageORM)
                .where(
                    MessageORM.conversation_id == conversation_id,
                    MessageORM.owner_id == owner_id,
                )
                .order_by(MessageORM.timestamp.desc(), MessageORM.id.desc())
                .limit(limit)
            )
            rows = list(result.all())

        return [
            Message(
                id=row.id,
                conversation_id=row.conversation_id,
                owner_id=row.owner_id,
                role=row.role,
                content=row.content,
                timestamp=row.timestamp,
            )
            for row in reversed(rows)
        ]
