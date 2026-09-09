import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _env(tmp_path, monkeypatch):
    shops_dir = tmp_path / "shops"
    shops_dir.mkdir()
    (shops_dir / "acme-cuts.json").write_text(
        json.dumps(
            {
                "shop_id": "acme-cuts",
                "name": "Acme Cuts",
                "hours": "Tue-Sat, 9-6",
                "booking_link": "https://example.com/book",
                "google_sheet_id": "sheet123",
            }
        )
    )

    monkeypatch.setenv("SHOPS_DIR", str(shops_dir))
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VALIDATE_TWILIO_SIGNATURE", "false")
    monkeypatch.delenv("DEBUG_TOKEN", raising=False)

    from app.config import get_settings
    from app.shops import load_shop

    get_settings.cache_clear()
    load_shop.cache_clear()
    yield
    get_settings.cache_clear()
    load_shop.cache_clear()


def test_debug_bookings_404_when_no_rows_yet():
    import app.main as main_module

    client = TestClient(main_module.app)
    response = client.get("/debug/bookings/acme-cuts")

    assert response.status_code == 404


def test_debug_bookings_returns_html_table_by_default():
    import app.main as main_module
    from app.csv_store import append_booking_row
    from app.shops import load_shop

    append_booking_row(load_shop("acme-cuts"), "whatsapp:+15551234567", "hi there")

    client = TestClient(main_module.app)
    response = client.get("/debug/bookings/acme-cuts")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "<table>" in response.text
    assert "Acme Cuts" in response.text
    assert "whatsapp:+15551234567" in response.text
    assert "hi there" in response.text


def test_debug_bookings_escapes_message_content():
    import app.main as main_module
    from app.csv_store import append_booking_row
    from app.shops import load_shop

    append_booking_row(
        load_shop("acme-cuts"),
        "whatsapp:+15551234567",
        "<script>alert(1)</script>",
    )

    client = TestClient(main_module.app)
    response = client.get("/debug/bookings/acme-cuts")

    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text


def test_debug_bookings_format_csv_returns_raw_csv():
    import app.main as main_module
    from app.csv_store import append_booking_row
    from app.shops import load_shop

    append_booking_row(load_shop("acme-cuts"), "whatsapp:+15551234567", "hi there")

    client = TestClient(main_module.app)
    response = client.get("/debug/bookings/acme-cuts?format=csv")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert response.text.splitlines()[0] == "timestamp,from,message,status"
    assert "<table>" not in response.text


def test_debug_bookings_unknown_shop_returns_404():
    import app.main as main_module

    client = TestClient(main_module.app)
    response = client.get("/debug/bookings/does-not-exist")

    assert response.status_code == 404


def test_debug_bookings_requires_token_when_configured(monkeypatch):
    monkeypatch.setenv("DEBUG_TOKEN", "s3cret")

    from app.config import get_settings

    get_settings.cache_clear()

    import app.main as main_module
    from app.csv_store import append_booking_row
    from app.shops import load_shop

    append_booking_row(load_shop("acme-cuts"), "whatsapp:+15551234567", "hi there")

    client = TestClient(main_module.app)

    unauthorized = client.get("/debug/bookings/acme-cuts")
    assert unauthorized.status_code == 403

    authorized_header = client.get(
        "/debug/bookings/acme-cuts", headers={"X-Debug-Token": "s3cret"}
    )
    assert authorized_header.status_code == 200
    assert "hi there" in authorized_header.text

    authorized_query = client.get("/debug/bookings/acme-cuts?token=s3cret")
    assert authorized_query.status_code == 200
    assert "hi there" in authorized_query.text

    wrong_query = client.get("/debug/bookings/acme-cuts?token=nope")
    assert wrong_query.status_code == 403
