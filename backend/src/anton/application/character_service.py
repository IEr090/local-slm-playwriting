from anton.application.llm_schemas.character_generation import GeneratedCast
from anton.application.mappers.character_mapper import to_characters
from anton.domain.models import Cast
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


class CharacterService:
    """Generate and manage the characters of a play."""

    def __init__(self, client: SLMClient) -> None:
        """Initialize the service with a small language model client."""
        self.client = client

    async def generate_cast(self, premise: str) -> Cast:
        """Generate the whole cast with a card for every character."""
        generated = await self.client.generate(
            system_prompt=load_prompt("character_generation.md"),
            user_prompt=premise,
            response_model=GeneratedCast,
        )
        characters = to_characters(generated.root)

        raise NotImplementedError
