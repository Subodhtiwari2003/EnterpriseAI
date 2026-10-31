import logging
from collections.abc import Sequence
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    RateLimitError,
)

from app.domain.interfaces.application_error import ApplicationError
from app.domain.interfaces.llm_provider import LLMProvider
from app.domain.models.chat import ChatMessage, ChatReply
from app.domain.models.message_model import Message

logger = logging.getLogger(__name__)


class OpenAIChatProvider(LLMProvider):
    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_tokens: int,
        chat_id: str = "enterprise_ai",
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key,
            timeout=timeout_seconds,
            max_retries=0,
        )
        self.model = model
        self.max_tokens = max_tokens
        self.chat_id = chat_id

    async def generate_chat_reply(
        self,
        message: ChatMessage,
        request_id: str,
        history: Sequence[Message] = (),
    ) -> ChatReply:
        started_at = perf_counter()
        logger.info(
            "AI provider request started",
            extra={"request_id": request_id, "model": self.model},
        )
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful enterprise chat service.",
                    },
                    *[
                        {"role": past_message.role, "content": past_message.content}
                        for past_message in history
                    ],
                    {"role": "user", "content": message.content},
                ],
                max_completion_tokens=self.max_tokens,
                extra_headers={"X-Request-ID": request_id},
            )
        except APITimeoutError as error:
            logger.warning("AI provider timed out", extra={"request_id": request_id})
            raise ApplicationError(
                "The AI provider timed out.",
                code="ai_provider_timeout",
                status_code=504,
            ) from error
        except RateLimitError as error:
            logger.warning("AI provider rate limit reached", extra={"request_id": request_id})
            raise ApplicationError(
                "The AI provider is temporarily rate limited.",
                code="ai_provider_rate_limited",
                status_code=429,
            ) from error
        except AuthenticationError as error:
            logger.error("AI provider authentication failed", extra={"request_id": request_id})
            raise ApplicationError(
                "The AI provider is not configured correctly.",
                code="ai_provider_authentication_failed",
                status_code=503,
            ) from error
        except APIConnectionError as error:
            logger.warning("AI provider connection failed", extra={"request_id": request_id})
            raise ApplicationError(
                "The AI provider is unavailable.",
                code="ai_provider_unavailable",
                status_code=503,
            ) from error
        except APIStatusError as error:
            logger.error(
                "AI provider returned an error status",
                extra={"request_id": request_id, "provider_status": error.status_code},
            )
            raise ApplicationError(
                "The AI provider could not complete the request.",
                code="ai_provider_error",
                status_code=502,
            ) from error

        if not response.choices:
            content = None
        else:
            content = response.choices[0].message.content
        if not content or not content.strip():
            raise ApplicationError(
                "The AI provider returned an empty response.",
                code="ai_provider_empty_response",
                status_code=502,
            )

        logger.info(
            "AI provider request completed",
            extra={
                "request_id": request_id,
                "model": self.model,
                "duration_seconds": round(perf_counter() - started_at, 3),
            },
        )
        return ChatReply(
            id=str(uuid4()),
            message_id=message.id,
            chat_id=self.chat_id,
            content=content.strip(),
            timestamp=datetime.now(timezone.utc),
            evaluation_score=None,
            conversation_id=message.conversation_id,
        )

    async def close(self) -> None:
        await self.client.close()
