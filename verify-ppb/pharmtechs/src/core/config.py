"""
Configuration settings for PPB Pharmtech License Verification Service
Supports environment-based configuration with sensible defaults
"""

import os
from .version import __version__


class Config:
    """Base configuration with production-safe defaults"""

    # Service Configuration
    SERVICE_NAME = "PPB Pharmtech License Verification Microservice"
    VERSION = __version__
    DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", "5001"))  # Different port from facilities

    # PPB Portal Configuration
    PPB_BASE_URL = "https://practice.pharmacyboardkenya.org"
    PPB_SEARCH_URL = f"{PPB_BASE_URL}/ajax/public"

    # Request Configuration
    REQUEST_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "15"))
    MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "2"))
    RETRY_BACKOFF = float(os.environ.get("RETRY_BACKOFF", "0.3"))

    # Rate Limiting (CRITICAL - prevents IP blocking)
    RATE_LIMIT_DELAY = float(os.environ.get("RATE_LIMIT_DELAY", "1.5"))

    # Caching Configuration
    CACHE_ENABLED = os.environ.get("CACHE_ENABLED", "true").lower() == "true"
    CACHE_BACKEND = os.environ.get("CACHE_BACKEND", "simple")  # 'simple' or 'redis'
    CACHE_TTL = int(os.environ.get("CACHE_TTL", "3600"))  # 1 hour default
    CACHE_MAX_SIZE = int(os.environ.get("CACHE_MAX_SIZE", "1000"))
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/1")  # Different DB from facilities

    # Logging Configuration
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.environ.get("LOG_FORMAT", "json")  # 'json' or 'text'

    # Security
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", "1048576"))  # 1MB


class DevelopmentConfig(Config):
    """Development configuration with debugging enabled"""
    DEBUG = True
    CACHE_TTL = 300  # 5 minutes for dev
    LOG_LEVEL = "DEBUG"
    LOG_FORMAT = "text"


class ProductionConfig(Config):
    """Production configuration with optimized settings"""
    DEBUG = False
    CACHE_TTL = 7200  # 2 hours for production
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "json"


class TestingConfig(Config):
    """Testing configuration with cache and rate limiting disabled"""
    DEBUG = True
    CACHE_ENABLED = False
    RATE_LIMIT_DELAY = 0.0  # No delay in tests
    LOG_LEVEL = "WARNING"


# Configuration dictionary
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}


def get_config(env=None):
    """
    Get configuration based on environment

    Args:
        env: Environment name (development/production/testing)

    Returns:
        Configuration class
    """
    if env is None:
        env = os.environ.get("FLASK_ENV", "default")
    return config.get(env, config["default"])
