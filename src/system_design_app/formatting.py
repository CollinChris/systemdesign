"""Formats content bank entries into Telegram message text."""

from __future__ import annotations

from system_design_app.models import Entry


def format_message(entry: Entry) -> str:
    if entry.type == "fact":
        body = f"System Design Fact\n\n{entry.text}"
    else:
        body = f"System Design Quiz\n\nQ: {entry.question}\n\nA: {entry.answer}"

    return f"{body}\n\n" f'"{entry.source_excerpt}"\n' f"Read more: {entry.source_url}"
