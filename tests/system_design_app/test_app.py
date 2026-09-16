import datetime as dt

import pytest

from system_design_app import app
from system_design_app.config import Config
from system_design_app.generator import GenerationError
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
TODAY = dt.date(2026, 9, 16)


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


def _wire(monkeypatch, *, bank, sent_ids=None, last_sent=None, gemini_key=None):
    """Patch every side effect; return dicts that record what happened."""
    sent_ids = set(sent_ids or ())
    sent: list[str] = []
    saved_state: dict = {}
    saved_bank: dict = {}
    monkeypatch.setattr(app, "load_config", lambda: _no_op_config(gemini_key))
    monkeypatch.setattr(app, "today_sg", lambda: TODAY)
    monkeypatch.setattr(app, "load_bank", lambda path: list(bank))
    monkeypatch.setattr(app, "load_state", lambda path: set(sent_ids))
    monkeypatch.setattr(app, "load_last_sent_date", lambda path: last_sent)
    monkeypatch.setattr(
        app, "send_message", lambda token, chat_id, text: sent.append(text)
    )
    monkeypatch.setattr(
        app,
        "save_state",
        lambda path, ids, last_sent_date=None: saved_state.update(
            ids=ids, last_sent_date=last_sent_date
        ),
    )
    monkeypatch.setattr(
        app, "save_bank", lambda path, entries: saved_bank.update(entries=entries)
    )
    return sent, saved_state, saved_bank


def test_run_sends_entry_and_persists_state_with_today(monkeypatch):
    sent, saved_state, _ = _wire(monkeypatch, bank=[FACT])

    app.run()

    assert len(sent) == 1 and "a fact" in sent[0]
    assert saved_state == {"ids": {1}, "last_sent_date": TODAY}


def test_run_skips_when_already_sent_today(monkeypatch):
    sent, saved_state, _ = _wire(monkeypatch, bank=[FACT], last_sent=TODAY)

    app.run()

    assert sent == [] and saved_state == {}


def test_force_overrides_the_once_a_day_guard(monkeypatch):
    sent, _, _ = _wire(monkeypatch, bank=[FACT], last_sent=TODAY)

    app.run(force=True)

    assert len(sent) == 1


def test_run_tops_up_via_generator_when_stock_is_low(monkeypatch):
    generated = [
        Entry(
            id=3, type="fact", source_url="u", source_excerpt="e", text="generated fact"
        )
    ]
    calls: dict = {}
    _, _, saved_bank = _wire(monkeypatch, bank=[FACT, FACT_2], gemini_key="sk-test")
    monkeypatch.setattr(app, "LOW_STOCK_THRESHOLD", 5)
    monkeypatch.setattr(app, "GENERATE_BATCH_SIZE", 10)

    def fake_generate(**kwargs):
        calls.update(kwargs)
        return generated

    monkeypatch.setattr(app, "generate_entries", fake_generate)

    app.run()

    assert saved_bank["entries"] == [FACT, FACT_2] + generated
    assert calls["count"] == 10 and calls["start_id"] == 3
    assert calls["fallback_model"] == "gemini-flash-lite-latest"


def test_top_up_triggers_before_pool_reset(monkeypatch):
    """Every entry already sent: the old code reset the pool first and saw a
    full bank, so it never generated. The count must be taken pre-reset."""
    calls: list = []
    _wire(monkeypatch, bank=[FACT, FACT_2], sent_ids={1, 2}, gemini_key="sk-test")
    monkeypatch.setattr(app, "LOW_STOCK_THRESHOLD", 3)
    monkeypatch.setattr(app, "generate_entries", lambda **kw: calls.append(kw) or [])

    app.run()

    assert len(calls) == 1


def test_no_generation_when_stock_is_fine(monkeypatch):
    bank = [
        Entry(id=i, type="fact", source_url="u", source_excerpt="e", text=f"f{i}")
        for i in range(1, 12)
    ]
    _wire(monkeypatch, bank=bank, gemini_key="sk-test")
    monkeypatch.setattr(app, "LOW_STOCK_THRESHOLD", 7)
    monkeypatch.setattr(
        app, "generate_entries", lambda **kw: pytest.fail("should not generate")
    )

    app.run()


def test_generation_failure_still_sends_then_notes_and_raises(monkeypatch):
    sent, saved_state, saved_bank = _wire(
        monkeypatch, bank=[FACT], gemini_key="sk-test"
    )
    monkeypatch.setattr(app, "LOW_STOCK_THRESHOLD", 5)

    def boom(**kwargs):
        raise GenerationError("Gemini API request failed on every model: 503; 503")

    monkeypatch.setattr(app, "generate_entries", boom)

    with pytest.raises(GenerationError):
        app.run()

    # The day's entry went out first, state was saved, then the warning note.
    assert len(sent) == 2
    assert "a fact" in sent[0]
    assert "content generation failed" in sent[1] and "503" in sent[1]
    assert saved_state["last_sent_date"] == TODAY
    assert saved_bank == {}


def test_main_exit_codes(monkeypatch):
    monkeypatch.setattr(app.sys, "argv", ["system-design-app"])
    monkeypatch.setattr(
        app, "run", lambda force=False: (_ for _ in ()).throw(GenerationError("x"))
    )
    with pytest.raises(SystemExit) as exc:
        app.main()
    assert exc.value.code == 2
