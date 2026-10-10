from typing import Annotated

from fastapi import APIRouter, Body, Request

from anton.api.dependencies import CharacterServiceDep
from anton.api.disconnect import cancel_on_disconnect
from anton.domain.models import Cast, CharacterDraft, CharacterWithCard


router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("/generate")
async def generate_cast(
    premise: Annotated[str, Body(embed=True, min_length=1)],
    service: CharacterServiceDep,
    request: Request,
) -> Cast:
    """Generate the whole cast with cards from a premise; stop generating if the client cancels."""
    return await cancel_on_disconnect(request, service.generate_cast(premise))


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
async def revise_character(character_id: str) -> None:
    """Revise the character according to the user's request."""
    raise NotImplementedError
