# Enterprise AI Chat

## Current Status

Sprints 1–5 provide the FastAPI foundation, chat API, pluggable LLM providers,
and PostgreSQL-backed conversation history. Sprint 6 secures chat and history
with OIDC authentication and owner-scoped access.

### Sprint 1: Application Foundation

- FastAPI application startup
- Environment-based settings
- Application logging
- Health endpoint
- Initial test setup

### Sprint 2: Request Context and Error Handling

- Request ID generation when a caller does not provide one
- Request ID preservation through the request state and response header
- Structured application errors with stable error codes, messages, status codes,
  and request IDs
- Tests covering the success and error paths

### Sprint 3: Chat Message API

- Chat domain entities for user messages and generated replies
- `SendChatMessage` use case with a deterministic placeholder response
- `POST /chat/messages` endpoint
- Legacy `POST /assistant/messages` route retained as a compatibility alias
- Request validation for user IDs and message content
- Request ID propagation through chat responses
- Tests covering successful replies, generated request IDs, and validation errors

### Sprint 4: AI Provider Integration

- `SendChatMessage` delegates reply generation to an injected LLM provider
- Local development defaults to a deterministic placeholder provider
- Optional asynchronous OpenAI chat-completions adapter
- Environment-based provider, model, API key, timeout, and token-limit settings
- Provider timeout, rate-limit, authentication, connection, and API failures map
    to stable application errors
- Request IDs are forwarded to the provider and included in safe operational logs
- Tests use a local provider double and do not require a live AI account

To use OpenAI, set `AI_PROVIDER=openai` and provide `AI_API_KEY` in `.env`. Keep
the key out of source control. `AI_MODEL`, `AI_TIMEOUT_SECONDS`, and
`AI_MAX_TOKENS` configure the request. The default `AI_PROVIDER=placeholder`
keeps the app usable without credentials.

### Sprint 5: Conversation Persistence

- PostgreSQL persistence for conversations and user/assistant messages
- Async SQLAlchemy repository with user-scoped conversation history
- `conversation_id` returned by chat endpoints and accepted to continue a chat
- `GET /chat/conversations/{conversation_id}/messages` history route
- Last 20 messages are supplied as context to the OpenAI provider
- The initial development implementation created tables on startup; Sprint 6
replaces that with Alembic migrations

### Sprint 6: OIDC Authentication and Conversation Ownership

- Chat and history endpoints require an OIDC access token in the
  `Authorization: Bearer` header
- RS256 signatures and required issuer, audience, expiry, and subject claims are
  validated against the configured JWKS endpoint
- Authenticated ownership uses a SHA-256 key derived from the verified issuer
  and subject; callers can no longer choose an identity in request data
- Conversation creation, continuation, history reads, and message persistence
  are scoped to that owner
- Database schema changes are managed with Alembic instead of application
  startup `create_all`
- Missing or invalid tokens return 401; JWKS outages return 503; another user's
  conversation remains indistinguishable from a missing conversation (404)

Set `AUTH_ISSUER`, `AUTH_AUDIENCE`, and `AUTH_JWKS_URL` to the values for your
OIDC provider in `.env`. The provider must publish RS256 signing keys at its
JWKS endpoint. Authentication configuration is required; the app does not have
a development identity bypass.

For a new database, apply the schema before starting the application:

```powershell
alembic upgrade head
```

For a database created before Alembic was introduced, back it up and verify
that its tables and indexes match the initial migration. Then run:

```powershell
alembic stamp 0001_conversation_storage
alembic upgrade head
```

The second command renames the old `user_id` columns to `owner_id`. Existing
conversation records retain the old caller-provided IDs and are not
automatically assigned to authenticated accounts; keep them archived or
reconcile ownership through a separately reviewed process.

### Next

Add streaming responses, then document ingestion and retrieval as separate
milestones.

## Setup

PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[test]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Set `DATABASE_URL` and the OIDC settings in `.env`. Apply database migrations
before starting the application.

## Run

```powershell
uvicorn app.main:app --reload
```

Application code is organized by clean-architecture responsibility: API
endpoints, middleware, and HTTP schemas live under `app/api`, framework-neutral
domain models and contracts under `app/domain`, orchestration under
`app/application/use_cases`, external providers under
`app/infrastructure/services`, general settings under `app/config`, and
dependency bindings in `app/dependency_container.py`.

Chat requests create a conversation automatically unless an existing
`conversation_id` is provided. Use the returned ID to continue the conversation
or retrieve history. The authenticated identity comes only from the verified
access token; callers do not send `user_id`.

Health endpoint:

```text
http://127.0.0.1:8000/health/
```

## Test

```powershell
pytest
```
