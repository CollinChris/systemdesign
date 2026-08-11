import json
from types import SimpleNamespace

import anthropic
import pytest

from system_design_app import generator
from system_design_app.generator import GenerationError, generate_entries


class _FakeMessages:
    def __init__(
        self, response_text: str | None = None, error: Exception | None = None
    ):
        self._response_text = response_text
        self._error = error

    def create(self, **kwargs):
        if self._error is not None:
            raise self._error
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=self._response_text)]
        )


class _FakeClient:
    def __init__(self, messages: _FakeMessages) -> None:
        self.messages = messages


def _patch_client(monkeypatch, messages: _FakeMessages) -> None:
    monkeypatch.setattr(
        generator.anthropic, "Anthropic", lambda api_key: _FakeClient(messages)
    )


def test_generate_entries_parses_valid_response(monkeypatch):
    payload = json.dumps(
        [
            {
                "type": "fact",
                "text": "new fact",
                "source_url": "https://example.com",
                "source_excerpt": "excerpt",
            },
            {
                "type": "quiz",
                "question": "q?",
                "answer": "a.",
                "source_url": "https://example.com",
                "source_excerpt": "excerpt",
            },
        ]
    )
    _patch_client(monkeypatch, _FakeMessages(response_text=payload))

    entries = generate_entries(
        api_key="sk-test",
        model="claude-sonnet-5",
        count=2,
        existing_entries=[],
        start_id=10,
    )

    assert [e.id for e in entries] == [10, 11]
    assert entries[0].type == "fact"
    assert entries[1].type == "quiz"


def test_generate_entries_skips_malformed_items(monkeypatch):
    payload = json.dumps(
        [
            {"type": "fact", "source_url": "u", "source_excerpt": "e"},  # missing text
            {
                "type": "fact",
                "text": "ok",
                "source_url": "https://example.com",
                "source_excerpt": "excerpt",
            },
        ]
    )
    _patch_client(monkeypatch, _FakeMessages(response_text=payload))

    entries = generate_entries(
        api_key="sk-test", model="m", count=2, existing_entries=[], start_id=1
    )

    assert len(entries) == 1
    assert entries[0].text == "ok"


def test_generate_entries_invalid_json_raises(monkeypatch):
    _patch_client(monkeypatch, _FakeMessages(response_text="not json"))

    with pytest.raises(GenerationError):
        generate_entries(
            api_key="sk-test", model="m", count=1, existing_entries=[], start_id=1
        )


def test_generate_entries_non_list_json_raises(monkeypatch):
    _patch_client(monkeypatch, _FakeMessages(response_text=json.dumps({"a": 1})))

    with pytest.raises(GenerationError):
        generate_entries(
            api_key="sk-test", model="m", count=1, existing_entries=[], start_id=1
        )


def test_generate_entries_api_error_raises_generation_error(monkeypatch):
    error = anthropic.APIConnectionError(request=SimpleNamespace())
    _patch_client(monkeypatch, _FakeMessages(error=error))

    with pytest.raises(GenerationError):
        generate_entries(
            api_key="sk-test", model="m", count=1, existing_entries=[], start_id=1
        )
