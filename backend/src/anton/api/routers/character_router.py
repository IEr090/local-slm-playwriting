from typing import Annotated

from fastapi import APIRouter, Body, Request
from pydantic import BaseModel, Field

from anton.api.dependencies import CharacterServiceDep, EditAgentDep, StoryServiceDep
from anton.api.disconnect import cancel_on_disconnect
from anton.application.agents.chat_edit_agent import ChatMessage
from anton.domain.models import Cast, Character, CharacterDraft, CharacterWithCard


router = APIRouter(prefix="/characters", tags=["characters"])


class ReviseRequest(BaseModel):
    """Represent a chat message about a character together with the character from the user's form."""

    message: str = Field(min_length=1)
    character: CharacterDraft


class CharacterRevision(BaseModel):
    """Represent the answer of the edit agent and the character as it sees it now."""

    reply: str
    character: Character


@router.post("/generate")
async def generate_cast(
    premise: Annotated[str, Body(embed=True, min_length=1)],
    service: CharacterServiceDep,
    story_service: StoryServiceDep,
    request: Request,
) -> Cast:
    """Generate the whole cast with cards from a premise; stop generating if the client cancels.

    The premise is the user's initial input, so a new Story Bible is started from it.
    """
    cast = await cancel_on_disconnect(request, service.generate_cast(premise))
    await story_service.start_play(premise)
    return cast


@router.get("")
async def get_cast(service: CharacterServiceDep) -> Cast:
    """Return the saved cast with cards."""
    return service.get_cast()


@router.post("")
async def create_character(draft: CharacterDraft, service: CharacterServiceDep) -> CharacterWithCard:
    """Create a character from the user's profile and generate its card."""
    return await service.create_character(draft)


@router.put("/{character_id}")
async def edit_character(character_id: str, draft: CharacterDraft, service: CharacterServiceDep) -> CharacterWithCard:
    """Update the character; regenerate its card only if the fields it is built from changed."""
    return await service.edit_character(character_id, draft)


@router.post("/{character_id}/revise")
async def revise_character(character_id: str, body: ReviseRequest, agent: EditAgentDep) -> CharacterRevision:
    """Send the user's chat message to the edit agent; the edited character is not saved."""
    character = Character(id=character_id, **body.character.model_dump())
    # Every character has its own conversation.
    result = await agent.send(character_id, character, body.message)
    return CharacterRevision(reply=result.reply, character=result.data)


@router.get("/{character_id}/revise")
async def get_revise_history(character_id: str, agent: EditAgentDep) -> list[ChatMessage]:
    """Return the chat history with the edit agent about the character."""
    return await agent.history(character_id)
