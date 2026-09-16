"""Entry point: pick one content bank entry and notify Telegram.

Order of operations, and why:

1. Once-a-day guard. Two triggers fire daily (an external cron at 05:00 UTC
   and GitHub's own schedule, which lands hours late). Whichever runs first
   sends; the second sees today's date in state.json and exits quietly. Pass
   --force to override when testing.
2. Top-up BEFORE the pool reset. Unsent entries are counted before any
   reshuffle, so generation triggers as stock falls, not only on the one or
   two runs per cycle where the old code happened to look.
3. Send today's entry, save state.
4. If generation failed, send a short Telegram note and exit non-zero so the
   Actions run is red instead of silently green.
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import random
import sys
from zoneinfo import ZoneInfo

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
    load_last_sent_date,
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

SG_TZ = ZoneInfo("Asia/Singapore")


def today_sg() -> dt.date:
    return dt.datetime.now(tz=SG_TZ).date()


def get_unsent(
    entries: list[Entry], sent_ids: set[int]
) -> tuple[list[Entry], set[int]]:
    """Return entries not yet sent, reshuffling (resetting) once the pool is exhausted."""
    unsent = [e for e in entries if e.id not in sent_ids]
    if not unsent:
        logger.info("all %d entries have been sent; starting a new cycle", len(entries))
        return list(entries), set()
    return unsent, sent_ids


def generation_failure_note(exc: Exception, unsent_left: int) -> str:
    return (
        "System Design bot: content generation failed today, so no new entries "
        f"were added. {unsent_left} unsent entr{'y' if unsent_left == 1 else 'ies'} left "
        f"before the bank repeats.\nError: {str(exc)[:300]}"
    )


def run(force: bool = False) -> None:
    cfg = load_config()
    today = today_sg()

    if not force and load_last_sent_date(STATE_PATH) == today:
        logger.info("already sent today (%s); nothing to do", today)
        return

    entries = load_bank(CONTENT_BANK_PATH)
    sent_ids = load_state(STATE_PATH)

    # Stock check before any reset: this is the number that should trigger a top-up.
    remaining = [e for e in entries if e.id not in sent_ids]
    generation_error: GenerationError | None = None
    if cfg.gemini_api_key and len(remaining) < LOW_STOCK_THRESHOLD:
        logger.info(
            "%d unsent entries left (< %d); generating %d more",
            len(remaining),
            LOW_STOCK_THRESHOLD,
            GENERATE_BATCH_SIZE,
        )
        try:
            new_entries = generate_entries(
                api_key=cfg.gemini_api_key,
                model=cfg.gemini_model,
                count=GENERATE_BATCH_SIZE,
                existing_entries=entries,
                start_id=next_id(entries),
                fallback_model=cfg.gemini_fallback_model,
            )
        except GenerationError as exc:
            generation_error = exc
            logger.warning("content generation failed: %s", exc)
        else:
            entries = entries + new_entries
            save_bank(CONTENT_BANK_PATH, entries)

    unsent, sent_ids = get_unsent(entries, sent_ids)
    entry = random.choice(unsent)
    send_message(cfg.telegram_bot_token, cfg.telegram_chat_id, format_message(entry))

    sent_ids.add(entry.id)
    save_state(STATE_PATH, sent_ids, last_sent_date=today)
    logger.info(
        "sent entry %d (%s); %d unsent left", entry.id, entry.type, len(unsent) - 1
    )

    if generation_error is not None:
        send_message(
            cfg.telegram_bot_token,
            cfg.telegram_chat_id,
            generation_failure_note(generation_error, len(unsent) - 1),
        )
        raise generation_error


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    parser = argparse.ArgumentParser(prog="system-design-app")
    parser.add_argument(
        "--force",
        action="store_true",
        help="send even if an entry already went out today",
    )
    args = parser.parse_args()
    try:
        run(force=args.force)
    except (ConfigError, ContentBankError, TelegramError) as exc:
        logger.error("%s", exc)
        sys.exit(1)
    except GenerationError as exc:
        # Today's entry was sent and state saved; the red run is the point.
        logger.error("generation failed (entry still sent): %s", exc)
        sys.exit(2)
