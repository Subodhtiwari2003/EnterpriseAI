from abc import ABC, abstractmethod

from app.domain.models.message_model import Message


class IConversationRepository(ABC):
    @abstractmethod
    async def create_conversation(self, owner_id: str) -> str:
        raise NotImplementedError

    @abstractmethod
    async def save_message(self, message: Message) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_history(
        self, conversation_id: str, owner_id: str, limit: int = 20
    ) -> list[Message]:
        raise NotImplementedError
