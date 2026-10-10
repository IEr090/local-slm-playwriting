from pathlib import Path

from anton.domain.models import Cast


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
        """Write the cast to a temporary file first so a crash never leaves a broken file."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(cast.model_dump_json(indent=2), encoding="utf-8")
        temporary.replace(self.path)
