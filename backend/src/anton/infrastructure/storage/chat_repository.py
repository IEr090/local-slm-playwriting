from typing import Protocol

from anton.domain.models import Chat


class ChatRepository(Protocol):
    """Define an interface for storing the chats of all pages."""

    def load(self, chat_id: str) -> Chat:
        """Return the saved chat, or an empty chat with this id if nothing is saved yet."""
        ...

    def save(self, chat: Chat) -> None:
        """Replace the saved chat with the same id by the given one."""
        ...

    def clear(self) -> None:
        """Remove all saved chats, e.g. when a new play is started."""
        ...
