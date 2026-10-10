from typing import Protocol

from anton.domain.models import Cast


class CastRepository(Protocol):
    """Define an interface for storing the cast."""

    def load(self) -> Cast | None:
        """Return the saved cast, or None if nothing is saved yet."""
        ...

    def save(self, cast: Cast) -> None:
        """Replace the saved cast with the given one."""
        ...
