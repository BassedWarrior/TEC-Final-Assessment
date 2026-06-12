"""
Configuration module.

Loads environment variables from .env file and provides a Settings class
with typed access to database URL, JWT secret, algorithm, and token expiry.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback-secret-change-me")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # Base URL of the MLB model API (Monte Carlo /simulate service)
    MODEL_API_URL: str = os.getenv("MODEL_API_URL", "http://localhost:8001")

    # Frontend origins allowed by CORS (comma-separated for multiple)
    FRONTEND_URL: list[str] = os.getenv("FRONTEND_URL", "http://localhost:5173").split(",")


settings = Settings()
