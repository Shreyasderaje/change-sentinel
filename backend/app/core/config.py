
from functools import lru_cache
from typing import Literal
from sqlalchemy.engine import make_url

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite:///./dev.db"
    migration_database_url: SecretStr | None = None

    # Supabase / PostgreSQL SSL certificate
    db_ssl_ca_file: str | None = None
    db_ssl_mode: Literal["verify-full", "disable"] = "verify-full"

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


    def get_migration_url(self):
        runtime = make_url(self.database_url)

        if self.migration_database_url is None:
            if (
                self.environment == "development"
                and runtime.get_backend_name() == "sqlite"
            ):
                return self.database_url

            raise RuntimeError(
                "MIGRATION_DATABASE_URL is required"
            )

        value = self.migration_database_url.get_secret_value()
        target = make_url(value)

        if self.environment != "development":
            if target.drivername != "postgresql+pg8000":
                raise RuntimeError(
                    "PostgreSQL migration credentials required"
                )

            if target.username == runtime.username:
                raise RuntimeError(
                    "Migration and runtime users must differ"
                )

        if self.db_ssl_mode == "disable":
            if (
                self.environment != "development"
                or target.drivername != "postgresql+pg8000"
                or target.host not in (
                    "localhost", "127.0.0.1", "::1"
                )
                or target.query
            ):
                raise RuntimeError(
                    "Unsafe migration SSL configuration"
                )

        return value

    def validate_security(self):

        if self.db_ssl_mode == "disable":
            url = make_url(self.database_url)

            if (
                self.environment != "development"
                or url.drivername != "postgresql+pg8000"
                or url.host not in (
                    "localhost", "127.0.0.1", "::1"
                )
            ):
                raise RuntimeError(
                    "SSL can only be disabled for local "
                    "PostgreSQL development connections"
                )

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
