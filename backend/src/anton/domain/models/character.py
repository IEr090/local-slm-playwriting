from typing import Literal

from pydantic import BaseModel


Gender = Literal["female", "male", "other"]
DramaticRole = Literal[
    "protagonist", "antagonist", "confidant", "catalyst",
    "outsider", "wildcard", "mentor", "foil",
]


class Relationship(BaseModel):
    """Represent a character's relationship to another character."""

    character_id: str
    description: str


class CharacterDraft(BaseModel):
    """Represent a character profile that has no id yet."""

    name: str
    surname: str
    age: int | None
    gender: Gender | None
    nationality_background: str
    appearance: str
    occupation_social_role: str
    personality: str
    biography: str
    dramatic_role: DramaticRole | None
    dramatic_role_description: str
    goal: str
    motivation: str
    fear_weakness: str
    internal_conflict: str
    character_arc: str
    relationships: list[Relationship]


class Character(CharacterDraft):
    """Represent a generated character."""

    id: str


class CharacterCard(BaseModel):
    """Represent the short grid card of a character."""

    role_label: DramaticRole | None
    tagline: str
    traits: list[str]
    wants: str
    fears: str


class CharacterWithCard(BaseModel):
    """Represent a character together with its grid card."""

    character: Character
    card: CharacterCard


class Cast(BaseModel):
    """Represent the cast with a card for every character."""

    characters: list[Character]
    cards: dict[str, CharacterCard]
