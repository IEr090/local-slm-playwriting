from uuid import uuid4

from anton.application.llm_schemas.character_generation import GeneratedCard, GeneratedCast
from anton.application.mappers.character_mapper import to_characters
from anton.domain.models import Cast, Character, CharacterCard, CharacterDraft, CharacterWithCard
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


CARD_SOURCE_FIELDS = {
    "dramatic_role", "occupation_social_role", "personality",
    "goal", "motivation", "fear_weakness",
}


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

    async def create_character(self, draft: CharacterDraft) -> CharacterWithCard:
        """Give a new character an id and generate its card."""
        character = Character(id=str(uuid4()), **draft.model_dump())
        card = await self._generate_card(character)
        return CharacterWithCard(character=character, card=card)

    async def _generate_card(self, character: Character) -> CharacterCard:
        """Generate the grid card from a character profile."""
        generated = await self.client.generate(
            system_prompt=load_prompt("character_card.md"),
            user_prompt=character.model_dump_json(include=CARD_SOURCE_FIELDS),
            response_model=GeneratedCard,
            think=False,
        )
        return CharacterCard(role_label=character.dramatic_role, **generated.model_dump())
