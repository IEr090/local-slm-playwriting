from typing import Annotated

from fastapi import APIRouter, Body

from anton.api.dto.character_dto import CastResponse


router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("/generate", response_model=CastResponse)
async def generate_cast(premise: Annotated[str, Body(embed=True, min_length=1)]) -> CastResponse:
    """Generate the whole cast with cards from a premise."""
    raise NotImplementedError


@router.get("", response_model=CastResponse)
async def get_cast() -> CastResponse:
    """Return the saved cast with cards."""
    raise NotImplementedError


@router.post("")
async def create_blank_character() -> None:
    """Create an empty character with a placeholder card."""
    raise NotImplementedError


@router.put("/{character_id}")
async def save_character(character_id: str) -> None:
    """Store the edited character."""
    raise NotImplementedError


@router.post("/{character_id}/card")
async def generate_card(character_id: str) -> None:
    """Regenerate the grid card from the character profile."""
    raise NotImplementedError


@router.post("/{character_id}/revise")
async def revise_character(character_id: str) -> None:
    """Revise the character according to the user's request."""
    raise NotImplementedError
