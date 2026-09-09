import csv

import pytest


@pytest.fixture(autouse=True)
def _local_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCAL_DATA_DIR", str(tmp_path / "data"))

    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _shop():
    from app.shops import ShopConfig

    return ShopConfig(
        shop_id="acme-cuts",
        name="Acme Cuts",
        hours="Tue-Sat, 9-6",
        booking_link="https://example.com/book",
        google_sheet_id="unused",
    )


def test_append_booking_row_creates_file_with_header_and_row():
    from app.csv_store import append_booking_row

    append_booking_row(_shop(), "whatsapp:+15551234567", "hey are you open tomorrow?")

    from app.config import get_settings

    path = get_settings().local_data_dir
    csv_path = f"{path}/acme-cuts/bookings.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert rows[0] == ["timestamp", "from", "message", "status"]
    assert rows[1][1:] == ["whatsapp:+15551234567", "hey are you open tomorrow?", "New"]


def test_append_booking_row_appends_without_duplicating_header():
    from app.csv_store import append_booking_row

    shop = _shop()
    append_booking_row(shop, "whatsapp:+15551111111", "first")
    append_booking_row(shop, "whatsapp:+15552222222", "second")

    from app.config import get_settings

    path = get_settings().local_data_dir
    csv_path = f"{path}/acme-cuts/bookings.csv"
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))

    assert len(rows) == 3
    assert rows[0] == ["timestamp", "from", "message", "status"]
