from pydantic import BaseModel, Field

from anton.domain.models import Character, CharacterDraft


class ReviseRequest(BaseModel):
    """Represent a chat message about a character together with the character from the user's form."""

    message: str = Field(min_length=1)
    character: CharacterDraft


class CharacterRevision(BaseModel):
    """Represent the answer of the edit agent and the character as it sees it now."""

    reply: str
    character: Character
