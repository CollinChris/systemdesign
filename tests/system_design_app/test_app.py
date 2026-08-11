from system_design_app import app
from system_design_app.config import Config
from system_design_app.models import Entry

FACT = Entry(
    id=1,
    type="fact",
    source_url="https://example.com",
    source_excerpt="excerpt",
    text="a fact",
)
FACT_2 = Entry(
    id=2,
    type="fact",
    source_url="https://example.com",
    source_excerpt="excerpt",
    text="another fact",
)


def test_get_unsent_filters_sent_ids():
    unsent, sent_ids = app.get_unsent([FACT, FACT_2], {1})

    assert unsent == [FACT_2]
    assert sent_ids == {1}


def test_get_unsent_reshuffles_when_pool_exhausted():
    unsent, sent_ids = app.get_unsent([FACT, FACT_2], {1, 2})

    assert unsent == [FACT, FACT_2]
    assert sent_ids == set()


def _no_op_config(gemini_api_key=None):
    return Config(
        telegram_bot_token="TOKEN",
        telegram_chat_id="123",
        gemini_api_key=gemini_api_key,
    )


def test_run_sends_entry_and_persists_state(monkeypatch):
    sent = {}
    saved_state = {}

    monkeypatch.setattr(app, "load_config", lambda: _no_op_config())
    monkeypatch.setattr(app, "load_bank", lambda path: [FACT])
    monkeypatch.setattr(app, "load_state", lambda path: set())
    monkeypatch.setattr(
        app, "send_message", lambda token, chat_id, text: sent.update(text=text)
    )
    monkeypatch.setattr(
        app, "save_state", lambda path, ids: saved_state.update(ids=ids)
    )

    app.run()

    assert "a fact" in sent["text"]
    assert saved_state["ids"] == {1}


def test_run_tops_up_via_generator_when_stock_is_low(monkeypatch):
    generated = [
        Entry(
            id=2,
            type="fact",
            source_url="u",
            source_excerpt="e",
            text="generated fact",
        )
    ]
    saved_bank = {}

    monkeypatch.setattr(
        app, "load_config", lambda: _no_op_config(gemini_api_key="sk-test")
    )
    monkeypatch.setattr(app, "load_bank", lambda path: [FACT])
    monkeypatch.setattr(app, "load_state", lambda path: set())
    monkeypatch.setattr(app, "send_message", lambda token, chat_id, text: None)
    monkeypatch.setattr(app, "save_state", lambda path, ids: None)
    monkeypatch.setattr(app, "generate_entries", lambda **kwargs: generated)
    monkeypatch.setattr(
        app, "save_bank", lambda path, entries: saved_bank.update(entries=entries)
    )
    monkeypatch.setattr(app, "LOW_STOCK_THRESHOLD", 5)

    app.run()

    assert saved_bank["entries"] == [FACT] + generated
