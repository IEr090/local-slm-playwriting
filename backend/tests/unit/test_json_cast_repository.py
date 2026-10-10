from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from anton.domain.models import Cast, Character, CharacterCard
from anton.infrastructure.storage import JsonCastRepository
from tests.unit.fakes import make_draft


def make_cast() -> Cast:
    """Create a cast of one character with its card."""
    character = Character(id="elena", **make_draft().model_dump())
    card = CharacterCard(role_label="protagonist", tagline="Director", traits=["A", "B", "C"], wants="Win.", fears="Loss.")
    return Cast(characters=[character], cards={"elena": card})


class JsonCastRepositoryTest(TestCase):
    """Test storing the cast in a JSON file."""

    def setUp(self) -> None:
        """Point the repository at a file inside a missing folder of a temporary directory."""
        self.directory = TemporaryDirectory()
        self.path = Path(self.directory.name) / "data" / "cast.json"
        self.repository = JsonCastRepository(self.path)

    def tearDown(self) -> None:
        """Remove the temporary directory."""
        self.directory.cleanup()

    def test_returns_none_before_first_save(self) -> None:
        """Return None when nothing is saved yet."""
        cast = self.repository.load()

        self.assertIsNone(cast)

    def test_loads_saved_cast(self) -> None:
        """Return the cast that was saved."""
        cast = make_cast()

        self.repository.save(cast)

        self.assertEqual(self.repository.load(), cast)

    def test_survives_restart(self) -> None:
        """Read the saved cast with a new repository on the same file."""
        cast = make_cast()

        self.repository.save(cast)

        self.assertEqual(JsonCastRepository(self.path).load(), cast)

    def test_leaves_no_temporary_file(self) -> None:
        """Keep only the cast file after saving."""
        cast = make_cast()

        self.repository.save(cast)

        self.assertEqual([path.name for path in self.path.parent.iterdir()], ["cast.json"])
