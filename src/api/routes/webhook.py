"""Webhook endpoint — receives and verifies GitHub webhook events."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, Request, Response

from src.api.dependencies import get_container, get_webhook_handler
from src.api.schemas import WebhookResponse
from src.application.webhook_handler import WebhookHandler
from src.container import Container
from src.domain.exceptions import WebhookValidationError

__all__ = ["router"]

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhook"])


@router.post("/webhook", response_model=WebhookResponse)
async def receive_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"),
    container: Container = Depends(get_container),
    handler: WebhookHandler = Depends(get_webhook_handler),
) -> WebhookResponse:
    """Receive a GitHub webhook event.

    Verifies the payload signature (when a webhook secret is configured),
    then delegates processing to :class:`WebhookHandler`.
    """
    body = await request.body()

    # Verify signature if a verifier is configured
    if container.webhook_verifier is not None:
        if not container.webhook_verifier.verify(body, x_hub_signature_256):
            raise WebhookValidationError("Invalid webhook signature")

    payload = await request.json()

    # Set the installation ID on the GitHub client if present
    installation = payload.get("installation")
    if installation:
        container.github_client.set_installation_id(installation["id"])

    logger.info("Received webhook: event=%s action=%s", x_github_event, payload.get("action"))
    await handler.handle_event(x_github_event, payload)

    return WebhookResponse(received=True)
