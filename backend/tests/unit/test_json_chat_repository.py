from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from anton.domain.models import Chat, ChatMessage
from anton.infrastructure.storage import JsonChatRepository


def make_chat(chat_id: str, text: str) -> Chat:
    """Create a chat with one user message and one answer."""
    return Chat(id=chat_id, messages=[
        ChatMessage(role="user", text=text),
        ChatMessage(role="assistant", text="Done.", decision="revised", updated=["Tone / Atmosphere"]),
    ])


class JsonChatRepositoryTest(TestCase):
    """Test storing the chats of all pages in one JSON file."""

    def setUp(self) -> None:
        """Point the repository at a file inside a missing folder of a temporary directory."""
        self.directory = TemporaryDirectory()
        self.path = Path(self.directory.name) / "data" / "chats.json"
        self.repository = JsonChatRepository(self.path)

    def tearDown(self) -> None:
        """Remove the temporary directory."""
        self.directory.cleanup()

    def test_returns_empty_chat_before_first_save(self) -> None:
        """Return a chat without messages when nothing is saved yet."""
        chat = self.repository.load("outline")

        self.assertEqual(chat, Chat(id="outline"))

    def test_loads_saved_chat(self) -> None:
        """Return the chat that was saved."""
        chat = make_chat("outline", "Make the ending darker.")

        self.repository.save(chat)

        self.assertEqual(self.repository.load("outline"), chat)

    def test_keeps_other_chats(self) -> None:
        """Replace only the chat with the same id."""
        outline = make_chat("outline", "Make the ending darker.")
        acts = make_chat("acts", "Act Two: Margit should be crueller.")
        self.repository.save(outline)
        self.repository.save(acts)

        changed = make_chat("outline", "Move it to the present day.")
        self.repository.save(changed)

        self.assertEqual(self.repository.load("outline"), changed)
        self.assertEqual(self.repository.load("acts"), acts)

    def test_survives_restart(self) -> None:
        """Read the saved chat with a new repository on the same file."""
        chat = make_chat("act-1", "Scene 3: Agnes should already know.")

        self.repository.save(chat)

        self.assertEqual(JsonChatRepository(self.path).load("act-1"), chat)

    def test_leaves_no_temporary_file(self) -> None:
        """Keep only the chats file after saving."""
        self.repository.save(make_chat("outline", "Make the ending darker."))

        self.assertEqual([path.name for path in self.path.parent.iterdir()], ["chats.json"])

    def test_clear_removes_all_chats(self) -> None:
        """Return empty chats after clearing, also when nothing was saved before."""
        self.repository.clear()
        self.repository.save(make_chat("outline", "Make the ending darker."))

        self.repository.clear()

        self.assertEqual(self.repository.load("outline"), Chat(id="outline"))
