"""Application-wide settings loaded from environment variables."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings

__all__ = ["Settings"]


class Settings(BaseSettings):
    """Global application settings.

    Values are read from environment variables or an ``.env`` file.
    """

    app_id: str = Field(..., description="GitHub App ID")
    private_key: str = Field(default="", description="GitHub App private key content")
    private_key_path: str = Field(default="./private-key.pem", description="Path to private key file")
    webhook_secret: str = Field(default="", description="Webhook signature secret")
    port: int = Field(default=8000, description="Server port")
    env: str = Field(default="development", description="Environment")
    log_level: str = Field(default="INFO", description="Logging level")
    allowed_origins: str = Field(default="*", description="CORS origins")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def is_development(self) -> bool:
        """Whether the app is running in development mode."""
        return self.env == "development"

    def get_private_key(self) -> str:
        """Return the private key content, reading from file if necessary.

        If ``private_key`` is set directly it is returned (with literal
        ``\\n`` sequences replaced by newlines).  Otherwise the key is
        read from ``private_key_path``.
        """
        if self.private_key:
            return self.private_key.replace("\\n", "\n")
        with open(self.private_key_path) as f:
            return f.read()
