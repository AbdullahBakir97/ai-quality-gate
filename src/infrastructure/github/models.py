"""Pydantic models for GitHub webhook payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field

__all__ = [
    "UserPayload",
    "LabelPayload",
    "RepositoryPayload",
    "InstallationPayload",
    "IssuePayload",
    "PullRequestPayload",
    "WebhookPayload",
]


class UserPayload(BaseModel):
    """GitHub user data from a webhook payload."""

    login: str
    id: int
    type: str = "User"


class LabelPayload(BaseModel):
    """GitHub label data from a webhook payload."""

    id: int | None = None
    name: str
    color: str = ""
    description: str = ""


class RepositoryPayload(BaseModel):
    """GitHub repository data from a webhook payload."""

    id: int
    name: str
    full_name: str
    owner: UserPayload
    private: bool = False
    default_branch: str = "main"


class InstallationPayload(BaseModel):
    """GitHub App installation data from a webhook payload."""

    id: int
    app_id: int | None = None


class IssuePayload(BaseModel):
    """GitHub issue data from a webhook payload."""

    number: int
    title: str
    body: str | None = None
    user: UserPayload
    labels: list[LabelPayload] = Field(default_factory=list)
    state: str = "open"


class PullRequestPayload(BaseModel):
    """GitHub pull request data from a webhook payload."""

    number: int
    title: str
    body: str | None = None
    user: UserPayload
    labels: list[LabelPayload] = Field(default_factory=list)
    state: str = "open"
    head: dict = Field(default_factory=dict)
    diff_url: str | None = None


class WebhookPayload(BaseModel):
    """Top-level GitHub webhook event payload."""

    action: str
    sender: UserPayload
    repository: RepositoryPayload
    installation: InstallationPayload | None = None
    issue: IssuePayload | None = None
    pull_request: PullRequestPayload | None = None
