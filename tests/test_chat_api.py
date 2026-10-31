import pytest
from fastapi.testclient import TestClient

from app.api.dependencies.current_user import get_current_user
from app.dependency_container import get_send_chat_message
from app.domain.interfaces.application_error import ApplicationError
from app.domain.models.message_model import Message
from app.domain.models.user_identity import UserIdentity
from app.infrastructure.services.llm.placeholder_llm_provider import (
    PlaceholderLLMProvider,
)
from app.application.use_cases.send_chat_message import SendChatMessage
from app.main import app


class InMemoryConversationRepository:
    def __init__(self) -> None:
        self.owners: dict[str, str] = {}
        self.messages: dict[str, list[Message]] = {}

    async def create_conversation(self, owner_id: str) -> str:
        conversation_id = f"conversation-{len(self.owners) + 1}"
        self.owners[conversation_id] = owner_id
        self.messages[conversation_id] = []
        return conversation_id

    async def save_message(self, message: Message) -> None:
        if self.owners.get(message.conversation_id) != message.owner_id:
            raise ApplicationError(
                "The conversation was not found.",
                code="conversation_not_found",
                status_code=404,
            )
        self.messages[message.conversation_id].append(message)

    async def get_history(
        self, conversation_id: str, owner_id: str, limit: int = 20
    ) -> list[Message]:
        if self.owners.get(conversation_id) != owner_id:
            raise ApplicationError(
                "The conversation was not found.",
                code="conversation_not_found",
                status_code=404,
            )
        return self.messages[conversation_id][-limit:]


@pytest.fixture(scope="module")
def client():
    repository = InMemoryConversationRepository()
    app.dependency_overrides[get_send_chat_message] = lambda: SendChatMessage(
        PlaceholderLLMProvider(), repository
    )
    app.dependency_overrides[get_current_user] = lambda: UserIdentity(
        issuer="https://issuer.example.test/",
        subject="chat-api-user",
    )
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def test_chat_message_returns_reply_and_request_id(client: TestClient) -> None:
    response = client.post(
        "/assistant/messages",
        headers={"X-Request-ID": "sprint3-request"},
        json={"content": "  Hello chat  "},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "sprint3-request"
    assert response.json()["assistant_id"] == "enterprise_ai"
    assert response.json()["message_id"]
    assert response.json()["conversation_id"]
    assert response.json()["content"] == (
        "Echo from Chat: 'Hello chat' (Request ID: sprint3-request)"
    )


def test_chat_message_generates_request_id_when_missing(client: TestClient) -> None:
    response = client.post(
        "/chat/messages",
        json={"content": "Hello chat"},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"]


def test_legacy_assistant_route_remains_available(client: TestClient) -> None:
    response = client.post(
        "/assistant/messages",
        headers={"X-Request-ID": "legacy-chat-request"},
        json={"content": "Hello chat"},
    )

    assert response.status_code == 200
    assert response.json()["assistant_id"] == "enterprise_ai"


def test_chat_message_rejects_empty_content(client: TestClient) -> None:
    response = client.post(
        "/assistant/messages",
        json={"content": "   "},
    )

    assert response.status_code == 422
    assert response.headers["X-Request-ID"]


def test_conversation_messages_are_persisted_and_returned_as_history(
    client: TestClient,
) -> None:
    first_response = client.post(
        "/chat/messages",
        json={"content": "First message"},
    )
    assert first_response.status_code == 200
    conversation_id = first_response.json()["conversation_id"]

    second_response = client.post(
        "/chat/messages",
        json={
            "content": "Follow-up message",
            "conversation_id": conversation_id,
        },
    )
    assert second_response.status_code == 200

    history_response = client.get(
        f"/chat/conversations/{conversation_id}/messages",
    )

    assert history_response.status_code == 200
    assert [message["role"] for message in history_response.json()] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert history_response.json()[0]["content"] == "First message"
    assert history_response.json()[2]["content"] == "Follow-up message"
    assert "owner_id" not in history_response.json()[0]


def test_conversation_history_is_scoped_to_user(client: TestClient) -> None:
    create_response = client.post(
        "/chat/messages",
        json={"content": "Private conversation"},
    )
    assert create_response.status_code == 200

    app.dependency_overrides[get_current_user] = lambda: UserIdentity(
        issuer="https://issuer.example.test/",
        subject="different-user",
    )
    response = client.get(
        f"/chat/conversations/{create_response.json()['conversation_id']}/messages",
        params={"user_id": "chat-api-user"},
    )

    assert response.status_code == 404
    assert response.json()["error"] == "conversation_not_found"


def test_chat_request_rejects_caller_supplied_user_id(client: TestClient) -> None:
    response = client.post(
        "/chat/messages",
        json={"user_id": "forged-user", "content": "Hello chat"},
    )

    assert response.status_code == 422
