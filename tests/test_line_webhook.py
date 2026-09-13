import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _shop_fixture(tmp_path, monkeypatch):
    shops_dir = tmp_path / "shops"
    shops_dir.mkdir()
    (shops_dir / "acme-cuts.json").write_text(
        json.dumps(
            {
                "shop_id": "acme-cuts",
                "name": "Acme Cuts",
                "hours": "Tue-Sat, 9-6",
                "services": ["Trim", "Color"],
                "booking_link": "https://example.com/book",
                "google_sheet_id": "sheet123",
                "sheet_tab": "Bookings",
                "after_hours_note": "A person picks this up after 9am.",
            }
        )
    )

    monkeypatch.setenv("SHOPS_DIR", str(shops_dir))
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VALIDATE_LINE_SIGNATURE", "false")

    from app.config import get_settings
    from app.shops import load_shop

    get_settings.cache_clear()
    load_shop.cache_clear()
    yield
    get_settings.cache_clear()
    load_shop.cache_clear()


def _line_payload(text: str, reply_token: str = "reply-token-1", user_id: str = "U123"):
    return {
        "events": [
            {
                "type": "message",
                "replyToken": reply_token,
                "source": {"type": "user", "userId": user_id},
                "message": {"type": "text", "id": "1", "text": text},
            }
        ]
    }


def test_webhook_logs_booking_and_sends_line_reply(monkeypatch):
    import app.main as main_module

    logged = {}
    replied = {}

    def fake_append(shop, from_id, message_body, received_at=None):
        logged["shop_id"] = shop.shop_id
        logged["from_id"] = from_id
        logged["message_body"] = message_body

    def fake_reply(reply_token, text):
        replied["reply_token"] = reply_token
        replied["text"] = text

    monkeypatch.setattr(main_module, "append_booking_row", fake_append)
    monkeypatch.setattr(main_module, "reply_text", fake_reply)

    client = TestClient(main_module.app)
    response = client.post(
        "/webhook/line/acme-cuts",
        json=_line_payload("hey are you open tomorrow?"),
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert logged == {
        "shop_id": "acme-cuts",
        "from_id": "U123",
        "message_body": "hey are you open tomorrow?",
    }
    assert replied["reply_token"] == "reply-token-1"
    assert "Tue-Sat, 9-6" in replied["text"]
    assert "https://example.com/book" in replied["text"]


def test_webhook_unknown_shop_returns_404():
    import app.main as main_module

    client = TestClient(main_module.app)
    response = client.post("/webhook/line/does-not-exist", json=_line_payload("hi"))

    assert response.status_code == 404


def test_webhook_ignores_non_text_events(monkeypatch):
    import app.main as main_module

    calls = []
    monkeypatch.setattr(
        main_module, "append_booking_row", lambda *a, **k: calls.append("append")
    )
    monkeypatch.setattr(main_module, "reply_text", lambda *a, **k: calls.append("reply"))

    client = TestClient(main_module.app)
    payload = {
        "events": [
            {
                "type": "message",
                "replyToken": "rt",
                "source": {"type": "user", "userId": "U123"},
                "message": {"type": "sticker", "id": "1"},
            }
        ]
    }
    response = client.post("/webhook/line/acme-cuts", json=payload)

    assert response.status_code == 200
    assert calls == []


def test_webhook_still_returns_ok_when_reply_fails(monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(main_module, "append_booking_row", lambda *a, **k: None)

    def failing_reply(*args, **kwargs):
        raise RuntimeError("LINE API down")

    monkeypatch.setattr(main_module, "reply_text", failing_reply)

    client = TestClient(main_module.app)
    response = client.post(
        "/webhook/line/acme-cuts", json=_line_payload("hi")
    )

    assert response.status_code == 200


def test_webhook_verify_request_with_no_events_returns_ok():
    import app.main as main_module

    client = TestClient(main_module.app)
    response = client.post("/webhook/line/acme-cuts", json={"events": []})

    assert response.status_code == 200


def test_webhook_rejects_invalid_signature(monkeypatch):
    monkeypatch.setenv("VALIDATE_LINE_SIGNATURE", "true")
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "shh")

    from app.config import get_settings

    get_settings.cache_clear()

    import app.main as main_module

    client = TestClient(main_module.app)
    response = client.post(
        "/webhook/line/acme-cuts",
        json=_line_payload("hi"),
        headers={"X-Line-Signature": "not-a-valid-signature"},
    )

    assert response.status_code == 403


def test_webhook_accepts_valid_signature(monkeypatch):
    monkeypatch.setenv("VALIDATE_LINE_SIGNATURE", "true")
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "shh")

    from app.config import get_settings

    get_settings.cache_clear()

    import app.main as main_module

    monkeypatch.setattr(main_module, "append_booking_row", lambda *a, **k: None)
    monkeypatch.setattr(main_module, "reply_text", lambda *a, **k: None)

    body = json.dumps(_line_payload("hi")).encode("utf-8")
    signature = base64.b64encode(
        hmac.new(b"shh", body, hashlib.sha256).digest()
    ).decode("utf-8")

    client = TestClient(main_module.app)
    response = client.post(
        "/webhook/line/acme-cuts",
        content=body,
        headers={
            "X-Line-Signature": signature,
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 200
