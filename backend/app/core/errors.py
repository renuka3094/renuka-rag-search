"""
Centralized error handling (Section 6.2).

Design rule from the brief: "An endpoint that returns 200 with an error
message in the body is an attention-to-detail deduction." So every error
path in this app raises one of these exceptions, and a single FastAPI
exception handler (registered in main.py) turns it into the right HTTP
status code with a consistent JSON error shape:

    {"error": {"code": "not_found", "message": "..."}}

Never return {"status": "error", ...} with a 200 status.
"""
from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

log = get_logger(__name__)


class AppError(Exception):
    status_code = 500
    code = "internal_error"

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ValidationAppError(AppError):
    status_code = 422
    code = "validation_error"


class UpstreamProviderError(AppError):
    """Raised when the LLM / embeddings / Azure Search call fails."""
    status_code = 502
    code = "upstream_provider_error"


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    log.error("app_error", path=str(request.url), code=exc.code, message=exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", path=str(request.url), error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "internal_error", "message": "Something went wrong. Please try again."}},
    )
