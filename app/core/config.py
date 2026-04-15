# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    # DB
    DATABASE_URL: str
    USE_LOCAL_DB: int = 0
    LOCAL_DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/feria"

    # JWT
    JWT_SECRET: str
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Google OAuth
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    STUDENT_EMAIL_DOMAIN: str = "tec.mx"
    ENVIRONMENT: str = "development"
    # URL base de la app (necesaria en produccion detras de proxy HTTPS)
    APP_BASE_URL: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    @field_validator("JWT_SECRET")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET debe tener al menos 32 caracteres para seguridad adecuada. "
                f"Longitud actual: {len(v)} caracteres."
            )
        return v


settings = Settings()