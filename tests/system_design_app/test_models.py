import pytest

from system_design_app.models import Entry


def test_fact_entry_round_trips_through_dict():
    entry = Entry(
        id=1,
        type="fact",
        source_url="https://example.com",
        source_excerpt="excerpt",
        text="a fact",
    )

    data = entry.to_dict()

    assert data == {
        "id": 1,
        "type": "fact",
        "source_url": "https://example.com",
        "source_excerpt": "excerpt",
        "text": "a fact",
    }
    assert Entry.from_dict(data) == entry


def test_quiz_entry_round_trips_through_dict():
    entry = Entry(
        id=2,
        type="quiz",
        source_url="https://example.com",
        source_excerpt="excerpt",
        question="q?",
        answer="a.",
    )

    data = entry.to_dict()

    assert data == {
        "id": 2,
        "type": "quiz",
        "source_url": "https://example.com",
        "source_excerpt": "excerpt",
        "question": "q?",
        "answer": "a.",
    }
    assert Entry.from_dict(data) == entry


def test_fact_entry_missing_text_raises():
    with pytest.raises(ValueError):
        Entry(id=1, type="fact", source_url="u", source_excerpt="e")


def test_quiz_entry_missing_answer_raises():
    with pytest.raises(ValueError):
        Entry(id=1, type="quiz", source_url="u", source_excerpt="e", question="q?")
