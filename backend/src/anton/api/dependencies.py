from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends

from anton.application.agents.act_chat import ActChat
from anton.application.agents.acts_target import ActsTarget
from anton.application.agents.character_target import CharacterTarget
from anton.application.agents.chat_edit_agent import ChatEditAgent, create_checkpointer
from anton.application.agents.outline_target import OutlineTarget
from anton.application.character_service import CharacterService
from anton.application.scene_planner import ScenePlanner
from anton.application.scene_service import SceneService
from anton.application.scene_writer import SceneWriter
from anton.application.text_service import TextService
from anton.application.story_service import StoryService
from anton.domain.models import ActSummary, Character, Outline
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


def chat_file(name: str) -> Path:
    """Return the file in the configured data directory that keeps one store of conversations."""
    return get_settings().data_dir / "chats" / f"{name}.pickle"


@lru_cache
def get_story_repository() -> StoryRepository:
    """Create one Story Bible repository in the configured data directory for the whole application."""
    return JsonStoryRepository(get_settings().data_dir / "story_bible.json")


@lru_cache
def get_edit_agent() -> ChatEditAgent[Character]:
    """Create one agent that edits characters, with a saved store of conversations, for the whole application."""
    return ChatEditAgent(get_slm_client(), CharacterTarget(), create_checkpointer(chat_file("characters")))


def get_character_service(
    client: Annotated[SLMClient, Depends(get_slm_client)],
    repository: Annotated[CastRepository, Depends(get_cast_repository)],
    edit_agent: Annotated[ChatEditAgent[Character], Depends(get_edit_agent)],
) -> CharacterService:
    """Create the character service with the configured SLM client, cast repository and edit agent."""
    return CharacterService(client, repository, edit_agent)


CharacterServiceDep = Annotated[CharacterService, Depends(get_character_service)]


@lru_cache
def get_outline_agent() -> ChatEditAgent[Outline]:
    """Create one agent that writes and edits the outline, with a saved store of its conversation."""
    return ChatEditAgent(get_slm_client(), OutlineTarget(), create_checkpointer(chat_file("outline")))


@lru_cache
def get_acts_agent() -> ChatEditAgent[list[ActSummary]]:
    """Create one agent that writes and edits the acts, with a saved store of its conversation."""
    return ChatEditAgent(get_slm_client(), ActsTarget(), create_checkpointer(chat_file("acts")))


@lru_cache
def get_act_chat() -> ActChat:
    """Create the chat of the act pages with a saved store of its conversations, one per act."""
    return ActChat(get_slm_client(), create_checkpointer(chat_file("acts-pages")))


def get_story_service(
    story_repository: Annotated[StoryRepository, Depends(get_story_repository)],
    cast_repository: Annotated[CastRepository, Depends(get_cast_repository)],
    outline_agent: Annotated[ChatEditAgent[Outline], Depends(get_outline_agent)],
    acts_agent: Annotated[ChatEditAgent[list[ActSummary]], Depends(get_acts_agent)],
    act_chat: Annotated[ActChat, Depends(get_act_chat)],
) -> StoryService:
    """Create the story service with the configured repositories, page agents and the act page chat."""
    return StoryService(story_repository, cast_repository, outline_agent, acts_agent, act_chat)


StoryServiceDep = Annotated[StoryService, Depends(get_story_service)]


def get_scene_service(
    story_repository: Annotated[StoryRepository, Depends(get_story_repository)],
    cast_repository: Annotated[CastRepository, Depends(get_cast_repository)],
    act_chat: Annotated[ActChat, Depends(get_act_chat)],
    client: Annotated[SLMClient, Depends(get_slm_client)],
) -> SceneService:
    """Create the scene service with the configured repositories, the act page chat and the scene planner."""
    return SceneService(story_repository, cast_repository, act_chat, ScenePlanner(client))


SceneServiceDep = Annotated[SceneService, Depends(get_scene_service)]


def get_text_service(
    story_repository: Annotated[StoryRepository, Depends(get_story_repository)],
    cast_repository: Annotated[CastRepository, Depends(get_cast_repository)],
    act_chat: Annotated[ActChat, Depends(get_act_chat)],
    client: Annotated[SLMClient, Depends(get_slm_client)],
) -> TextService:
    """Create the text service with the configured repositories, the act page chat and the scene writer."""
    return TextService(story_repository, cast_repository, act_chat, SceneWriter(client))


TextServiceDep = Annotated[TextService, Depends(get_text_service)]
