import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from twilio.twiml.messaging_response import MessagingResponse

from .config import get_settings
from .replies import build_auto_reply
from .sheets import append_booking_row
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
