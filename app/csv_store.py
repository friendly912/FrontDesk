import csv
from datetime import datetime, timezone
from pathlib import Path

from .config import get_settings
from .shops import ShopConfig

HEADER = ["timestamp", "from", "message", "status"]


def _csv_path(shop: ShopConfig) -> Path:
    shop_dir = Path(get_settings().local_data_dir) / shop.shop_id
    shop_dir.mkdir(parents=True, exist_ok=True)
    return shop_dir / "bookings.csv"


def append_booking_row(
    shop: ShopConfig,
    from_number: str,
    message_body: str,
    received_at: datetime | None = None,
) -> None:
    received_at = received_at or datetime.now(timezone.utc)
    path = _csv_path(shop)
    is_new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new_file:
            writer.writerow(HEADER)
        writer.writerow(
            [received_at.strftime("%Y-%m-%d %H:%M"), from_number, message_body, "New"]
        )
