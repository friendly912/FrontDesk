from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    google_service_account_file: str = "./secrets/service-account.json"
    shops_dir: str = "./shops"
    validate_twilio_signature: bool = True
    # "csv" (default) needs no external account and writes to local_data_dir;
    # "google_sheets" requires a Google Cloud service account.
    bookings_backend: str = "csv"
    local_data_dir: str = "./data"
    # Set when the app sits behind a proxy/tunnel (ngrok, load balancer) so the
    # signature check validates against the URL Twilio actually posted to.
    public_base_url: str = ""
    # If set, /debug/bookings/{shop_id} requires this value in an
    # X-Debug-Token header. Leave unset only for local dev — the endpoint
    # returns raw customer phone numbers and messages.
    debug_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
