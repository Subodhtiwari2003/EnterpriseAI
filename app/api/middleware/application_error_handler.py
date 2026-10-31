from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.interfaces.application_error import ApplicationError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def handle_application_error(
        request: Request, error: ApplicationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=error.status_code,
            content={
                "error": error.code,
                "message": error.message,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
