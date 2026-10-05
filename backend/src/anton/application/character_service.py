from anton.domain.models import Character, CharacterCard
from anton.infrastructure.slm import SLMClient


class CharacterService:
    """Generate and manage the characters of a play."""

    def __init__(self, client: SLMClient) -> None:
        """Initialize the service with a small language model client."""
        self.client = client

    async def generate_cast(self, premise: str) -> tuple[list[Character], dict[str, CharacterCard]]:
        """Generate the whole cast with a card for every character."""


        raise NotImplementedError
