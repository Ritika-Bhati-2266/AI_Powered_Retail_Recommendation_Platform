"""
Application configuration via environment variables with sensible defaults.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables with .env support."""

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

    # CORS
    CORS_ORIGINS: list[str] = ["*"]

    # Authentication — SECRET_KEY should come from the environment in production.
    # This dev default is NOT safe for production; set JWT_SECRET/SECRET_KEY env var.
    SECRET_KEY: str = "dev-only-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Default password for demo/seeded accounts (documented; not for real users)
    DEMO_PASSWORD: str = "Customer@2030"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
