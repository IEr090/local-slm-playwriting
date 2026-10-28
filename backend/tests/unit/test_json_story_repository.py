from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from anton.domain.models import Act, Place, Scene, SceneText, StoryBible
from anton.infrastructure.storage import JsonStoryRepository
from tests.unit.test_story_models import make_outline


def make_story() -> StoryBible:
    """Create a Story Bible with an outline, one act with a written scene and one place."""
    scene = Scene(number=1, place_id="kitchen", place_notes="", character_ids=["agnes"], what_happens="Agnes waits.")
    act = Act(number=1, summary="The siblings arrive.", dramatic_function="setup", scenes=[scene])
    act.scene_texts = [SceneText(scene_number=1, text="AGNES: Eat.")]
    return StoryBible(
        user_input="A lighthouse and a will.",
        outline=make_outline(),
        acts=[act],
        places=[Place(id="kitchen", name="The keeper's kitchen", description="A stove.", significance="Home.")],
        acts_built_from_outline=make_outline(),
    )


class JsonStoryRepositoryTest(TestCase):
    """Test storing the Story Bible in a JSON file."""

    def setUp(self) -> None:
        """Point the repository at a file inside a missing folder of a temporary directory."""
        self.directory = TemporaryDirectory()
        self.path = Path(self.directory.name) / "data" / "story_bible.json"
        self.repository = JsonStoryRepository(self.path)

    def tearDown(self) -> None:
        """Remove the temporary directory."""
        self.directory.cleanup()

    def test_returns_none_before_first_save(self) -> None:
        """Return None when nothing is saved yet."""
        story = self.repository.load()

        self.assertIsNone(story)

    def test_loads_saved_story(self) -> None:
        """Return the Story Bible that was saved, even though the file also holds computed fields."""
        story = make_story()

        self.repository.save(story)

        self.assertEqual(self.repository.load(), story)

    def test_survives_restart(self) -> None:
        """Read the saved Story Bible with a new repository on the same file."""
        story = make_story()

        self.repository.save(story)

        self.assertEqual(JsonStoryRepository(self.path).load(), story)

    def test_leaves_no_temporary_file(self) -> None:
        """Keep only the Story Bible file after saving."""
        self.repository.save(make_story())

        self.assertEqual([path.name for path in self.path.parent.iterdir()], ["story_bible.json"])
