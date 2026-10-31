import asyncio
from typing import Any

import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from app.domain.interfaces.access_token_verifier import (
    IAccessTokenVerifier,
    InvalidAccessToken,
    TokenVerifierUnavailable,
)
from app.domain.models.user_identity import UserIdentity


class OIDCAccessTokenVerifier(IAccessTokenVerifier):
    def __init__(
        self,
        issuer: str,
        audience: str,
        jwks_url: str,
        timeout_seconds: float,
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.jwks_client = PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            timeout=timeout_seconds,
        )

    async def verify(self, token: str) -> UserIdentity:
        try:
            signing_key = await asyncio.to_thread(
                self.jwks_client.get_signing_key_from_jwt,
                token,
            )
        except PyJWKClientConnectionError as error:
            raise TokenVerifierUnavailable from error
        except PyJWKClientError as error:
            raise InvalidAccessToken from error
        except jwt.InvalidTokenError as error:
            raise InvalidAccessToken from error

        try:
            claims: dict[str, Any] = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iss", "sub", "aud"]},
            )
        except jwt.InvalidTokenError as error:
            raise InvalidAccessToken from error

        subject = claims.get("sub")
        if not isinstance(subject, str) or not subject.strip():
            raise InvalidAccessToken
        return UserIdentity(issuer=self.issuer, subject=subject)
