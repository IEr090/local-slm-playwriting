import json
from unittest import IsolatedAsyncioTestCase
from uuid import UUID

from anton.application.agents.character_target import CharacterTarget
from anton.application.agents.chat_edit_agent import ChatEditAgent, create_checkpointer
from anton.application.character_service import CARD_SOURCE_FIELDS, CharacterService
from anton.errors import CastNotFoundError, CharacterNotFoundError
from anton.domain.models import Cast, Character, CharacterCard, CharacterHistoryEntry
from tests.unit.fakes import CARD, FakeSLMClient, InMemoryCastRepository, make_draft, make_generated_cast


def make_edit_agent() -> ChatEditAgent[Character]:
    """Create the edit agent of characters with a fake model client; the tests here never chat."""
    return ChatEditAgent(FakeSLMClient(), CharacterTarget(), create_checkpointer())


OLD_CARD = CharacterCard(role_label="protagonist", tagline="Old tagline", traits=["A", "B", "C"], wants="Old.", fears="Old.")


def make_cast() -> Cast:
    """Create a saved cast of two characters with old cards."""
    first = Character(id="first", **make_draft().model_dump())
    second = Character(id="second", **(make_draft().model_dump() | {"name": "Mark", "age": 31}))
    return Cast(characters=[first, second], cards={"first": OLD_CARD, "second": OLD_CARD})


class CreateCharacterTest(IsolatedAsyncioTestCase):
    """Test creating a single character with its card."""

    async def asyncSetUp(self) -> None:
        """Create the service with a fake model client and an empty repository."""
        self.client = FakeSLMClient(CARD)
        self.repository = InMemoryCastRepository()
        self.service = CharacterService(self.client, self.repository, make_edit_agent())
        self.draft = make_draft()

    async def test_gives_new_character_an_id(self) -> None:
        """Assign a UUID and keep the profile unchanged."""
        result = await self.service.create_character(self.draft)

        UUID(result.character.id)
        self.assertEqual(result.character.model_dump(exclude={"id", "history"}), self.draft.model_dump())
        self.assertEqual(result.character.history, [])

    async def test_builds_card_from_model_response(self) -> None:
        """Take the card text from the model and the role label from the profile."""
        result = await self.service.create_character(self.draft)

        self.assertEqual(result.card.model_dump(exclude={"role_label"}), CARD.model_dump())
        self.assertEqual(result.card.role_label, self.draft.dramatic_role)

    async def test_sends_only_card_source_fields(self) -> None:
        """Pass only the card source fields to the card prompt."""
        await self.service.create_character(self.draft)

        profile = self.client.calls[0]["user_prompt"].split("\n\n# LANGUAGE")[0]
        self.assertEqual(set(json.loads(profile)), CARD_SOURCE_FIELDS)

    async def test_asks_for_card_in_profile_language(self) -> None:
        """Name the language of the profile's text, so a Russian profile gets a Russian card."""
        russian = make_draft().model_copy(update={
            "occupation_social_role": "Нотариус",
            "personality": "Скрытный и расчётливый",
            "goal": "Получить наследство",
            "motivation": "Долги",
            "fear_weakness": "Боится разоблачения",
        })

        await self.service.create_character(russian)

        self.assertIn("Write every card field in Russian.", self.client.calls[0]["user_prompt"])

    async def test_asks_for_english_card_for_english_profile(self) -> None:
        """Keep English for an English profile."""
        await self.service.create_character(self.draft)

        self.assertIn("Write every card field in English.", self.client.calls[0]["user_prompt"])

    async def test_adds_character_to_saved_cast(self) -> None:
        """Save the new character and its card in the cast."""
        result = await self.service.create_character(self.draft)

        cast = self.repository.load()
        self.assertEqual(cast.characters, [result.character])
        self.assertEqual(cast.cards, {result.character.id: result.card})


class GenerateCastTest(IsolatedAsyncioTestCase):
    """Test generating and saving the whole cast."""

    async def test_saves_generated_cast(self) -> None:
        """Save the generated cast in the repository."""
        repository = InMemoryCastRepository()
        service = CharacterService(FakeSLMClient(make_generated_cast(), CARD), repository, make_edit_agent())

        cast = await service.generate_cast("A theatre in Vienna.")

        self.assertEqual(repository.load(), cast)
        self.assertEqual(repository.saves, 1)


class GetCastTest(IsolatedAsyncioTestCase):
    """Test reading the saved cast."""

    async def test_raises_without_saved_cast(self) -> None:
        """Report that no cast has been generated yet."""
        service = CharacterService(FakeSLMClient(CARD), InMemoryCastRepository(), make_edit_agent())

        with self.assertRaises(CastNotFoundError):
            service.get_cast()


class EditCharacterTest(IsolatedAsyncioTestCase):
    """Test editing a character of the saved cast."""

    async def asyncSetUp(self) -> None:
        """Create the service with a fake model client and a saved cast of two characters."""
        self.client = FakeSLMClient(CARD)
        self.repository = InMemoryCastRepository(make_cast())
        self.service = CharacterService(self.client, self.repository, make_edit_agent())

    async def test_replaces_only_edited_character(self) -> None:
        """Keep the id, the order and the other character unchanged."""
        draft = make_draft().model_copy(update={"age": 48})

        await self.service.edit_character("first", draft)

        cast = self.repository.load()
        self.assertEqual([character.id for character in cast.characters], ["first", "second"])
        self.assertEqual(cast.characters[0].age, 48)
        self.assertEqual(cast.characters[1], make_cast().characters[1])

    async def test_keeps_card_when_card_sources_unchanged(self) -> None:
        """Skip the model when only fields outside the card sources changed."""
        draft = make_draft().model_copy(update={"age": 48})

        result = await self.service.edit_character("first", draft)

        self.assertEqual(self.client.calls, [])
        self.assertEqual(result.card, OLD_CARD)

    async def test_regenerates_card_when_card_sources_changed(self) -> None:
        """Generate and save a new card once when a card source field changed."""
        draft = make_draft().model_copy(update={"goal": "Sell the theatre."})

        result = await self.service.edit_character("first", draft)

        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(result.card.tagline, CARD.tagline)
        self.assertEqual(self.repository.load().cards["first"], result.card)

    async def test_keeps_history(self) -> None:
        """Keep the character's history, which the user's profile does not contain."""
        cast = make_cast()
        cast.characters[0].history = [CharacterHistoryEntry(act_number=1, scene_number=2, change="Learns about the debt.")]
        self.repository.save(cast)

        result = await self.service.edit_character("first", make_draft().model_copy(update={"age": 48}))

        self.assertEqual(result.character.history, cast.characters[0].history)
        self.assertEqual(self.repository.load().characters[0].history, cast.characters[0].history)

    async def test_raises_for_unknown_character(self) -> None:
        """Report a character id that is not in the saved cast."""
        draft = make_draft()

        with self.assertRaises(CharacterNotFoundError):
            await self.service.edit_character("unknown", draft)
