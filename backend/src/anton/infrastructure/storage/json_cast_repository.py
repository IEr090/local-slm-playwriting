from pathlib import Path

from anton.domain.models import Cast
from anton.infrastructure.storage.atomic_file import write_atomically


class JsonCastRepository:
    """Store the whole cast in one JSON file."""

    def __init__(self, path: Path) -> None:
        """Initialize the repository with the path of the JSON file."""
        self.path = path

    def load(self) -> Cast | None:
        """Return the saved cast, or None if the file does not exist yet."""
        if not self.path.exists():
            return None
        return Cast.model_validate_json(self.path.read_text(encoding="utf-8"))

    def save(self, cast: Cast) -> None:
        """Replace the saved cast without ever leaving a broken file."""
        write_atomically(self.path, cast.model_dump_json(indent=2))
