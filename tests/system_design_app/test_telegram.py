import httpx
import pytest

from system_design_app import telegram


class _FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self.text = text

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            request = httpx.Request("POST", "https://api.telegram.org/fake")
            response = httpx.Response(self.status_code, text=self.text, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)


def test_send_message_success(monkeypatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return _FakeResponse(200)

    monkeypatch.setattr(telegram.httpx, "post", fake_post)

    telegram.send_message("TOKEN", "12345", "hello")

    assert captured["url"] == "https://api.telegram.org/botTOKEN/sendMessage"
    assert captured["json"] == {"chat_id": "12345", "text": "hello"}


def test_send_message_http_error_raises_telegram_error(monkeypatch):
    def fake_post(url, json, timeout):
        return _FakeResponse(403, text="Forbidden")

    monkeypatch.setattr(telegram.httpx, "post", fake_post)

    with pytest.raises(telegram.TelegramError):
        telegram.send_message("TOKEN", "12345", "hello")


def test_send_message_network_error_raises_telegram_error(monkeypatch):
    def fake_post(url, json, timeout):
        raise httpx.ConnectError("boom", request=httpx.Request("POST", url))

    monkeypatch.setattr(telegram.httpx, "post", fake_post)

    with pytest.raises(telegram.TelegramError):
        telegram.send_message("TOKEN", "12345", "hello")
