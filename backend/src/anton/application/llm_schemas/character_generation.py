from pydantic import BaseModel, Field, RootModel

from anton.domain.models import DramaticRole, Gender


class GeneratedRelationship(BaseModel):
    """Represent a relationship that references another character by full name."""

    name: str = Field(description="First name of the other character, exactly as in their profile.")
    surname: str = Field(description="Family name of the other character, exactly as in their profile. Empty string if they have none.")
    description: str = Field(description="What they want from each other and how power is distributed.")


class GeneratedCharacter(BaseModel):
    """Represent a character as the language model generates it."""

    name: str = Field(description="First name only.")
    surname: str = Field(description="Family name. Empty string if unknown.")
    age: int = Field(description="Age in years.")
    gender: Gender
    nationality_background: str
    appearance: str
    occupation_social_role: str
    personality: str
    biography: str
    dramatic_role: DramaticRole
    dramatic_role_description: str = Field(description="How the character drives or blocks the central conflict.")
    goal: str
    motivation: str
    fear_weakness: str
    internal_conflict: str
    character_arc: str
    relationships: list[GeneratedRelationship]


class GeneratedCast(RootModel[list[GeneratedCharacter]]):
    """Represent the cast as the language model generates it."""


class GeneratedCard(BaseModel):
    """Represent a character card as the language model generates it."""

    tagline: str
    traits: list[str] = Field(min_length=3, max_length=3)
    wants: str
    fears: str
