import pytest

from src.mail.mail import mail


@pytest.fixture(autouse=True)
def _no_live_mail_sending(monkeypatch):
    async def _noop_send_message(*args, **kwargs):
        return None

    monkeypatch.setattr(mail, "send_message", _noop_send_message)
