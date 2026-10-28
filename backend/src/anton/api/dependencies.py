from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from langgraph.checkpoint.memory import InMemorySaver

from anton.application.agents.acts_target import ActsTarget
from anton.application.agents.character_target import CharacterTarget
from anton.application.agents.chat_edit_agent import ChatEditAgent, create_checkpointer
from anton.application.agents.outline_target import OutlineTarget
from anton.application.agents.scene_targets import SceneBoard, ScenesTarget, StructureTarget
from anton.application.agents.text_target import TextTarget
from anton.application.character_service import CharacterService
from anton.application.scene_planner import ScenePlanner
from anton.application.scene_service import SceneService
from anton.application.scene_writer import SceneWriter
from anton.application.text_service import TextService
from anton.application.story_service import StoryService
from anton.domain.models import ActSummary, Character, Outline, SceneText
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
def get_edit_agent() -> ChatEditAgent[Character]:
    """Create one agent that edits characters, with an in-memory store of conversations, for the whole application."""
    return ChatEditAgent(get_slm_client(), CharacterTarget(), create_checkpointer())


EditAgentDep = Annotated[ChatEditAgent[Character], Depends(get_edit_agent)]


@lru_cache
def get_outline_agent() -> ChatEditAgent[Outline]:
    """Create one agent that writes and edits the outline, with an in-memory store of its conversation."""
    return ChatEditAgent(get_slm_client(), OutlineTarget(), create_checkpointer())


@lru_cache
def get_acts_agent() -> ChatEditAgent[list[ActSummary]]:
    """Create one agent that writes and edits the acts, with an in-memory store of its conversation."""
    return ChatEditAgent(get_slm_client(), ActsTarget(), create_checkpointer())


def get_story_service(
    story_repository: Annotated[StoryRepository, Depends(get_story_repository)],
    cast_repository: Annotated[CastRepository, Depends(get_cast_repository)],
    outline_agent: Annotated[ChatEditAgent[Outline], Depends(get_outline_agent)],
    acts_agent: Annotated[ChatEditAgent[list[ActSummary]], Depends(get_acts_agent)],
) -> StoryService:
    """Create the story service with the configured repositories and page agents."""
    return StoryService(story_repository, cast_repository, outline_agent, acts_agent)


StoryServiceDep = Annotated[StoryService, Depends(get_story_service)]


@lru_cache
def get_act_checkpointer() -> InMemorySaver:
    """Create one store of the act page conversations, shared by both agents of the page."""
    return create_checkpointer()


@lru_cache
def get_structure_agent() -> ChatEditAgent[SceneBoard]:
    """Create one agent that proposes and edits the scenes of an act."""
    return ChatEditAgent(get_slm_client(), StructureTarget(), get_act_checkpointer())


@lru_cache
def get_scenes_agent() -> ChatEditAgent[SceneBoard]:
    """Create one agent that edits the plans of the scenes of an act."""
    return ChatEditAgent(get_slm_client(), ScenesTarget(), get_act_checkpointer())


def get_scene_service(
    story_repository: Annotated[StoryRepository, Depends(get_story_repository)],
    cast_repository: Annotated[CastRepository, Depends(get_cast_repository)],
    structure_agent: Annotated[ChatEditAgent[SceneBoard], Depends(get_structure_agent)],
    scenes_agent: Annotated[ChatEditAgent[SceneBoard], Depends(get_scenes_agent)],
    client: Annotated[SLMClient, Depends(get_slm_client)],
) -> SceneService:
    """Create the scene service with the configured repositories, act page agents and scene planner."""
    return SceneService(story_repository, cast_repository, structure_agent, scenes_agent, ScenePlanner(client))


SceneServiceDep = Annotated[SceneService, Depends(get_scene_service)]


@lru_cache
def get_text_agent() -> ChatEditAgent[list[SceneText]]:
    """Create one agent that revises the text of an act; it writes into the chat of the act page."""
    return ChatEditAgent(get_slm_client(), TextTarget(), get_act_checkpointer())


def get_text_service(
    story_repository: Annotated[StoryRepository, Depends(get_story_repository)],
    cast_repository: Annotated[CastRepository, Depends(get_cast_repository)],
    text_agent: Annotated[ChatEditAgent[list[SceneText]], Depends(get_text_agent)],
    client: Annotated[SLMClient, Depends(get_slm_client)],
) -> TextService:
    """Create the text service with the configured repositories, the text agent and the scene writer."""
    return TextService(story_repository, cast_repository, text_agent, SceneWriter(client))


TextServiceDep = Annotated[TextService, Depends(get_text_service)]
