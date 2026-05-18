"""Webhook endpoint — receives, verifies, and asynchronously dispatches GitHub events.

The endpoint returns ``200`` to GitHub as soon as the signature and JSON
payload have been validated, then schedules the actual analysis on FastAPI's
``BackgroundTasks``.  This is required because GitHub treats a webhook
delivery as failed if the receiver does not respond within ~10 seconds — and
the analysis pipeline (config fetch + detectors + scorers + label/comment/
check-run posts) routinely exceeds that on a cold Render dyno or for large
PR diffs.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request

from src.api.dependencies import get_container, get_webhook_handler
from src.api.schemas import WebhookResponse
from src.application.webhook_handler import WebhookHandler
from src.container import Container
from src.domain.exceptions import WebhookValidationError

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


async def _process_event_safely(
    handler: WebhookHandler,
    event_type: str,
    payload: dict,
) -> None:
    """Run :meth:`WebhookHandler.handle_event` and swallow any exception.

    Background tasks scheduled via FastAPI run *after* the response is sent,
    so an unhandled exception here only ends up in logs — never in an HTTP
    response.  We log loudly so failures are still visible in the bot's
    Render / container logs.
    """
    try:
        await handler.handle_event(event_type, payload)
    except Exception as exc:  # background safety net — never re-raise from a BackgroundTask
        logger.exception(
            "webhook: background processing failed (event=%s action=%s): %s",
            event_type,
            payload.get("action"),
            exc,
        )


@router.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
    container: Container = Depends(get_container),
    handler: WebhookHandler = Depends(get_webhook_handler),
) -> WebhookResponse:
    """Receive a GitHub webhook event.

    Verifies the payload signature (when a webhook secret is configured),
    captures the installation ID, and schedules the analysis to run in the
    background so the response can return well inside GitHub's 10 second
    delivery window.
    """
    body = await request.body()

    if container.webhook_verifier is not None and not container.webhook_verifier.verify(body, x_hub_signature_256):
        raise WebhookValidationError("Invalid webhook signature")

    payload = await request.json()

    installation = payload.get("installation")
    if installation:
        container.github_client.set_installation_id(installation["id"])

    logger.info(
        "Received webhook: event=%s action=%s",
        x_github_event,
        payload.get("action"),
    )

    # Defer the analysis pipeline so we can ACK GitHub immediately.  Without
    # this, slow detectors / scorers / a cold dyno can push the response past
    # GitHub's 10s timeout and the delivery is marked failed even though the
    # bot eventually finishes its work.
    background_tasks.add_task(_process_event_safely, handler, x_github_event, payload)

    return WebhookResponse(received=True)
