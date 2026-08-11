from pathlib import Path

import pytest

from system_design_app.config import ConfigError, load_config


def _write_env(tmp_path: Path, content: str) -> Path:
    env_file = tmp_path / ".env"
    env_file.write_text(content, encoding="utf-8")
    return env_file


def test_load_config_reads_required_and_optional_fields(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    env_file = _write_env(
        tmp_path,
        "TELEGRAM_BOT_TOKEN=abc123\nTELEGRAM_CHAT_ID=999\nANTHROPIC_API_KEY=sk-test\n",
    )

    cfg = load_config(env_file=env_file)

    assert cfg.telegram_bot_token == "abc123"
    assert cfg.telegram_chat_id == "999"
    assert cfg.anthropic_api_key == "sk-test"
    assert cfg.anthropic_model == "claude-sonnet-5"


def test_load_config_missing_token_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    env_file = _write_env(tmp_path, "TELEGRAM_CHAT_ID=999\n")

    with pytest.raises(ConfigError):
        load_config(env_file=env_file)


def test_load_config_blank_anthropic_key_is_none(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    env_file = _write_env(
        tmp_path,
        "TELEGRAM_BOT_TOKEN=abc123\nTELEGRAM_CHAT_ID=999\nANTHROPIC_API_KEY=\n",
    )

    cfg = load_config(env_file=env_file)

    assert cfg.anthropic_api_key is None
