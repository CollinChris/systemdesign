"""Loading and persisting the content bank and send-history state."""

from __future__ import annotations

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


def load_state(path: Path) -> set[int]:
    if not path.exists():
        return set()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("state file at %s is corrupt; starting a fresh cycle", path)
        return set()
    return set(raw.get("sent_ids", []))


def save_state(path: Path, sent_ids: set[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"sent_ids": sorted(sent_ids)}, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")
