from typing import Protocol

from anton.domain.models import StoryBible


class StoryRepository(Protocol):
    """Define an interface for storing the Story Bible of the play."""

    def load(self) -> StoryBible | None:
        """Return the saved Story Bible, or None if nothing is saved yet."""
        ...

    def save(self, story: StoryBible) -> None:
        """Replace the saved Story Bible with the given one."""
        ...
