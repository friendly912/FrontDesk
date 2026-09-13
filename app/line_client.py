import base64
import hashlib
import hmac

import httpx

from .config import get_settings

REPLY_URL = "https://api.line.me/v2/bot/message/reply"


def is_valid_line_signature(body: bytes, signature: str) -> bool:
    settings = get_settings()
    if not settings.validate_line_signature:
        return True
    digest = hmac.new(
        settings.line_channel_secret.encode("utf-8"), body, hashlib.sha256
    ).digest()
    expected = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected, signature)


def reply_text(reply_token: str, text: str) -> None:
    settings = get_settings()
    response = httpx.post(
        REPLY_URL,
        headers={
            "Authorization": f"Bearer {settings.line_channel_access_token}",
            "Content-Type": "application/json",
        },
        json={"replyToken": reply_token, "messages": [{"type": "text", "text": text}]},
        timeout=10.0,
    )
    response.raise_for_status()
