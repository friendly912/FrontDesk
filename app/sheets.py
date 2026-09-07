from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

from .config import get_settings
from .shops import ShopConfig

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

_service = None


def _get_service():
    global _service
    if _service is None:
        creds = service_account.Credentials.from_service_account_file(
            get_settings().google_service_account_file, scopes=SCOPES
        )
        _service = build("sheets", "v4", credentials=creds)
    return _service


def append_booking_row(
    shop: ShopConfig,
    from_number: str,
    message_body: str,
    received_at: datetime | None = None,
) -> None:
    received_at = received_at or datetime.now(timezone.utc)
    row = [received_at.strftime("%Y-%m-%d %H:%M"), from_number, message_body, "New"]
    _get_service().spreadsheets().values().append(
        spreadsheetId=shop.google_sheet_id,
        range=f"{shop.sheet_tab}!A:D",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()
