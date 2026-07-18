"""Application configuration, sourced entirely from environment variables.

Every setting has a safe local-dev default so the app boots out of the box.
Production overrides come from the environment (see .env.example).
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="JOTTR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Storage -----------------------------------------------------------
    # The single named volume. Everything the app owns lives under here.
    data_dir: Path = Field(default=Path("./data"))

    # --- HTTP / app --------------------------------------------------------
    # Public base URL of the app, used to build the OAuth redirect URI.
    base_url: str = Field(default="http://localhost:8000")
    # Where the built SPA lives (populated by the Docker build). In local dev
    # the Vite dev server serves the frontend instead, so this may be absent.
    static_dir: Path = Field(default=Path("./static"))

    # --- Auth --------------------------------------------------------------
    google_client_id: str = Field(default="")
    google_client_secret: str = Field(default="")
    # Comma-separated allowlist of emails permitted to log in.
    allowed_emails: str = Field(default="")
    # Secret used to sign the session JWT. MUST be overridden in production.
    jwt_secret: str = Field(default="dev-insecure-change-me")
    jwt_ttl_seconds: int = Field(default=60 * 60 * 24 * 30)  # 30 days
    session_cookie_name: str = Field(default="jottr_session")

    # When true (and no Google client id is set), skip real OAuth and log in a
    # fixed dev user. Lets Phase 0 run before Google credentials exist.
    dev_auth: bool = Field(default=True)
    dev_auth_email: str = Field(default="dev@localhost")

    @property
    def allowed_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.allowed_emails.split(",") if e.strip()}

    @property
    def oauth_redirect_uri(self) -> str:
        return f"{self.base_url.rstrip('/')}/api/auth/callback"

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    def is_email_allowed(self, email: str) -> bool:
        # Empty allowlist means "allow the dev user only" in dev, nobody in prod.
        allow = self.allowed_email_set
        if not allow:
            return self.dev_auth and email.lower() == self.dev_auth_email.lower()
        return email.lower() in allow

    # --- Volume layout -----------------------------------------------------
    @property
    def notes_dir(self) -> Path:
        return self.data_dir / "notes"

    @property
    def daily_dir(self) -> Path:
        return self.data_dir / "daily"

    @property
    def attachments_dir(self) -> Path:
        return self.data_dir / "attachments"

    @property
    def auth_dir(self) -> Path:
        return self.data_dir / "auth"

    @property
    def index_db_path(self) -> Path:
        return self.data_dir / "index.sqlite"

    def ensure_volume(self) -> None:
        """Create the on-disk layout inside the data volume if missing."""
        for d in (self.notes_dir, self.daily_dir, self.attachments_dir, self.auth_dir):
            d.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
