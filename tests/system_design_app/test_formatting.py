from system_design_app.formatting import format_message
from system_design_app.models import Entry


def test_format_fact_message_includes_text_and_source():
    entry = Entry(
        id=1,
        type="fact",
        source_url="https://example.com/article",
        source_excerpt="a short excerpt",
        text="a fact about caching",
    )

    message = format_message(entry)

    assert "a fact about caching" in message
    assert "a short excerpt" in message
    assert "https://example.com/article" in message


def test_format_quiz_message_includes_question_and_answer():
    entry = Entry(
        id=2,
        type="quiz",
        source_url="https://example.com/article",
        source_excerpt="a short excerpt",
        question="what is sharding?",
        answer="splitting rows across nodes",
    )

    message = format_message(entry)

    assert "what is sharding?" in message
    assert "splitting rows across nodes" in message
    assert "https://example.com/article" in message
