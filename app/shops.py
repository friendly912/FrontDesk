import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from .config import get_settings


class ShopConfig(BaseModel):
    shop_id: str
    name: str
    hours: str
    services: list[str] = []
    booking_link: str
    google_sheet_id: str
    sheet_tab: str = "Bookings"
    after_hours_note: str = ""


class ShopNotFoundError(Exception):
    pass


@lru_cache(maxsize=None)
def load_shop(shop_id: str) -> ShopConfig:
    path = Path(get_settings().shops_dir) / f"{shop_id}.json"
    if not path.exists():
        raise ShopNotFoundError(shop_id)
    return ShopConfig(**json.loads(path.read_text()))
