import json
from types import SimpleNamespace

import pytest
from google.genai import errors

from system_design_app import generator
from system_design_app.generator import GenerationError, generate_entries

VALID = json.dumps(
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


class _FakeModels:
    """Scripted responses: each item is either a text payload or an exception.
    Records the model name of every call."""

    def __init__(self, script: list) -> None:
        self._script = list(script)
        self.calls: list[str] = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs["model"])
        item = self._script.pop(0) if self._script else VALID
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(text=item)


class _FakeClient:
    def __init__(self, models: _FakeModels) -> None:
        self.models = models


def _patch_client(monkeypatch, models: _FakeModels) -> None:
    monkeypatch.setattr(generator.genai, "Client", lambda **kwargs: _FakeClient(models))


def _err(code: int, message: str = "boom") -> errors.APIError:
    cls = errors.ServerError if code >= 500 else errors.ClientError
    return cls(code=code, response_json={"error": {"code": code, "message": message}})


def _gen(**overrides):
    kwargs = {
        "api_key": "test-key",
        "model": "gemini-flash-latest",
        "count": 2,
        "existing_entries": [],
        "start_id": 10,
        "fallback_model": "gemini-flash-lite-latest",
        "sleep": lambda s: None,
    }
    kwargs.update(overrides)
    return generate_entries(**kwargs)


def test_generate_entries_parses_valid_response(monkeypatch):
    models = _FakeModels([VALID])
    _patch_client(monkeypatch, models)

    entries = _gen()

    assert [e.id for e in entries] == [10, 11]
    assert entries[0].type == "fact" and entries[1].type == "quiz"
    assert models.calls == ["gemini-flash-latest"]


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
    _patch_client(monkeypatch, _FakeModels([payload]))

    entries = _gen()

    assert len(entries) == 1 and entries[0].text == "ok"


def test_generate_entries_invalid_json_raises(monkeypatch):
    _patch_client(monkeypatch, _FakeModels(["not json"]))
    with pytest.raises(GenerationError):
        _gen()


def test_generate_entries_non_list_json_raises(monkeypatch):
    _patch_client(monkeypatch, _FakeModels([json.dumps({"a": 1})]))
    with pytest.raises(GenerationError):
        _gen()


def test_all_malformed_raises(monkeypatch):
    _patch_client(monkeypatch, _FakeModels([json.dumps([{"type": "fact"}])]))
    with pytest.raises(GenerationError):
        _gen()


def test_retries_transient_503_then_succeeds(monkeypatch):
    slept: list[float] = []
    models = _FakeModels([_err(503, "high demand"), _err(503, "high demand"), VALID])
    _patch_client(monkeypatch, models)

    entries = _gen(sleep=slept.append)

    assert len(entries) == 2
    assert models.calls == ["gemini-flash-latest"] * 3
    assert slept == [10.0, 20.0]  # backoff between the two failures


def test_falls_back_to_second_model_after_exhausting_retries(monkeypatch):
    models = _FakeModels([_err(503)] * 3 + [VALID])
    _patch_client(monkeypatch, models)

    entries = _gen(max_attempts=3)

    assert len(entries) == 2
    assert models.calls == ["gemini-flash-latest"] * 3 + ["gemini-flash-lite-latest"]


def test_daily_quota_switches_model_without_retrying(monkeypatch):
    quota = _err(
        429, "Quota exceeded ... GenerateRequestsPerDayPerProjectPerModel-FreeTier"
    )
    models = _FakeModels([quota, VALID])
    _patch_client(monkeypatch, models)

    _gen()

    assert models.calls == ["gemini-flash-latest", "gemini-flash-lite-latest"]


def test_unknown_model_404_switches_model(monkeypatch):
    models = _FakeModels([_err(404, "not found"), VALID])
    _patch_client(monkeypatch, models)

    _gen()

    assert models.calls == ["gemini-flash-latest", "gemini-flash-lite-latest"]


def test_every_model_failing_raises_with_all_failures_listed(monkeypatch):
    models = _FakeModels([_err(503)] * 6)
    _patch_client(monkeypatch, models)

    with pytest.raises(GenerationError) as exc:
        _gen(max_attempts=3)

    assert models.calls.count("gemini-flash-latest") == 3
    assert models.calls.count("gemini-flash-lite-latest") == 3
    assert "every model" in str(exc.value) and "503" in str(exc.value)


def test_non_retryable_client_error_raises_immediately(monkeypatch):
    models = _FakeModels([_err(400, "credit balance too low")])
    _patch_client(monkeypatch, models)

    with pytest.raises(GenerationError):
        _gen()

    assert models.calls == ["gemini-flash-latest"]


def test_no_fallback_when_same_as_primary(monkeypatch):
    models = _FakeModels([_err(503)] * 2)
    _patch_client(monkeypatch, models)

    with pytest.raises(GenerationError):
        _gen(fallback_model="gemini-flash-latest", max_attempts=2)

    assert models.calls == ["gemini-flash-latest"] * 2
