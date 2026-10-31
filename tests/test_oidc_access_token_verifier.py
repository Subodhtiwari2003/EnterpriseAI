import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

from app.domain.interfaces.access_token_verifier import (
    InvalidAccessToken,
    TokenVerifierUnavailable,
)
from app.infrastructure.services.auth.oidc_access_token_verifier import (
    OIDCAccessTokenVerifier,
)


ISSUER = "https://issuer.example.test/"
AUDIENCE = "enterprise-ai-chat-tests"


@pytest.fixture
def rsa_keys(monkeypatch: pytest.MonkeyPatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    monkeypatch.setattr(
        PyJWKClient,
        "get_signing_key_from_jwt",
        lambda _client, _token: SimpleNamespace(key=public_key),
    )
    return private_key


def create_token(private_key, **overrides) -> str:
    now = datetime.now(timezone.utc)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "user-123",
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def create_verifier() -> OIDCAccessTokenVerifier:
    return OIDCAccessTokenVerifier(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url="https://issuer.example.test/.well-known/jwks.json",
        timeout_seconds=1,
    )


def test_verifies_signature_issuer_audience_and_subject(rsa_keys) -> None:
    identity = asyncio.run(create_verifier().verify(create_token(rsa_keys)))

    assert identity.issuer == ISSUER
    assert identity.subject == "user-123"
    assert len(identity.owner_id) == 64


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://untrusted.example.test/"},
        {"aud": "another-service"},
        {"sub": ""},
        {"exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
    ],
)
def test_rejects_invalid_claims(rsa_keys, overrides) -> None:
    with pytest.raises(InvalidAccessToken):
        asyncio.run(create_verifier().verify(create_token(rsa_keys, **overrides)))


def test_rejects_invalid_signature(rsa_keys) -> None:
    other_private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    with pytest.raises(InvalidAccessToken):
        asyncio.run(create_verifier().verify(create_token(other_private_key)))


def test_jwks_connection_failure_is_not_misreported_as_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_to_fetch(_client, _token):
        raise PyJWKClientConnectionError("JWKS unavailable")

    monkeypatch.setattr(PyJWKClient, "get_signing_key_from_jwt", fail_to_fetch)

    with pytest.raises(TokenVerifierUnavailable):
        asyncio.run(create_verifier().verify("token"))
