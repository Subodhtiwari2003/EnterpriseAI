from app.domain.interfaces.access_token_verifier import IAccessTokenVerifier
from app.domain.models.user_identity import UserIdentity


class AuthenticateUser:
    def __init__(self, token_verifier: IAccessTokenVerifier) -> None:
        self.token_verifier = token_verifier

    async def execute(self, access_token: str) -> UserIdentity:
        return await self.token_verifier.verify(access_token)
