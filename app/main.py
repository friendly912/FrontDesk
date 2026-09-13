import logging
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from .bookings import append_booking_row
from .config import get_settings
from .debug_view import render_bookings_table
from .line_client import is_valid_line_signature, reply_text
from .replies import build_auto_reply
from .shops import ShopNotFoundError, load_shop

logger = logging.getLogger("frontdesk")
app = FastAPI(title="Frontdesk")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook/line/{shop_id}")
async def line_webhook(
    shop_id: str, request: Request, x_line_signature: str | None = Header(default=None)
):
    body = await request.body()
    if not is_valid_line_signature(body, x_line_signature or ""):
        raise HTTPException(status_code=403, detail="Invalid LINE signature")

    try:
        shop = load_shop(shop_id)
    except ShopNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown shop '{shop_id}'")

    payload = await request.json()
    for event in payload.get("events", []):
        message = event.get("message", {})
        if event.get("type") != "message" or message.get("type") != "text":
            continue

        from_id = event.get("source", {}).get("userId", "")
        message_body = message.get("text", "").strip()
        reply_token = event.get("replyToken")

        try:
            append_booking_row(shop, from_id, message_body)
        except Exception:
            logger.exception("Failed to log booking row for shop %s", shop_id)

        if reply_token:
            try:
                reply_text(reply_token, build_auto_reply(shop))
            except Exception:
                logger.exception("Failed to send LINE reply for shop %s", shop_id)

    return {"status": "ok"}


@app.get("/debug/bookings/{shop_id}")
def debug_bookings(
    shop_id: str,
    token: str | None = None,
    format: str | None = None,
    x_debug_token: str | None = Header(default=None),
):
    settings = get_settings()
    if settings.debug_token and settings.debug_token not in (token, x_debug_token):
        raise HTTPException(
            status_code=403, detail="Invalid or missing token (?token= or X-Debug-Token)"
        )

    try:
        shop = load_shop(shop_id)
    except ShopNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown shop '{shop_id}'")

    if settings.bookings_backend != "csv":
        raise HTTPException(
            status_code=404,
            detail="No local CSV file — BOOKINGS_BACKEND is not 'csv'",
        )

    path = Path(settings.local_data_dir) / shop.shop_id / "bookings.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No bookings logged yet for this shop")

    csv_text = path.read_text()
    if format == "csv":
        return PlainTextResponse(csv_text)
    return HTMLResponse(render_bookings_table(shop.name, csv_text))
