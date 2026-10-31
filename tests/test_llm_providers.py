import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from app.application.use_cases.send_chat_message import SendChatMessage
from app.config.application_settings import ApplicationSettings
from app.domain.interfaces.conversation_repo import IConversationRepository
from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.models.chat import ChatMessage, ChatReply
from app.domain.models.message_model import Message
from app.infrastructure.services.llm.openai_chat_provider import OpenAIChatProvider
from app.infrastructure.services.llm.placeholder_llm_provider import (
    PlaceholderLLMProvider,
)


class RecordingLLMProvider(LLMProvider):
    def __init__(self) -> None:
        self.received_message: ChatMessage | None = None
        self.received_request_id: str | None = None

    async def generate_chat_reply(
        self, message: ChatMessage, request_id: str, history: list[Message]
    ) -> ChatReply:
        self.received_message = message
        self.received_request_id = request_id
        return ChatReply(
            id="reply-1",
            message_id=message.id,
            chat_id="test-chat",
            content="Provider response",
            timestamp=datetime.now(timezone.utc),
            conversation_id=message.conversation_id,
        )


class RecordingConversationRepository(IConversationRepository):
    def __init__(self) -> None:
        self.conversation_id: str | None = None
        self.saved_messages: list[Message] = []
        self.history: list[Message] = []

    async def create_conversation(self, owner_id: str) -> str:
        self.conversation_id = "conversation-1"
        return self.conversation_id

    async def save_message(self, message: Message) -> None:
        self.saved_messages.append(message)

    async def get_history(
        self, conversation_id: str, owner_id: str, limit: int = 20
    ) -> list[Message]:
        assert conversation_id == self.conversation_id
        return self.history


def test_placeholder_provider_returns_linked_reply() -> None:
    message = ChatMessage(
        id="message-1",
        owner_id="user-1",
        content="Hello",
        timestamp=datetime.now(timezone.utc),
        conversation_id="conversation-1",
    )

    reply = asyncio.run(
        PlaceholderLLMProvider().generate_chat_reply(message, "request-1")
    )

    assert reply.message_id == message.id
    assert reply.chat_id == "enterprise_ai"
    assert "request-1" in reply.content


def test_send_chat_message_uses_llm_provider() -> None:
    llm_provider = RecordingLLMProvider()
    repository = RecordingConversationRepository()
    use_case = SendChatMessage(llm_provider, repository)

    reply = asyncio.run(use_case.execute("user-1", "Hello", "request-2"))

    assert llm_provider.received_message is not None
    assert llm_provider.received_message.owner_id == "user-1"
    assert llm_provider.received_message.content == "Hello"
    assert llm_provider.received_request_id == "request-2"
    assert reply.message_id == llm_provider.received_message.id
    assert reply.content == "Provider response"
    assert reply.conversation_id == "conversation-1"
    assert [message.role for message in repository.saved_messages] == [
        "user",
        "assistant",
    ]


def test_openai_provider_requires_non_empty_api_key() -> None:
    with pytest.raises(ValidationError):
        ApplicationSettings(ai_provider="openai", ai_api_key=" ")


def test_provider_name_is_case_insensitive() -> None:
    settings = ApplicationSettings(ai_provider="PLACEHOLDER")

    assert settings.ai_provider == "placeholder"


def test_openai_provider_normalizes_response_and_forwards_request_id() -> None:
    provider = OpenAIChatProvider(
        api_key="test-key",
        model="test-model",
        timeout_seconds=1,
        max_tokens=50,
    )
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="  Provider reply  "))]
    )
    provider.client.chat.completions.create = AsyncMock(return_value=completion)
    message = ChatMessage(
        id="message-2",
        owner_id="user-2",
        content="A prompt",
        timestamp=datetime.now(timezone.utc),
        conversation_id="conversation-2",
    )

    reply = asyncio.run(provider.generate_chat_reply(message, "request-3"))

    assert reply.message_id == "message-2"
    assert reply.content == "Provider reply"
    provider.client.chat.completions.create.assert_awaited_once()
    call_kwargs = provider.client.chat.completions.create.await_args.kwargs
    assert call_kwargs["extra_headers"] == {"X-Request-ID": "request-3"}
    asyncio.run(provider.close())


def test_openai_provider_includes_persisted_history_in_prompt() -> None:
    provider = OpenAIChatProvider(
        api_key="test-key",
        model="test-model",
        timeout_seconds=1,
        max_tokens=50,
    )
    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="Follow-up response"))]
    )
    provider.client.chat.completions.create = AsyncMock(return_value=completion)
    message = ChatMessage(
        id="message-new",
        owner_id="user-2",
        content="And what happened next?",
        timestamp=datetime.now(timezone.utc),
        conversation_id="conversation-2",
    )
    history = [
        Message(
            id="message-old",
            conversation_id="conversation-2",
            owner_id="user-2",
            role="user",
            content="Tell me a story.",
            timestamp=datetime.now(timezone.utc),
        ),
        Message(
            id="reply-old",
            conversation_id="conversation-2",
            owner_id="user-2",
            role="assistant",
            content="Once upon a time.",
            timestamp=datetime.now(timezone.utc),
        ),
    ]

    asyncio.run(
        provider.generate_chat_reply(message, "request-history", history)
    )

    sent_messages = provider.client.chat.completions.create.await_args.kwargs["messages"]
    assert sent_messages[1] == {"role": "user", "content": "Tell me a story."}
    assert sent_messages[2] == {
        "role": "assistant",
        "content": "Once upon a time.",
    }
    assert sent_messages[3] == {
        "role": "user",
        "content": "And what happened next?",
    }
    asyncio.run(provider.close())
