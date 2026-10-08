from typing import TypeVar

from pydantic import BaseModel

from anton.application.llm_schemas.character_generation import GeneratedCard
from anton.domain.models import CharacterDraft


T = TypeVar("T", bound=BaseModel)

CARD = GeneratedCard(
    tagline="Artistic director of a failing theatre",
    traits=["Stubborn", "Proud", "Devoted"],
    wants="To save the theatre she built.",
    fears="Losing her life's work.",
)


def make_draft() -> CharacterDraft:
    """Create a complete character profile without an id."""
    return CharacterDraft(
        name="Elena",
        surname="Weiss",
        age=47,
        gender="female",
        nationality_background="Austrian",
        appearance="Tall, grey hair tied back.",
        occupation_social_role="Artistic director of an independent theatre",
        personality="Stubborn, proud and fiercely loyal.",
        biography="Founded the theatre twenty years ago.",
        dramatic_role="protagonist",
        dramatic_role_description="Fights to keep the theatre open.",
        goal="Save the theatre from bankruptcy.",
        motivation="The theatre is her whole life.",
        fear_weakness="Being forgotten.",
        internal_conflict="Art against money.",
        character_arc="Learns to let others lead.",
        relationships=[],
    )


class FakeSLMClient:
    """Return a prepared response and remember every call."""

    def __init__(self, response: BaseModel) -> None:
        """Initialize the client with the response it always returns."""
        self.response = response
        self.calls: list[dict] = []

    async def generate(self, system_prompt: str, user_prompt: str, response_model: type[T], think: bool) -> T:
        """Record the call and return the prepared response."""
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response_model": response_model,
            "think": think,
        })
        return self.response


class FailingSLMClient:
    """Raise the prepared error on every call."""

    def __init__(self, error: Exception) -> None:
        """Initialize the client with the error it always raises."""
        self.error = error

    async def generate(self, system_prompt: str, user_prompt: str, response_model: type[T], think: bool) -> T:
        """Raise the prepared error."""
        raise self.error
