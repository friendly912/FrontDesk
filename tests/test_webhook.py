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
    monkeypatch.setenv("VALIDATE_TWILIO_SIGNATURE", "false")

    from app.config import get_settings
    from app.shops import load_shop

    get_settings.cache_clear()
    load_shop.cache_clear()
    yield
    get_settings.cache_clear()
    load_shop.cache_clear()


def test_webhook_replies_and_logs_booking(monkeypatch):
    import app.main as main_module

    captured = {}

    def fake_append(shop, from_number, message_body, received_at=None):
        captured["shop_id"] = shop.shop_id
        captured["from_number"] = from_number
        captured["message_body"] = message_body

    monkeypatch.setattr(main_module, "append_booking_row", fake_append)

    client = TestClient(main_module.app)
    response = client.post(
        "/webhook/whatsapp/acme-cuts",
        data={"From": "whatsapp:+15551234567", "Body": "hey are you open tomorrow?"},
    )

    assert response.status_code == 200
    assert "Tue-Sat, 9-6" in response.text
    assert "https://example.com/book" in response.text
    assert captured == {
        "shop_id": "acme-cuts",
        "from_number": "whatsapp:+15551234567",
        "message_body": "hey are you open tomorrow?",
    }


def test_webhook_unknown_shop_returns_404():
    import app.main as main_module

    client = TestClient(main_module.app)
    response = client.post(
        "/webhook/whatsapp/does-not-exist",
        data={"From": "whatsapp:+15551234567", "Body": "hi"},
    )

    assert response.status_code == 404


def test_webhook_still_replies_when_sheets_append_fails(monkeypatch):
    import app.main as main_module

    def failing_append(*args, **kwargs):
        raise RuntimeError("sheets api down")

    monkeypatch.setattr(main_module, "append_booking_row", failing_append)

    client = TestClient(main_module.app)
    response = client.post(
        "/webhook/whatsapp/acme-cuts",
        data={"From": "whatsapp:+15551234567", "Body": "hi"},
    )

    assert response.status_code == 200
    assert "Tue-Sat, 9-6" in response.text
