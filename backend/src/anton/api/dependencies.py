from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from anton.application.character_service import CharacterService
from anton.infrastructure.slm import OllamaClient, SLMClient


@lru_cache
def get_slm_client() -> SLMClient:
    """Create one Ollama client for the whole application."""
    return OllamaClient(model="qwen3:4b", num_ctx=16384)


def get_character_service(client: Annotated[SLMClient, Depends(get_slm_client)]) -> CharacterService:
    """Create the character service with the configured SLM client."""
    return CharacterService(client)


CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]
