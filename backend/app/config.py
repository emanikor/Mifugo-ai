"""
Central config, loaded from environment variables (populated by
docker-compose.yml in containers, or a local .env file when running
the backend outside Docker for quick iteration).

Nothing in here should ever point at a non-local hostname — DATABASE_URL
and OLLAMA_BASE_URL should only ever resolve to `db`/`ollama` (Docker
service names) or 127.0.0.1.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://mifugo_user:changeme@db:5432/mifugo"

    secret_key: str = "changeme-generate-a-real-random-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12  # 12h — agents work long field days

    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_timeout_seconds: int = 60

    app_env: str = "development"

    # Comma-separated list of allowed frontend origins for CORS.
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
