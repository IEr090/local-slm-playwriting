from fastapi import APIRouter


router = APIRouter(prefix="/characters", tags=["characters"])


@router.post("/generate")
async def generate_cast() -> None:
    """Generate the whole cast with cards from a premise."""
    raise NotImplementedError


@router.get("")
async def get_cast() -> None:
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
