"""Minimal Telegram Bot API client for sending notifications."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class TelegramError(RuntimeError):
    """Raised when the Telegram API rejects or is unreachable for a request."""


def send_message(bot_token: str, chat_id: str, text: str) -> None:
    url = f"{TELEGRAM_API_BASE}/bot{bot_token}/sendMessage"
    try:
        response = httpx.post(
            url,
            json={"chat_id": chat_id, "text": text},
            timeout=15.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise TelegramError(
            f"Telegram API returned {exc.response.status_code}: {exc.response.text}"
        ) from exc
    except httpx.RequestError as exc:
        raise TelegramError(f"failed to reach Telegram API: {exc}") from exc

    logger.info("sent Telegram notification to chat %s", chat_id)
