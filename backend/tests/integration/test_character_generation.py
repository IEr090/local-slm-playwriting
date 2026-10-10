from unittest import IsolatedAsyncioTestCase

from anton.application.character_service import CharacterService
from anton.domain.models import Cast
from tests.integration import create_test_client
from tests.unit.fakes import InMemoryCastRepository


USER_PROMPT = """The play takes place in Vienna in a small independent theatre that is close to bankruptcy.

Elena is the 47-year-old artistic director of the theatre. She built it many years ago and refuses to close it, even though the financial situation is getting worse.

Mark is a 31-year-old actor in the theatre. He respects Elena but is tired of working for very little money and is considering leaving for a commercial production.

Anna is a 28-year-old playwright. Elena wants to stage Anna's new play, but Anna believes Elena is changing the script too much and compromising her artistic vision.

Create complete character profiles for all three characters."""


class CharacterGenerationTest(IsolatedAsyncioTestCase):
    """Test cast generation against a local Ollama model."""

    async def test_generates_cast(self) -> None:
        """Generate complete profiles and cards for Elena, Mark, and Anna."""
        service = CharacterService(create_test_client(), InMemoryCastRepository())

        cast = await service.generate_cast(USER_PROMPT)

        self.assert_characters(cast)
        self.assert_relationships(cast)
        self.assert_cards(cast)

    def assert_characters(self, cast: Cast) -> None:
        """Check that every character is present, keeps the given age, and has no empty fields."""
        generated = [(character.name, character.surname, character.age) for character in cast.characters]

        self.assertEqual(len(cast.characters), 3, f"Generated characters: {generated}")
        self.assertEqual(
            {character.name.casefold(): character.age for character in cast.characters},
            {"elena": 47, "mark": 31, "anna": 28},
            f"Generated characters: {generated}",
        )
        self.assertEqual(len({character.id for character in cast.characters}), 3)

        empty_fields = {
            character.name: [
                field
                for field, value in character.model_dump().items()
                if isinstance(value, str) and not value.strip()
            ]
            for character in cast.characters
        }
        empty_fields = {
            name: fields
            for name, fields in empty_fields.items()
            if fields
        }

        self.assertFalse(
            empty_fields,
            f"Generated characters contain empty fields: {empty_fields}",
        )

    def assert_relationships(self, cast: Cast) -> None:
        """Check that every relationship links to another character of the cast."""
        ids = {character.id for character in cast.characters}

        for character in cast.characters:
            self.assertTrue(character.relationships, f"{character.name} has no relationships")
            for relationship in character.relationships:
                self.assertIn(
                    relationship.character_id,
                    ids - {character.id},
                    f"{character.name} has an unlinked relationship: {relationship.description}",
                )

    def assert_cards(self, cast: Cast) -> None:
        """Check that every character has a complete card."""
        self.assertEqual(set(cast.cards), {character.id for character in cast.characters})

        for character in cast.characters:
            card = cast.cards[character.id]
            self.assertEqual(card.role_label, character.dramatic_role)
            self.assertEqual(len(card.traits), 3)
            self.assertTrue(card.tagline.strip() and card.wants.strip() and card.fears.strip())
