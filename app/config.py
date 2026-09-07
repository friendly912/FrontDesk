from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    google_service_account_file: str = "./secrets/service-account.json"
    shops_dir: str = "./shops"
    validate_twilio_signature: bool = True
    # Set when the app sits behind a proxy/tunnel (ngrok, load balancer) so the
    # signature check validates against the URL Twilio actually posted to.
    public_base_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
