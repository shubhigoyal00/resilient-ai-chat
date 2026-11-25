"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. All values come from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Comma-separated Gemini API keys, e.g. "key1,key2" -> key_1, key_2
    llm_api_keys: str = ""
    # LiteLLM model string, e.g. "gemini/gemini-3.5-flash-lite"
    gemini_model: str = "gemini/gemini-3.5-flash-lite"
    # SQLAlchemy database URL. Must support sqlite:////data/app.db
    database_url: str = "sqlite:////data/app.db"
    # Comma-separated CORS origins
    allowed_origins: str = "http://localhost:3000"
    # Feature flag for the X-Simulate-Failure header
    enable_failure_simulation: bool = False
    # Default system prompt when a request/session does not override it
    default_system_prompt: str = "You are a helpful assistant."
    # Upload limits
    max_upload_mb: float = 10.0
    max_doc_chars: int = 40000  # extracted document text cap sent to the model
    max_attachments_per_message: int = 5

    @property
    def max_upload_bytes(self) -> int:
        return int(self.max_upload_mb * 1024 * 1024)

    @property
    def key_pool(self) -> list[tuple[str, str]]:
        """Return [(key_1, secret), (key_2, secret), ...] in configured order."""
        keys = [k.strip() for k in self.llm_api_keys.split(",") if k.strip()]
        return [(f"key_{i + 1}", secret) for i, secret in enumerate(keys)]

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
