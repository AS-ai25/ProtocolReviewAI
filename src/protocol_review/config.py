"""Settings loaded from environment / .env (pydantic-settings)."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    anthropic_api_key: str = ""
    llm_model: str = "claude-opus-5-5"
    llm_effort: str = "medium"
    llm_max_tokens: int = 16000
    llm_fallbacks: bool = True
    no_llm: bool = False

    # Webhook
    webhook_secret: str = "change-me"

    # Notifications
    boss_email: str = "coordinator@example.org"
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "protocol-review@example.org"
    email_dry_run: bool = True

    # IMAP ingest
    imap_host: str = ""
    imap_user: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    imap_poll_seconds: int = 120

    # Storage
    database_url: str = "sqlite:///data/protocol_review.db"
    output_dir: str = "outputs"
    log_file: str = "logs/server.log"
    knowledge_base_dir: str = "knowledge_base"

    # Pipeline
    max_revise_rounds: int = 1
    # Hybrid scientific decision rule (charter v1.3): score >= pass_min -> PASS,
    # human_min..pass_min-1 -> NEEDS_HUMAN_REVIEW, < human_min -> MAJOR_CONCERNS
    score_pass_min: int = 90
    score_human_min: int = 70
    clinicaltrials_timeout: int = 20

    @property
    def output_path(self) -> Path:
        p = Path(self.output_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def knowledge_base_path(self) -> Path:
        p = Path(self.knowledge_base_dir)
        return p if p.is_absolute() else PROJECT_ROOT / p

    @property
    def resolved_database_url(self) -> str:
        url = self.database_url
        if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
            rel = url[len("sqlite:///"):]
            if not Path(rel).is_absolute():
                abs_path = PROJECT_ROOT / rel
                abs_path.parent.mkdir(parents=True, exist_ok=True)
                return "sqlite:///" + abs_path.as_posix()
        return url


settings = Settings()
