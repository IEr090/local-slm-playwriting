from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read the application settings from ANTON_* environment variables and the .env file."""

    model_config = SettingsConfigDict(env_prefix="ANTON_", env_file=".env")

    ollama_model: str = "qwen3:4b"
    ollama_num_ctx: int = 16384
    thinking: bool = True
