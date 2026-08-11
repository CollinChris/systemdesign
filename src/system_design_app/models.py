"""Data model for content bank entries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

EntryType = Literal["fact", "quiz"]


@dataclass(frozen=True)
class Entry:
    id: int
    type: EntryType
    source_url: str
    source_excerpt: str
    text: str | None = None
    question: str | None = None
    answer: str | None = None

    def __post_init__(self) -> None:
        if self.type == "fact" and not self.text:
            raise ValueError(f"fact entry {self.id} is missing 'text'")
        if self.type == "quiz" and not (self.question and self.answer):
            raise ValueError(f"quiz entry {self.id} is missing 'question'/'answer'")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Entry:
        return cls(
            id=data["id"],
            type=data["type"],
            source_url=data["source_url"],
            source_excerpt=data["source_excerpt"],
            text=data.get("text"),
            question=data.get("question"),
            answer=data.get("answer"),
        )

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "source_url": self.source_url,
            "source_excerpt": self.source_excerpt,
        }
        if self.type == "fact":
            data["text"] = self.text
        else:
            data["question"] = self.question
            data["answer"] = self.answer
        return data
