"""Environment-based configuration for system_design_app."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONTENT_BANK_PATH = DATA_DIR / "content_bank.json"
STATE_PATH = DATA_DIR / "state.json"

DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5"
LOW_STOCK_THRESHOLD = 3
GENERATE_BATCH_SIZE = 5


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    telegram_chat_id: str
    anthropic_api_key: str | None
    anthropic_model: str = DEFAULT_ANTHROPIC_MODEL


def load_config(env_file: Path | None = None) -> Config:
    """Load configuration from the environment, reading `.env` first."""
    load_dotenv(dotenv_path=env_file or PROJECT_ROOT / ".env")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token:
        raise ConfigError("TELEGRAM_BOT_TOKEN is not set")
    if not chat_id:
        raise ConfigError("TELEGRAM_CHAT_ID is not set")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip() or None
    model = os.environ.get("ANTHROPIC_MODEL", "").strip() or DEFAULT_ANTHROPIC_MODEL

    return Config(
        telegram_bot_token=token,
        telegram_chat_id=chat_id,
        anthropic_api_key=api_key,
        anthropic_model=model,
    )
