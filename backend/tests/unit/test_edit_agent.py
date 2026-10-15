import json
from unittest import IsolatedAsyncioTestCase

from anton.application.edit_agent import edit_character
from anton.application.llm_schemas.character_edit import EditedCharacter
from anton.domain.models import Character, Relationship
from tests.unit.fakes import FakeSLMClient, make_draft


CHANGES = "Make her ten years older and more cynical."


def make_character() -> Character:
    """Create a saved character with a relationship to another character."""
    return Character(
        id="first",
        **(make_draft().model_dump() | {"relationships": [{"character_id": "second", "description": "Rivals."}]}),
    )


def make_edited() -> EditedCharacter:
    """Create a model answer with the requested changes applied."""
    return EditedCharacter(
        **(make_draft().model_dump(exclude={"relationships"}) | {"age": 57, "personality": "Cynical and proud."}),
    )


class EditCharacterTest(IsolatedAsyncioTestCase):
    """Test applying agreed changes to a character with the model."""

    async def asyncSetUp(self) -> None:
        """Create a fake model client that returns the edited character."""
        self.edited = make_edited()
        self.client = FakeSLMClient(self.edited)
        self.character = make_character()

    async def test_takes_profile_from_model_response(self) -> None:
        """Replace the profile fields with the ones the model returned."""
        result = await edit_character(self.client, self.character, CHANGES)

        self.assertEqual(result.model_dump(exclude={"id", "relationships"}), self.edited.model_dump())

    async def test_keeps_id_and_relationships(self) -> None:
        """Keep the id and the relationships of the original character."""
        result = await edit_character(self.client, self.character, CHANGES)

        self.assertEqual(result.id, "first")
        self.assertEqual(result.relationships, [Relationship(character_id="second", description="Rivals.")])

    async def test_sends_character_without_id_and_relationships(self) -> None:
        """Pass the profile without the id and the relationships to the model."""
        await edit_character(self.client, self.character, CHANGES)

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual(prompt["character"], self.character.model_dump(exclude={"id", "relationships"}))

    async def test_sends_changes(self) -> None:
        """Pass the agreed changes to the model."""
        await edit_character(self.client, self.character, CHANGES)

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual(prompt["changes"], CHANGES)

    async def test_asks_model_to_think(self) -> None:
        """Let the model think; the settings may still switch thinking off."""
        await edit_character(self.client, self.character, CHANGES)

        self.assertTrue(self.client.calls[0]["think"])
