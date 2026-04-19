"""GitHub API client implementing IGitHubClient from the domain layer."""

from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

from src.domain.exceptions import GitHubAPIError
from src.domain.interfaces import IGitHubClient

from .auth import GitHubAuthenticator

__all__ = ["GitHubClient"]

logger = logging.getLogger(__name__)

# Default label colours applied when creating labels that do not yet exist.
LABEL_COLORS: dict[str, str] = {
    "ai-generated": "d93f0b",
    "ai-suspected": "e4e669",
    "low-quality": "f9d0c4",
    "high-quality": "0e8a16",
}

_BASE_URL = "https://api.github.com"
_BOT_COMMENT_MARKER = "<!-- AI Quality Gate -->"


class GitHubClient(IGitHubClient):
    """Concrete GitHub API client backed by *httpx.AsyncClient*.

    All requests are authenticated using installation access tokens
    obtained from the supplied :class:`GitHubAuthenticator`.
    """

    def __init__(self, authenticator: GitHubAuthenticator, installation_id: int = 0) -> None:
        self._auth = authenticator
        self._installation_id = installation_id

    def set_installation_id(self, installation_id: int) -> None:
        """Update the installation ID used for subsequent API calls."""
        self._installation_id = installation_id

    async def _headers(self) -> dict[str, str]:
        """Build authentication and accept headers."""
        token = await self._auth.get_installation_token(self._installation_id)
        return {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Execute an authenticated API request.

        Raises:
            GitHubAPIError: On non-2xx responses.
        """
        headers = await self._headers()
        async with httpx.AsyncClient(base_url=_BASE_URL) as client:
            resp = await client.request(method, path, headers=headers, json=json, params=params)

        if resp.status_code >= 400:
            raise GitHubAPIError(
                f"GitHub API error {resp.status_code}: {resp.text}",
                status_code=resp.status_code,
            )
        return resp

    # ------------------------------------------------------------------
    # IGitHubClient implementation
    # ------------------------------------------------------------------

    async def post_comment(self, owner: str, repo: str, number: int, body: str) -> None:
        """Post or update an AI Quality Gate comment on an issue or PR.

        If a comment containing the bot marker already exists it will be
        updated in-place; otherwise a new comment is created.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: Issue or pull-request number.
            body: Markdown comment body.
        """
        marked_body = f"{_BOT_COMMENT_MARKER}\n{body}"

        # Check for an existing bot comment
        existing_id = await self._find_bot_comment(owner, repo, number)
        if existing_id is not None:
            await self._request(
                "PATCH",
                f"/repos/{owner}/{repo}/issues/comments/{existing_id}",
                json={"body": marked_body},
            )
            logger.info("Updated existing comment %s on %s/%s#%d", existing_id, owner, repo, number)
        else:
            await self._request(
                "POST",
                f"/repos/{owner}/{repo}/issues/{number}/comments",
                json={"body": marked_body},
            )
            logger.info("Created new comment on %s/%s#%d", owner, repo, number)

    async def add_labels(self, owner: str, repo: str, number: int, labels: list[str]) -> None:
        """Add labels to an issue or PR, creating missing labels first.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: Issue or pull-request number.
            labels: Label names to apply.
        """
        await self._ensure_labels_exist(owner, repo, labels)
        await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{number}/labels",
            json={"labels": labels},
        )
        logger.info("Added labels %s to %s/%s#%d", labels, owner, repo, number)

    async def create_check_run(
        self,
        owner: str,
        repo: str,
        head_sha: str,
        title: str,
        summary: str,
        conclusion: str,
        details: str,
    ) -> None:
        """Create a check run on a commit.

        Args:
            owner: Repository owner.
            repo: Repository name.
            head_sha: The SHA of the commit to annotate.
            title: Check run title.
            summary: Short summary text.
            conclusion: One of ``success``, ``failure``, ``neutral``, etc.
            details: Extended markdown details.
        """
        await self._request(
            "POST",
            f"/repos/{owner}/{repo}/check-runs",
            json={
                "name": "AI Quality Gate",
                "head_sha": head_sha,
                "status": "completed",
                "conclusion": conclusion,
                "output": {
                    "title": title,
                    "summary": summary,
                    "text": details,
                },
            },
        )
        logger.info("Created check run on %s/%s@%s", owner, repo, head_sha[:8])

    async def request_changes(self, owner: str, repo: str, number: int, body: str) -> None:
        """Submit a pull-request review requesting changes.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: Pull-request number.
            body: Review body in markdown.
        """
        await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls/{number}/reviews",
            json={"body": body, "event": "REQUEST_CHANGES"},
        )
        logger.info("Requested changes on %s/%s#%d", owner, repo, number)

    async def close_contribution(self, owner: str, repo: str, number: int) -> None:
        """Close an issue or pull request.

        Args:
            owner: Repository owner.
            repo: Repository name.
            number: Issue or pull-request number.
        """
        await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/issues/{number}",
            json={"state": "closed"},
        )
        logger.info("Closed %s/%s#%d", owner, repo, number)

    async def get_file_content(self, owner: str, repo: str, path: str) -> str | None:
        """Retrieve a file from the repository, decoded from base64.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: File path within the repository.

        Returns:
            The decoded file content, or ``None`` if the file does not exist.
        """
        try:
            resp = await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}")
            data = resp.json()
            return base64.b64decode(data["content"]).decode("utf-8")
        except GitHubAPIError as exc:
            if exc.status_code == 404:
                return None
            raise

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _find_bot_comment(self, owner: str, repo: str, number: int) -> int | None:
        """Return the ID of the existing bot comment, if any."""
        try:
            resp = await self._request("GET", f"/repos/{owner}/{repo}/issues/{number}/comments")
            for comment in resp.json():
                if _BOT_COMMENT_MARKER in comment.get("body", ""):
                    return comment["id"]
        except GitHubAPIError:
            pass
        return None

    async def _ensure_labels_exist(self, owner: str, repo: str, labels: list[str]) -> None:
        """Create any labels that do not already exist in the repository."""
        for label in labels:
            color = LABEL_COLORS.get(label, "ededed")
            try:
                await self._request(
                    "POST",
                    f"/repos/{owner}/{repo}/labels",
                    json={"name": label, "color": color},
                )
            except GitHubAPIError as exc:
                # 422 means the label already exists — that's fine.
                if exc.status_code != 422:
                    logger.warning("Failed to create label %s: %s", label, exc)
