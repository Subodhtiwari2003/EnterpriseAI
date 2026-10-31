from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.dependencies.current_user import get_current_user
from app.api.routers.chat import router as chat_router
from app.dependency_container import get_authenticate_user
from app.domain.interfaces.access_token_verifier import InvalidAccessToken
from app.domain.models.user_identity import UserIdentity


class FakeAuthenticator:
    async def execute(self, token: str) -> UserIdentity:
        if token != "valid-test-token":
            raise InvalidAccessToken
        return UserIdentity(
            issuer="https://issuer.example.test/",
            subject="verified-user",
        )


def create_test_client() -> TestClient:
    test_app = FastAPI()

    @test_app.get("/protected")
    async def protected_endpoint(
        identity: UserIdentity = Depends(get_current_user),
    ) -> dict[str, str]:
        return {"owner_id": identity.owner_id}

    test_app.dependency_overrides[get_authenticate_user] = lambda: FakeAuthenticator()
    return TestClient(test_app)


def test_missing_bearer_token_is_rejected() -> None:
    with create_test_client() as client:
        response = client.get("/protected")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_chat_endpoints_require_bearer_authentication() -> None:
    test_app = FastAPI()
    test_app.include_router(chat_router, prefix="/chat")

    with TestClient(test_app) as client:
        message_response = client.post(
            "/chat/messages",
            json={"content": "Hello"},
        )
        history_response = client.get(
            "/chat/conversations/conversation-1/messages",
        )

    assert message_response.status_code == 401
    assert history_response.status_code == 401


def test_invalid_bearer_token_is_rejected() -> None:
    with create_test_client() as client:
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer invalid-test-token"},
        )

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_verified_identity_is_derived_from_bearer_token() -> None:
    with create_test_client() as client:
        response = client.get(
            "/protected",
            headers={"Authorization": "Bearer valid-test-token"},
        )

    assert response.status_code == 200
    assert response.json()["owner_id"] == UserIdentity(
        issuer="https://issuer.example.test/",
        subject="verified-user",
    ).owner_id


def test_identity_owner_key_changes_with_issuer_or_subject() -> None:
    identity = UserIdentity(
        issuer="https://issuer.example.test/",
        subject="verified-user",
    )
    assert identity.owner_id != UserIdentity(
        issuer="https://other-issuer.example.test/",
        subject="verified-user",
    ).owner_id
    assert identity.owner_id != UserIdentity(
        issuer="https://issuer.example.test/",
        subject="another-user",
    ).owner_id
