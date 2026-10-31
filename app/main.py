from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.middleware.application_error_handler import register_exception_handlers
from app.api.middleware.request_id import RequestIdMiddleware
from app.api.routers.chat import router as chat_router
from app.api.routers.health import router as health_router
from app.dependency_container import get_dependency_container
from app.config.application_logging import configure_application_logging


application_dependencies = get_dependency_container()
configure_application_logging(application_dependencies.settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await application_dependencies.close()

app = FastAPI(
	title=application_dependencies.settings.app_name,
	version="0.1.0",
	lifespan=lifespan,
)
app.add_middleware(RequestIdMiddleware)
register_exception_handlers(app)
app.include_router(health_router)
app.include_router(chat_router, prefix="/chat")
app.include_router(chat_router, prefix="/assistant")
