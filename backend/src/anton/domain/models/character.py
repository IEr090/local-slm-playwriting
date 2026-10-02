from pydantic import BaseModel, RootModel


class Character(BaseModel):
    """Represent a generated character."""

    name: str
    age: str
    gender: str
    nationality_background: str
    appearance: str
    occupation_social_role: str
    personality: str
    biography: str
    dramatic_role: str
    goal: str
    motivation: str
    fear_weakness: str
    internal_conflict: str
    relationships: str
    character_arc: str


class Characters(RootModel[list[Character]]):
    """Represent a collection of generated characters."""
