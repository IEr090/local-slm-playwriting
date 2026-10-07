from anton.infrastructure.config import Settings

from .client import SLMClient
from .ollama_client import OllamaClient


def create_slm_client(settings: Settings) -> SLMClient:
    """Create the model client described by the settings."""
    return OllamaClient(
        model=settings.ollama_model,
        num_ctx=settings.ollama_num_ctx,
        thinking=settings.thinking,
    )
