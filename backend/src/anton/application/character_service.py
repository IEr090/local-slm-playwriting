from anton.application.llm_schemas.character_generation import GeneratedCard, GeneratedCast
from anton.application.mappers.character_mapper import to_characters
from anton.domain.models import Cast, Character, CharacterCard
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
            think=True,
        )
        characters = to_characters(generated.root)

        cards = {}
        for character in characters:
            cards[character.id] = await self._generate_card(character)

        return Cast(characters=characters, cards=cards)

    async def _generate_card(self, character: Character) -> CharacterCard:
        """Generate the grid card from a character profile."""
        generated = await self.client.generate(
            system_prompt=load_prompt("character_card.md"),
            user_prompt=character.model_dump_json(exclude={"id", "relationships"}),
            response_model=GeneratedCard,
            think=False,
        )
        return CharacterCard(role_label=character.dramatic_role, **generated.model_dump())
