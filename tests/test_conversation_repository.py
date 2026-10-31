import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.interfaces.application_error import ApplicationError
from app.infrastructure.database import Database
from app.infrastructure.repositories.conversation_repository import (
    ConversationRepository,
)
from app.infrastructure.orm.models import Base
from app.domain.models.message_model import Message


def test_conversation_repository_persists_and_scopes_history(tmp_path) -> None:
    async def run_test() -> None:
        database_file = tmp_path / "conversations.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{database_file}")
        database = Database(engine)
        repository = ConversationRepository(
            async_sessionmaker(engine, expire_on_commit=False)
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        try:
            conversation_id = await repository.create_conversation("user-1")
            message = Message(
                id="message-1",
                conversation_id=conversation_id,
                owner_id="user-1",
                role="user",
                content="Persist this",
                timestamp=datetime.now(timezone.utc),
            )
            await repository.save_message(message)

            history = await repository.get_history(conversation_id, "user-1")

            assert len(history) == 1
            assert history[0].id == message.id
            assert history[0].content == message.content
            assert history[0].role == message.role

            with pytest.raises(ApplicationError) as error:
                await repository.get_history(conversation_id, "different-owner")
            assert error.value.status_code == 404

            with pytest.raises(ApplicationError) as error:
                await repository.save_message(
                    message.model_copy(update={"owner_id": "different-owner"})
                )
            assert error.value.status_code == 404
        finally:
            await database.close()

    asyncio.run(run_test())
