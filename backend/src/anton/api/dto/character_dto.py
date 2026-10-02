from pydantic import BaseModel

from anton.domain.models import Character, CharacterCard


class CastResponse(BaseModel):
    """Represent the cast with a card for every character."""

    characters: list[Character]
    cards: dict[str, CharacterCard]
