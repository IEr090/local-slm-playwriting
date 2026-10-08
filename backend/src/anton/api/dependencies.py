from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from anton.application.character_service import CharacterService
from anton.infrastructure.config import Settings
from anton.infrastructure.slm import SLMClient, create_slm_client


@lru_cache
def get_settings() -> Settings:
    """Read the settings once for the whole application."""
    return Settings()


@lru_cache
def get_slm_client() -> SLMClient:
    """Create one model client for the whole application."""
    return create_slm_client(get_settings())


def get_character_service(client: Annotated[SLMClient, Depends(get_slm_client)]) -> CharacterService:
    """Create the character service with the configured SLM client."""
    return CharacterService(client)


CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]
