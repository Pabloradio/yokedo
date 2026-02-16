import os


def get_auth_service_base_url() -> str:
    # Example: http://127.0.0.1:8000
    value = os.getenv("AUTH_SERVICE_BASE_URL", "").strip()
    if not value:
        raise RuntimeError("AUTH_SERVICE_BASE_URL is not set")
    return value.rstrip("/")
