
from functools import lru_cache
import math

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./dev.db"

    # PostgreSQL SSL; enabled by default, with optional CA certificate.
    db_ssl_enabled: bool = True
    db_ssl_ca_file: str | None = None

    # JWT Authentication
    jwt_secret: str = "CHANGE_ME_FOR_LOCAL_DEVELOPMENT_ONLY"
    jwt_algorithm: str = "HS256"
    jwt_minutes: int = 60

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Application environment
    environment: str = "development"

    # Sarvam credentials and model selection (server-side only)
    sarvam_api_key: SecretStr | None = None
    sarvam_stt_model: str = "saaras:v4"
    sarvam_chat_model: str = "sarvam-105b"
    sarvam_timeout_seconds: float = 30.0
    sarvam_upload_idle_timeout_seconds: float = 10.0
    sarvam_upload_max_duration_seconds: float = 120.0

    @field_validator("sarvam_upload_idle_timeout_seconds")
    @classmethod
    def validate_upload_idle_timeout(cls, value: float) -> float:
        if not math.isfinite(value) or not 0 < value <= 60:
            raise ValueError("SARVAM_UPLOAD_IDLE_TIMEOUT_SECONDS must be greater than 0 and at most 60.")
        return value

    @field_validator("sarvam_upload_max_duration_seconds")
    @classmethod
    def validate_upload_max_duration(cls, value: float) -> float:
        if not math.isfinite(value) or not 0 < value <= 600:
            raise ValueError("SARVAM_UPLOAD_MAX_DURATION_SECONDS must be greater than 0 and at most 600.")
        return value

    def validate_security(self):
        if self.environment != "development":
            if (
                self.jwt_secret
                == "CHANGE_ME_FOR_LOCAL_DEVELOPMENT_ONLY"
                or len(self.jwt_secret) < 32
            ):
                raise RuntimeError(
                    "A strong JWT_SECRET is required outside development"
                )

            if not self.database_url.startswith("postgresql"):
                raise RuntimeError(
                    "PostgreSQL is required outside development"
                )

            if "*" in self.cors_origins.split(","):
                raise RuntimeError(
                    "Wildcard CORS forbidden outside development"
                )


@lru_cache
def get_settings():
    settings = Settings()
    settings.validate_security()
    return settings
