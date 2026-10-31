from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplicationSettings(BaseSettings):
    app_name: str = "Enterprise AI Chat"
    app_env: str = "development"
    log_level: str = "INFO"
    ai_provider: str = "placeholder"
    ai_api_key: SecretStr | None = None
    ai_model: str = "gpt-4o-mini"
    ai_timeout_seconds: float = 30.0
    ai_max_tokens: int = 1000
    database_url: SecretStr
    auth_issuer: str
    auth_audience: str
    auth_jwks_url: str
    auth_jwks_timeout_seconds: float = 5.0

    @field_validator("ai_provider")
    @classmethod
    def normalize_ai_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("auth_issuer", "auth_jwks_url")
    @classmethod
    def require_https_auth_urls(cls, value: str) -> str:
        normalized = value.strip()
        parsed = urlsplit(normalized)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Authentication issuer and JWKS URL must be HTTPS URLs")
        return normalized

    @field_validator("auth_audience")
    @classmethod
    def validate_auth_audience(cls, value: str) -> str:
        audience = value.strip()
        if not audience:
            raise ValueError("AUTH_AUDIENCE must not be empty")
        return audience

    @model_validator(mode="after")
    def validate_ai_configuration(self) -> "ApplicationSettings":
        if self.ai_provider not in {"placeholder", "openai"}:
            raise ValueError("AI_PROVIDER must be 'placeholder' or 'openai'")
        if self.ai_provider == "openai" and (
            self.ai_api_key is None or not self.ai_api_key.get_secret_value().strip()
        ):
            raise ValueError("AI_API_KEY is required when AI_PROVIDER is 'openai'")
        if self.ai_timeout_seconds <= 0:
            raise ValueError("AI_TIMEOUT_SECONDS must be greater than zero")
        if self.ai_max_tokens < 1:
            raise ValueError("AI_MAX_TOKENS must be at least 1")
        if self.auth_jwks_timeout_seconds <= 0:
            raise ValueError("AUTH_JWKS_TIMEOUT_SECONDS must be greater than zero")
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_application_settings() -> ApplicationSettings:
    return ApplicationSettings()
