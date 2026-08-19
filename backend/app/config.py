"""
Application configuration via environment variables with sensible defaults.
"""
import warnings

from pydantic_settings import BaseSettings

# The JWT signing key shipped as the dev fallback. It is NOT a secret and is
# documented in the README — it must never be used outside local development.
DEV_FALLBACK_SECRET = "dev-only-insecure-secret-change-me"
# Documented demo/seed account password (500 seeded customers + admin).
DEFAULT_DEMO_PASSWORD = "Customer@2030"


class Settings(BaseSettings):
    """Application settings loaded from environment variables with .env support."""

    # Deployment environment. Production-like environments (or a Postgres
    # DATABASE_URL) enable the fail-closed startup guards below.
    ENVIRONMENT: str = "development"

    # Database — SQLite by default for zero-install dev, Postgres for production
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/personalisation.db"

    # Redis (optional — skip for local dev, set for production)
    REDIS_URL: str = ""

    # Model — store next to the app
    MODEL_PATH: str = "./data/model.pkl"

    # Seed data configuration
    CUSTOMER_COUNT: int = 500
    EVENT_COUNT: int = 10000

    # API
    APP_TITLE: str = "Retail Hyper-Personalisation Engine"
    APP_VERSION: str = "1.0.0"

    # CORS — tightened by default to local dev origins. The served SPA + Vite
    # dev proxy are same-origin, so a wide-open `*` default is unnecessary and
    # invalid-to-combine with allow_credentials. Override via CORS_ORIGINS env
    # (comma-separated) for any other deployment.
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Authentication — SECRET_KEY should come from the environment in production.
    # This dev default is NOT safe for production; set JWT_SECRET/SECRET_KEY env var.
    SECRET_KEY: str = DEV_FALLBACK_SECRET
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Default password for demo/seeded accounts (documented; not for real users)
    DEMO_PASSWORD: str = DEFAULT_DEMO_PASSWORD

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def is_production(self) -> bool:
        """True for production-like deployments: explicit ENVIRONMENT=production
        or a non-SQLite (Postgres) DATABASE_URL."""
        env = self.ENVIRONMENT.strip().lower()
        return env in ("production", "prod") or self.DATABASE_URL.startswith("postgres")

    def model_post_init(self, __context) -> None:
        """Fail closed on obviously insecure production configurations."""
        if self.is_production and self.SECRET_KEY == DEV_FALLBACK_SECRET:
            raise RuntimeError(
                "Refusing to start in a production-like environment: SECRET_KEY is "
                "still the insecure dev fallback. Set SECRET_KEY to a strong random "
                "value (e.g. `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`)."
            )
        if self.SECRET_KEY == DEV_FALLBACK_SECRET:
            warnings.warn(
                "SECRET_KEY is the insecure dev fallback — set SECRET_KEY in the "
                "environment for any non-local deployment.",
                stacklevel=2,
            )


settings = Settings()
