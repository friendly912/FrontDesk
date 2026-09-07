from twilio.request_validator import RequestValidator

from .config import get_settings


def is_valid_twilio_request(url: str, form_params: dict, signature: str) -> bool:
    settings = get_settings()
    if not settings.validate_twilio_signature:
        return True
    validator = RequestValidator(settings.twilio_auth_token)
    return validator.validate(url, form_params, signature)
