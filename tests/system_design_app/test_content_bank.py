import json

import pytest

from system_design_app.content_bank import (
    ContentBankError,
    load_bank,
    load_state,
    next_id,
    save_bank,
    save_state,
)
from system_design_app.models import Entry

FACT = {
    "id": 1,
    "type": "fact",
    "source_url": "https://example.com",
    "source_excerpt": "excerpt",
    "text": "a fact",
}


def test_load_bank_missing_file_raises(tmp_path):
    with pytest.raises(ContentBankError):
        load_bank(tmp_path / "missing.json")


def test_load_bank_invalid_json_raises(tmp_path):
    path = tmp_path / "bank.json"
    path.write_text("not json", encoding="utf-8")

    with pytest.raises(ContentBankError):
        load_bank(path)


def test_load_bank_non_list_raises(tmp_path):
    path = tmp_path / "bank.json"
    path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    with pytest.raises(ContentBankError):
        load_bank(path)


def test_save_and_load_bank_round_trip(tmp_path):
    path = tmp_path / "nested" / "bank.json"
    entries = [Entry.from_dict(FACT)]

    save_bank(path, entries)
    loaded = load_bank(path)

    assert loaded == entries


def test_next_id_increments_past_max():
    entries = [Entry.from_dict(FACT), Entry.from_dict({**FACT, "id": 5})]

    assert next_id(entries) == 6


def test_next_id_on_empty_bank_is_one():
    assert next_id([]) == 1


def test_load_state_missing_file_is_empty(tmp_path):
    assert load_state(tmp_path / "missing.json") == set()


def test_load_state_corrupt_file_is_empty(tmp_path):
    path = tmp_path / "state.json"
    path.write_text("not json", encoding="utf-8")

    assert load_state(path) == set()


def test_save_and_load_state_round_trip(tmp_path):
    path = tmp_path / "nested" / "state.json"

    save_state(path, {3, 1, 2})

    assert load_state(path) == {1, 2, 3}
