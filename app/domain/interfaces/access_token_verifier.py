from abc import ABC, abstractmethod

from app.domain.models.user_identity import UserIdentity


class InvalidAccessToken(Exception):
    pass


class TokenVerifierUnavailable(Exception):
    pass


class IAccessTokenVerifier(ABC):
    @abstractmethod
    async def verify(self, token: str) -> UserIdentity:
        raise NotImplementedError
