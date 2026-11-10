import logging
from uuid import uuid4

from anton.application.agents.chat_edit_agent import ChatEditAgent, ChatEditResult, ChatMessage
from anton.application.language import play_language
from anton.application.llm_schemas.character_generation import GeneratedCard, GeneratedCast
from anton.application.mappers.character_mapper import to_characters
from anton.domain.models import Cast, Character, CharacterCard, CharacterDraft, CharacterWithCard
from anton.errors import CastNotFoundError, CharacterNotFoundError
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient
from anton.infrastructure.storage import CastRepository


logger = logging.getLogger(__name__)

CARD_SOURCE_FIELDS = {
    "dramatic_role", "occupation_social_role", "personality",
    "goal", "motivation", "fear_weakness",
}


class CharacterService:
    """Generate and manage the characters of a play."""

    def __init__(
        self,
        client: SLMClient,
        repository: CastRepository,
        edit_agent: ChatEditAgent[Character],
    ) -> None:
        """Initialize the service with a small language model client, a cast repository and the edit agent."""
        self.client = client
        self.repository = repository
        self.edit_agent = edit_agent

    async def generate_cast(self, premise: str) -> Cast:
        """Generate the whole cast with a card for every character and replace the saved cast."""
        logger.debug("Generating cast premise_length=%s", len(premise))
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
        logger.info("Saved generated cast character_count=%s", len(characters))
        return cast

    def get_cast(self) -> Cast:
        """Return the saved cast."""
        logger.debug("Reading cast")
        cast = self.repository.load()
        if cast is None:
            logger.warning("Cast is missing")
            raise CastNotFoundError("No cast has been generated yet.")
        return cast

    async def create_character(self, draft: CharacterDraft) -> CharacterWithCard:
        """Give a new character an id, generate its card and add both to the saved cast."""
        logger.debug("Creating character")
        character = Character(id=str(uuid4()), **draft.model_dump())
        card = await self._generate_card(character)

        cast = self.repository.load() or Cast(characters=[], cards={})
        cast.characters.append(character)
        cast.cards[character.id] = card
        self.repository.save(cast)
        logger.info("Saved created character character_id=%s", character.id)

        return CharacterWithCard(character=character, card=card)

    async def edit_character(self, character_id: str, draft: CharacterDraft) -> CharacterWithCard:
        """Replace the character and regenerate its card only if its source fields changed."""
        logger.debug("Editing character character_id=%s", character_id)
        cast = self.get_cast()
        old = _find(cast, character_id)
        character = Character(id=character_id, **draft.model_dump())

        card = cast.cards.get(character_id)
        old_source = old.model_dump(include=CARD_SOURCE_FIELDS)
        new_source = character.model_dump(include=CARD_SOURCE_FIELDS)
        if card is None or old_source != new_source:
            card = await self._generate_card(character)

        # Another request may have saved the cast while the card was generated.
        cast = self.get_cast()
        old = _find(cast, character_id)
        # The history is written by the story service and is not part of the user's profile.
        character.history = old.history
        cast.characters[cast.characters.index(old)] = character
        cast.cards[character_id] = card
        self.repository.save(cast)
        logger.info("Saved edited character character_id=%s", character_id)

        return CharacterWithCard(character=character, card=card)

    async def revise_character(
        self, character_id: str, draft: CharacterDraft, message: str,
    ) -> ChatEditResult[Character]:
        """Send the user's message with the character from their form to the edit agent; nothing is saved."""
        logger.debug("Revising character character_id=%s message_length=%s", character_id, len(message))
        character = Character(id=character_id, **draft.model_dump())
        # Every character has its own conversation.
        return await self.edit_agent.send(character_id, character, message)

    async def revise_history(self, character_id: str) -> list[ChatMessage]:
        """Return the chat history with the edit agent about the character."""
        logger.debug("Reading character chat character_id=%s", character_id)
        return await self.edit_agent.history(character_id)

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
    logger.warning("Character is missing character_id=%s", character_id)
    raise CharacterNotFoundError(f"Character {character_id} is not in the saved cast.")
