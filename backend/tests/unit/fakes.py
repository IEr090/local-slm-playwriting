from typing import TypeVar

from pydantic import BaseModel

from anton.application.llm_schemas.character_generation import GeneratedCard, GeneratedCast, GeneratedCharacter
from anton.domain.models import Cast, CharacterDraft


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


def make_generated_cast() -> GeneratedCast:
    """Create a model answer with one character built from the complete profile."""
    return GeneratedCast([GeneratedCharacter(**make_draft().model_dump(exclude={"relationships"}), relationships=[])])


class FakeSLMClient:
    """Return a prepared response for every response model and remember every call."""

    def __init__(self, *responses: BaseModel) -> None:
        """Initialize the client with the responses it returns, one per response model."""
        self.responses = {type(response): response for response in responses}
        self.calls: list[dict] = []

    async def generate(self, system_prompt: str, user_prompt: str, response_model: type[T], think: bool) -> T:
        """Record the call and return the response prepared for the response model."""
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response_model": response_model,
            "think": think,
        })
        return self.responses[response_model]


class FailingSLMClient:
    """Raise the prepared error on every call."""

    def __init__(self, error: Exception) -> None:
        """Initialize the client with the error it always raises."""
        self.error = error

    async def generate(self, system_prompt: str, user_prompt: str, response_model: type[T], think: bool) -> T:
        """Raise the prepared error."""
        raise self.error


class InMemoryCastRepository:
    """Keep the cast in memory and count every save."""

    def __init__(self, cast: Cast | None = None) -> None:
        """Initialize the repository, optionally with an already saved cast."""
        self.cast = cast.model_copy(deep=True) if cast is not None else None
        self.saves = 0

    def load(self) -> Cast | None:
        """Return a copy of the saved cast, like a real storage would."""
        return self.cast.model_copy(deep=True) if self.cast is not None else None

    def save(self, cast: Cast) -> None:
        """Keep a copy of the cast and count the save."""
        self.cast = cast.model_copy(deep=True)
        self.saves += 1


class ScriptedSLMClient:
    """Return or raise the prepared responses in order, one per call, and remember every call."""

    def __init__(self, *responses: BaseModel | Exception) -> None:
        """Initialize the client with the responses it returns or raises, in call order."""
        self.responses = list(responses)
        self.calls: list[dict] = []

    async def generate(self, system_prompt: str, user_prompt: str, response_model: type[T], think: bool) -> T:
        """Record the call and return or raise the next prepared response."""
        self.calls.append({
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "response_model": response_model,
            "think": think,
        })
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response
