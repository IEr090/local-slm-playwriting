from pathlib import Path

from anton.domain.models import StoryBible
from anton.infrastructure.storage.atomic_file import write_atomically


class JsonStoryRepository:
    """Store the whole Story Bible (outline, acts with scenes, places) in one JSON file."""

    def __init__(self, path: Path) -> None:
        """Initialize the repository with the path of the JSON file."""
        self.path = path

    def load(self) -> StoryBible | None:
        """Return the saved Story Bible, or None if the file does not exist yet."""
        if not self.path.exists():
            return None
        return StoryBible.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, story: StoryBible) -> None:
        """Replace the saved Story Bible without ever leaving a broken file."""
        write_atomically(self.path, story.model_dump_json(indent=2))
