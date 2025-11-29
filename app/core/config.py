"""
Application configuration settings.
Manages all environment variables and constants.
"""

import os
from typing import Optional


class Settings:
    """Application settings configuration."""
    
    # Application metadata
    APP_NAME: str = "Search API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "FastAPI backend with search functionality"
    
    # Server configuration
    API_V1_STR: str = "/api/v1"
    SERVER_HOST: str = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))
    
    # External API configuration
    EXTERNAL_API_URL: str = os.getenv(
        "EXTERNAL_API_URL",
        "https://november7-730026606190.europe-west1.run.app"
    )
    EXTERNAL_API_ENDPOINT: str = "/messages/"
    EXTERNAL_API_TIMEOUT: int = int(os.getenv("EXTERNAL_API_TIMEOUT", "30"))
    
    # Pagination defaults
    DEFAULT_SKIP: int = 0
    DEFAULT_LIMIT: int = 10
    MAX_LIMIT: int = 100
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/app.log")
    
    # Cache configuration
    INCREMENTAL_REFRESH_SECONDS: int = int(os.getenv("INCREMENTAL_REFRESH_SECONDS", "15"))
    FULL_REFRESH_HOURS: int = int(os.getenv("FULL_REFRESH_HOURS", "6"))
    FETCH_LIMIT: int = int(os.getenv("FETCH_LIMIT", "10000"))
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = ENVIRONMENT == "development"
    
    @property
    def full_api_url(self) -> str:
        """Get full API endpoint URL."""
        return f"{self.EXTERNAL_API_URL}{self.EXTERNAL_API_ENDPOINT}"


# Create settings instance
settings = Settings()
