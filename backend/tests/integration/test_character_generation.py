from unittest import IsolatedAsyncioTestCase

from anton.domain.models import Characters
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import OllamaClient


USER_PROMPT = """The play takes place in Vienna in a small independent theatre that is close to bankruptcy.

Elena is the 47-year-old artistic director of the theatre. She built it many years ago and refuses to close it, even though the financial situation is getting worse.

Mark is a 31-year-old actor in the theatre. He respects Elena but is tired of working for very little money and is considering leaving for a commercial production.

Anna is a 28-year-old playwright. Elena wants to stage Anna's new play, but Anna believes Elena is changing the script too much and compromising her artistic vision.

Create complete character profiles for all three characters."""


class CharacterGenerationTest(IsolatedAsyncioTestCase):
    """Test character generation against a local Ollama model."""

    async def test_generates_all_characters(self) -> None:
        """Generate and validate profiles for Elena, Mark, and Anna."""
        client = OllamaClient(model="qwen3:4b")

        characters = await client.generate(
            system_prompt=load_prompt("character_generation.md"),
            user_prompt=USER_PROMPT,
            response_model=Characters,
        )

        self.assertEqual(len(characters.root), 3)
        self.assertEqual(
            {character.name.casefold() for character in characters.root},
            {"elena", "mark", "anna"},
        )
        empty_fields = {
            character.name: [
                field
                for field, value in character.model_dump().items()
                if isinstance(value, str) and not value.strip()
            ]
            for character in characters.root
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
