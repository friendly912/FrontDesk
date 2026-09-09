import logging
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from twilio.twiml.messaging_response import MessagingResponse

from .bookings import append_booking_row
from .config import get_settings
from .replies import build_auto_reply
from .shops import ShopNotFoundError, load_shop
from .whatsapp import is_valid_twilio_request

logger = logging.getLogger("frontdesk")
app = FastAPI(title="Frontdesk")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/webhook/whatsapp/{shop_id}")
async def whatsapp_webhook(shop_id: str, request: Request):
    form = await request.form()
    params = dict(form)
    signature = request.headers.get("X-Twilio-Signature", "")

    settings = get_settings()
    url = (
        settings.public_base_url.rstrip("/") + request.url.path
        if settings.public_base_url
        else str(request.url)
    )
    if not is_valid_twilio_request(url, params, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    try:
        shop = load_shop(shop_id)
    except ShopNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown shop '{shop_id}'")

    from_number = params.get("From", "")
    message_body = params.get("Body", "").strip()

    try:
        append_booking_row(shop, from_number, message_body)
    except Exception:
        logger.exception("Failed to log booking row for shop %s", shop_id)

    twiml = MessagingResponse()
    twiml.message(build_auto_reply(shop))
    return Response(content=str(twiml), media_type="application/xml")


@app.get("/debug/bookings/{shop_id}")
def debug_bookings(
    shop_id: str,
    token: str | None = None,
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

    return PlainTextResponse(path.read_text())
