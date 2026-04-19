"""Global exception handler middleware for the FastAPI application."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.domain.exceptions import (
    AIQualityGateError,
    AnalysisError,
    ConfigurationError,
    GitHubAPIError,
    WebhookValidationError,
)

__all__ = ["register_error_handlers"]

logger = logging.getLogger(__name__)

# Map domain exception types to HTTP status codes.
_STATUS_MAP: dict[type[AIQualityGateError], int] = {
    WebhookValidationError: 401,
    ConfigurationError: 500,
    GitHubAPIError: 502,
    AnalysisError: 422,
}


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(AIQualityGateError)
    async def handle_domain_error(request: Request, exc: AIQualityGateError) -> JSONResponse:
        """Convert domain exceptions into JSON error responses."""
        status_code = _STATUS_MAP.get(type(exc), 500)
        logger.error("Domain error [%s]: %s", type(exc).__name__, exc)
        return JSONResponse(
            status_code=status_code,
            content={
                "error": type(exc).__name__,
                "detail": str(exc),
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all for unhandled exceptions."""
        logger.exception("Unexpected error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": "InternalServerError",
                "detail": "An unexpected error occurred.",
            },
        )
