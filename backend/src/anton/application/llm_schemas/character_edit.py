from pydantic import BaseModel, Field

from anton.domain.models import DramaticRole, Gender


class EditedCharacter(BaseModel):
    """Represent a character profile as the language model returns it after an edit, without relationships."""

    name: str = Field(description="First name only.")
    surname: str = Field(description="Family name. Empty string if unknown.")
    age: int | None = Field(description="Age in years, or null if unknown.")
    gender: Gender | None
    nationality_background: str
    appearance: str
    occupation_social_role: str
    personality: str
    biography: str
    dramatic_role: DramaticRole | None
    dramatic_role_description: str = Field(description="How the character drives or blocks the central conflict.")
    goal: str
    motivation: str
    fear_weakness: str
    internal_conflict: str
    character_arc: str
