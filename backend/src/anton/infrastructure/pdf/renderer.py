from typing import Protocol

from anton.domain.models import PlayDocument


class PdfRenderer(Protocol):
    """Define an interface for something that typesets the finished play into a PDF."""

    def render(self, document: PlayDocument) -> bytes:
        """Return the bytes of a PDF of the play."""
        ...
