from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from anton.application.character_service import CharacterService
from anton.application.edit_agent import EditAgent, create_checkpointer
from anton.application.outline_agent import OutlineAgent, create_outline_checkpointer
from anton.application.story_service import StoryService
from anton.infrastructure.config import Settings
from anton.infrastructure.slm import SLMClient, create_slm_client
from anton.infrastructure.storage import CastRepository, JsonCastRepository, JsonStoryRepository, StoryRepository


@lru_cache
def get_settings() -> Settings:
    """Read the settings once for the whole application."""
    return Settings()


@lru_cache
def get_slm_client() -> SLMClient:
    """Create one model client for the whole application."""
    return create_slm_client(get_settings())


@lru_cache
def get_cast_repository() -> CastRepository:
    """Create one cast repository in the configured data directory for the whole application."""
    return JsonCastRepository(get_settings().data_dir / "cast.json")


@lru_cache
def get_story_repository() -> StoryRepository:
    """Create one Story Bible repository in the configured data directory for the whole application."""
    return JsonStoryRepository(get_settings().data_dir / "story_bible.json")


def get_character_service(
    client: Annotated[SLMClient, Depends(get_slm_client)],
    repository: Annotated[CastRepository, Depends(get_cast_repository)],
) -> CharacterService:
    """Create the character service with the configured SLM client and cast repository."""
    return CharacterService(client, repository)


CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]


@lru_cache
def get_edit_agent() -> EditAgent:
    """Create one edit agent with an in-memory store of conversations for the whole application."""
    return EditAgent(get_slm_client(), create_checkpointer())


EditAgentDep = Annotated[EditAgent, Depends(get_edit_agent)]


@lru_cache
def get_outline_agent() -> OutlineAgent:
    """Create one outline agent with an in-memory store of its conversation for the whole application."""
    return OutlineAgent(get_slm_client(), create_outline_checkpointer())


def get_story_service(
    client: Annotated[SLMClient, Depends(get_slm_client)],
    story_repository: Annotated[StoryRepository, Depends(get_story_repository)],
    cast_repository: Annotated[CastRepository, Depends(get_cast_repository)],
    outline_agent: Annotated[OutlineAgent, Depends(get_outline_agent)],
) -> StoryService:
    """Create the story service with the configured SLM client, repositories and outline agent."""
    return StoryService(client, story_repository, cast_repository, outline_agent)


StoryServiceDep = Annotated[StoryService, Depends(get_story_service)]
