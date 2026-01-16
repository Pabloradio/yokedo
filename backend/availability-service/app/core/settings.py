from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # PostgreSQL configuration
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str

    # JWT configuration
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Pydantic v2 settings configuration
    # This replaces the previous SettingsConfigDict to avoid Pylance warnings.
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }


# Instantiate global settings object
settings = Settings()
