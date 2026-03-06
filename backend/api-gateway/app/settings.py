#api-gateway/app/settings.py

import os

REQUEST_ID_HEADER = "X-Request-ID"

PROXY_CONNECT_TIMEOUT_SECONDS = 2.0
PROXY_READ_TIMEOUT_SECONDS = 10.0

# Rate limiting (fixed window, in-memory). MVP-level protection.
RATE_LIMIT_WINDOW_SECONDS = 60

# Global limits for /api/*
RATE_LIMIT_API_REQUESTS_PER_WINDOW = 120

# Stricter limits for /api/auth/*
RATE_LIMIT_AUTH_REQUESTS_PER_WINDOW = 30

# Auth token validation (gateway delegates validation to auth-service)
AUTH_TOKEN_VALIDATION_PATH = "/api/auth/me"

# Optional: small cache to reduce auth-service calls (MVP)
AUTH_CONTEXT_CACHE_TTL_SECONDS = 30
AUTH_CONTEXT_CACHE_MAX_ENTRIES = 1000


def get_auth_service_base_url() -> str:
    # Example: http://127.0.0.1:7000
    value = os.getenv("AUTH_SERVICE_BASE_URL", "").strip()
    if not value:
        raise RuntimeError("AUTH_SERVICE_BASE_URL is not set")
    return value.rstrip("/")


def get_cors_allowed_origins() -> list[str]:
    """
    Comma-separated list of allowed origins for CORS.
    Example:
      CORS_ALLOWED_ORIGINS="http://localhost:3000,http://127.0.0.1:3000"
    """
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return []
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
