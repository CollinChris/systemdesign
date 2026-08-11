"""Entry point: pick one content bank entry and notify Telegram."""

from __future__ import annotations

import logging
import random
import sys

from system_design_app.config import (
    CONTENT_BANK_PATH,
    GENERATE_BATCH_SIZE,
    LOW_STOCK_THRESHOLD,
    STATE_PATH,
    ConfigError,
    load_config,
)
from system_design_app.content_bank import (
    ContentBankError,
    load_bank,
    load_state,
    next_id,
    save_bank,
    save_state,
)
from system_design_app.formatting import format_message
from system_design_app.generator import GenerationError, generate_entries
from system_design_app.models import Entry
from system_design_app.telegram import TelegramError, send_message

logger = logging.getLogger(__name__)


def get_unsent(
    entries: list[Entry], sent_ids: set[int]
) -> tuple[list[Entry], set[int]]:
    """Return entries not yet sent, reshuffling (resetting) once the pool is exhausted."""
    unsent = [e for e in entries if e.id not in sent_ids]
    if not unsent:
        logger.info("all %d entries have been sent; starting a new cycle", len(entries))
        return list(entries), set()
    return unsent, sent_ids


def run() -> None:
    cfg = load_config()

    entries = load_bank(CONTENT_BANK_PATH)
    sent_ids = load_state(STATE_PATH)
    unsent, sent_ids = get_unsent(entries, sent_ids)

    if cfg.gemini_api_key and len(unsent) < LOW_STOCK_THRESHOLD:
        try:
            new_entries = generate_entries(
                api_key=cfg.gemini_api_key,
                model=cfg.gemini_model,
                count=GENERATE_BATCH_SIZE,
                existing_entries=entries,
                start_id=next_id(entries),
            )
        except GenerationError as exc:
            logger.warning("content generation skipped: %s", exc)
        else:
            if new_entries:
                entries = entries + new_entries
                save_bank(CONTENT_BANK_PATH, entries)
                unsent = unsent + new_entries

    entry = random.choice(unsent)
    send_message(cfg.telegram_bot_token, cfg.telegram_chat_id, format_message(entry))

    sent_ids.add(entry.id)
    save_state(STATE_PATH, sent_ids)
    logger.info("sent entry %d (%s)", entry.id, entry.type)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    try:
        run()
    except (ConfigError, ContentBankError, TelegramError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
