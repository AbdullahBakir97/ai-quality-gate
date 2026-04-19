"""Health check and metrics endpoints."""

from __future__ import annotations

import time

from fastapi import APIRouter

from src.api.schemas import HealthResponse

__all__ = ["router"]

router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return current application health status.

    Returns:
        A :class:`HealthResponse` with status, uptime, and version.
    """
    return HealthResponse(
        status="ok",
        uptime=round(time.time() - _START_TIME, 2),
        version="1.0.0",
    )


@router.get("/metrics")
async def metrics() -> dict[str, object]:
    """Return basic application metrics.

    Returns:
        A dictionary with uptime and a timestamp.
    """
    return {
        "uptime_seconds": round(time.time() - _START_TIME, 2),
        "timestamp": time.time(),
    }
