from pathlib import Path

from pydantic import TypeAdapter

from anton.domain.models import Chat
from anton.infrastructure.storage.atomic_file import write_atomically


CHATS = TypeAdapter(dict[str, Chat])


class JsonChatRepository:
    """Store the chats of all pages in one JSON file, keyed by chat id."""

    def __init__(self, path: Path) -> None:
        """Initialize the repository with the path of the JSON file."""
        self.path = path

    def load(self, chat_id: str) -> Chat:
        """Return the saved chat, or an empty chat with this id if it has no messages yet."""
        return self._load_all().get(chat_id) or Chat(id=chat_id)

    def save(self, chat: Chat) -> None:
        """Replace the chat with the same id and keep the other chats unchanged."""
        chats = self._load_all()
        chats[chat.id] = chat
        write_atomically(self.path, CHATS.dump_json(chats, indent=2).decode("utf-8"))

    def clear(self) -> None:
        """Remove all saved chats."""
        self.path.unlink(missing_ok=True)

    def _load_all(self) -> dict[str, Chat]:
        """Return all saved chats, or none if the file does not exist yet."""
        if not self.path.exists():
            return {}
        return CHATS.validate_json(self.path.read_text(encoding="utf-8"))
