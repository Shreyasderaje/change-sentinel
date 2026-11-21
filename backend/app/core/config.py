
from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./dev.db"

    # Supabase / PostgreSQL SSL certificate
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
