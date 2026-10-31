from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.application.use_cases.authenticate_user import AuthenticateUser
from app.application.use_cases.send_chat_message import SendChatMessage
from app.config.application_settings import (
    ApplicationSettings,
    get_application_settings,
)
from app.domain.interfaces.access_token_verifier import IAccessTokenVerifier
from app.domain.interfaces.conversation_repo import IConversationRepository
from app.domain.interfaces.llm_provider import LLMProvider
from app.infrastructure.database import Database
from app.infrastructure.repositories.conversation_repository import (
    ConversationRepository,
)
from app.infrastructure.services.auth.oidc_access_token_verifier import (
    OIDCAccessTokenVerifier,
)
from app.infrastructure.services.llm.openai_chat_provider import OpenAIChatProvider
from app.infrastructure.services.llm.placeholder_llm_provider import (
    PlaceholderLLMProvider,
)


@dataclass(frozen=True)
class ApplicationDependencyContainer:
    settings: ApplicationSettings
    llm_provider: LLMProvider
    access_token_verifier: IAccessTokenVerifier
    authenticate_user: AuthenticateUser
    database: Database
    conversation_repository: IConversationRepository
    send_chat_message: SendChatMessage

    async def close(self) -> None:
        try:
            await self.llm_provider.close()
        finally:
            await self.database.close()


@lru_cache
def get_dependency_container() -> ApplicationDependencyContainer:
    settings = get_application_settings()
    if settings.ai_provider == "openai":
        llm_provider: LLMProvider = OpenAIChatProvider(
            api_key=settings.ai_api_key.get_secret_value(),
            model=settings.ai_model,
            timeout_seconds=settings.ai_timeout_seconds,
            max_tokens=settings.ai_max_tokens,
        )
    else:
        llm_provider = PlaceholderLLMProvider()
    access_token_verifier = OIDCAccessTokenVerifier(
        issuer=settings.auth_issuer,
        audience=settings.auth_audience,
        jwks_url=settings.auth_jwks_url,
        timeout_seconds=settings.auth_jwks_timeout_seconds,
    )
    engine = create_async_engine(
        settings.database_url.get_secret_value(),
        pool_pre_ping=True,
    )
    database = Database(engine)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    conversation_repository = ConversationRepository(session_factory)
    return ApplicationDependencyContainer(
        settings=settings,
        llm_provider=llm_provider,
        access_token_verifier=access_token_verifier,
        authenticate_user=AuthenticateUser(access_token_verifier),
        database=database,
        conversation_repository=conversation_repository,
        send_chat_message=SendChatMessage(llm_provider, conversation_repository),
    )


def get_send_chat_message() -> SendChatMessage:
    return get_dependency_container().send_chat_message


def get_authenticate_user() -> AuthenticateUser:
    return get_dependency_container().authenticate_user
