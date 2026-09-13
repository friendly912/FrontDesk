from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    line_channel_secret: str = ""
    line_channel_access_token: str = ""
    validate_line_signature: bool = True
    google_service_account_file: str = "./secrets/service-account.json"
    shops_dir: str = "./shops"
    # "csv" (default) needs no external account and writes to local_data_dir;
    # "google_sheets" requires a Google Cloud service account.
    bookings_backend: str = "csv"
    local_data_dir: str = "./data"
    # If set, /debug/bookings/{shop_id} requires this value in an
    # X-Debug-Token header. Leave unset only for local dev — the endpoint
    # returns raw customer LINE user IDs and messages.
    debug_token: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
