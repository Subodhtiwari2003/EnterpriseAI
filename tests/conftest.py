import os


os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("AUTH_ISSUER", "https://issuer.example.test/")
os.environ.setdefault("AUTH_AUDIENCE", "enterprise-ai-chat-tests")
os.environ.setdefault(
    "AUTH_JWKS_URL",
    "https://issuer.example.test/.well-known/jwks.json",
)
