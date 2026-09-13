from datetime import datetime

from . import csv_store, sheets
from .config import get_settings
from .shops import ShopConfig


def append_booking_row(
    shop: ShopConfig,
    from_id: str,
    message_body: str,
    received_at: datetime | None = None,
) -> None:
    backend = get_settings().bookings_backend
    if backend == "csv":
        csv_store.append_booking_row(shop, from_id, message_body, received_at)
    elif backend == "google_sheets":
        sheets.append_booking_row(shop, from_id, message_body, received_at)
    else:
        raise ValueError(f"Unknown BOOKINGS_BACKEND '{backend}'")
