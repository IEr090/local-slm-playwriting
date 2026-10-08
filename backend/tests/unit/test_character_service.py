import json
from unittest import IsolatedAsyncioTestCase
from uuid import UUID

from anton.application.character_service import CARD_SOURCE_FIELDS, CharacterService
from tests.unit.fakes import CARD, FakeSLMClient, make_draft


class CreateCharacterTest(IsolatedAsyncioTestCase):
    """Test creating a single character with its card."""

    async def asyncSetUp(self) -> None:
        """Create the service with a fake model client."""
        self.client = FakeSLMClient(CARD)
        self.service = CharacterService(self.client)
        self.draft = make_draft()

    async def test_gives_new_character_an_id(self) -> None:
        """Assign a UUID and keep the profile unchanged."""
        result = await self.service.create_character(self.draft)

        UUID(result.character.id)
        self.assertEqual(result.character.model_dump(exclude={"id"}), self.draft.model_dump())

    async def test_builds_card_from_model_response(self) -> None:
        """Take the card text from the model and the role label from the profile."""
        result = await self.service.create_character(self.draft)

        self.assertEqual(result.card.model_dump(exclude={"role_label"}), CARD.model_dump())
        self.assertEqual(result.card.role_label, self.draft.dramatic_role)

    async def test_sends_only_card_source_fields(self) -> None:
        """Pass only the card source fields to the card prompt."""
        await self.service.create_character(self.draft)

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual(set(prompt), CARD_SOURCE_FIELDS)
