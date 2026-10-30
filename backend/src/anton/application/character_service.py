from uuid import uuid4

from anton.errors import CastNotFoundError, CharacterNotFoundError
from anton.application.language import play_language
from anton.application.llm_schemas.character_generation import GeneratedCard, GeneratedCast
from anton.application.mappers.character_mapper import to_characters
from anton.domain.models import Cast, Character, CharacterCard, CharacterDraft, CharacterWithCard
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient
from anton.infrastructure.storage import CastRepository


CARD_SOURCE_FIELDS = {
    "dramatic_role", "occupation_social_role", "personality",
    "goal", "motivation", "fear_weakness",
}


class CharacterService:
    """Generate and manage the characters of a play."""

    def __init__(self, client: SLMClient, repository: CastRepository) -> None:
        """Initialize the service with a small language model client and a cast repository."""
        self.client = client
        self.repository = repository

    async def generate_cast(self, premise: str) -> Cast:
        """Generate the whole cast with a card for every character and replace the saved cast."""
        generated = await self.client.generate(
            system_prompt=load_prompt("character_generation.md"),
            user_prompt=f"{premise}\n\n# LANGUAGE\n\nWrite every text field in {play_language(premise)}.",
            response_model=GeneratedCast,
            think=True,
        )
        characters = to_characters(generated.root)

        cards = {}
        for character in characters:
            cards[character.id] = await self._generate_card(character)

        cast = Cast(characters=characters, cards=cards)
        self.repository.save(cast)
        return cast

    def get_cast(self) -> Cast:
        """Return the saved cast."""
        cast = self.repository.load()
        if cast is None:
            raise CastNotFoundError("No cast has been generated yet.")
        return cast

    async def create_character(self, draft: CharacterDraft) -> CharacterWithCard:
        """Give a new character an id, generate its card and add both to the saved cast."""
        character = Character(id=str(uuid4()), **draft.model_dump())
        card = await self._generate_card(character)

        cast = self.repository.load() or Cast(characters=[], cards={})
        cast.characters.append(character)
        cast.cards[character.id] = card
        self.repository.save(cast)

        return CharacterWithCard(character=character, card=card)

    async def edit_character(self, character_id: str, draft: CharacterDraft) -> CharacterWithCard:
        """Replace the character and regenerate its card only if its source fields changed."""
        cast = self.get_cast()
        old = _find(cast, character_id)
        character = Character(id=character_id, **draft.model_dump())

        card = cast.cards.get(character_id)
        if card is None or old.model_dump(include=CARD_SOURCE_FIELDS) != character.model_dump(include=CARD_SOURCE_FIELDS):
            card = await self._generate_card(character)

        # Another request may have saved the cast while the card was generated.
        cast = self.get_cast()
        old = _find(cast, character_id)
        # The history is written by the story service and is not part of the user's profile.
        character.history = old.history
        cast.characters[cast.characters.index(old)] = character
        cast.cards[character_id] = card
        self.repository.save(cast)

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


def _find(cast: Cast, character_id: str) -> Character:
    """Return the character with the given id from the cast."""
    for character in cast.characters:
        if character.id == character_id:
            return character
    raise CharacterNotFoundError(f"Character {character_id} is not in the saved cast.")
