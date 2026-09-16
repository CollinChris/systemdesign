"""Loading and persisting the content bank and send-history state."""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

from system_design_app.models import Entry

logger = logging.getLogger(__name__)


class ContentBankError(RuntimeError):
    """Raised when the content bank file is missing or malformed."""


def load_bank(path: Path) -> list[Entry]:
    if not path.exists():
        raise ContentBankError(f"content bank not found at {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContentBankError(f"content bank at {path} is not valid JSON") from exc
    if not isinstance(raw, list):
        raise ContentBankError(f"content bank at {path} must be a JSON array")
    return [Entry.from_dict(item) for item in raw]


def save_bank(path: Path, entries: list[Entry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps([e.to_dict() for e in entries], indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")


def next_id(entries: list[Entry]) -> int:
    return max((e.id for e in entries), default=0) + 1


def _read_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("state file at %s is corrupt; starting a fresh cycle", path)
        return {}
    return raw if isinstance(raw, dict) else {}


def load_state(path: Path) -> set[int]:
    return set(_read_state(path).get("sent_ids", []))


def load_last_sent_date(path: Path) -> dt.date | None:
    """The (Asia/Singapore) date of the last send, or None. Lets two daily
    triggers coexist: the second one sees today's date and stands down."""
    raw = _read_state(path).get("last_sent_date")
    if not raw:
        return None
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        logger.warning(
            "state file at %s has an unreadable last_sent_date %r", path, raw
        )
        return None


def save_state(
    path: Path, sent_ids: set[int], last_sent_date: dt.date | None = None
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict = {"sent_ids": sorted(sent_ids)}
    if last_sent_date is None:
        last_sent_date = load_last_sent_date(path)  # keep what is there
    if last_sent_date is not None:
        payload["last_sent_date"] = last_sent_date.isoformat()
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
