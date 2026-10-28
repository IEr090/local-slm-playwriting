from unittest import IsolatedAsyncioTestCase

from anton.application.llm_schemas.outline_generation import GeneratedOutline, GeneratedOutlineRevision
from anton.application.story_service import OUTLINE_CAST_FIELDS, StoryService
from anton.domain.models import Cast, Character, ChatMessage, Chat, StoryBible
from anton.errors import CastNotFoundError, StoryNotFoundError, StoryOrderError
from tests.unit.fakes import FakeSLMClient, InMemoryCastRepository, InMemoryChatRepository, InMemoryStoryRepository, make_draft
from tests.unit.test_story_models import make_outline


USER_INPUT = "A lighthouse keeper dies and leaves the house to the housekeeper."
GENERATED_OUTLINE = GeneratedOutline(**(make_outline().model_dump() | {"title": "  The Salt House  "}))
REVISION = GeneratedOutlineRevision(
    outline=GeneratedOutline(**(make_outline().model_dump() | {"tone": "Black comedy."})),
    change_note="Darkened the tone.",
)


def make_cast() -> Cast:
    """Create a cast of one character."""
    return Cast(characters=[Character(id="elena", **make_draft().model_dump())], cards={})


def make_service(
    *responses,
    story: StoryBible | None = None,
    cast: Cast | None = None,
) -> tuple[StoryService, FakeSLMClient, InMemoryStoryRepository, InMemoryChatRepository]:
    """Create the story service with a fake model client and in-memory repositories."""
    client = FakeSLMClient(*responses)
    story_repository = InMemoryStoryRepository(story)
    chat_repository = InMemoryChatRepository()
    service = StoryService(client, story_repository, InMemoryCastRepository(cast), chat_repository)
    return service, client, story_repository, chat_repository


class StartPlayTest(IsolatedAsyncioTestCase):
    """Test starting a new Story Bible from the user's initial input."""

    async def test_saves_user_input_in_new_story(self) -> None:
        """Replace the old Story Bible with an empty one that keeps the input."""
        service, _, repository, _ = make_service(story=StoryBible(user_input="Old.", outline=make_outline()))

        service.start_play(USER_INPUT)

        self.assertEqual(repository.load(), StoryBible(user_input=USER_INPUT))

    async def test_forgets_old_chats(self) -> None:
        """Remove the chats of the previous play."""
        service, _, _, chats = make_service()
        chats.save(Chat(id="outline", messages=[ChatMessage(role="user", text="Darker.")]))

        service.start_play(USER_INPUT)

        self.assertEqual(chats.load("outline"), Chat(id="outline"))

    async def test_get_story_raises_before_start(self) -> None:
        """Report that no play has been started yet."""
        service, *_ = make_service()

        with self.assertRaises(StoryNotFoundError):
            service.get_story()


class GenerateOutlineTest(IsolatedAsyncioTestCase):
    """Test generating the outline from the user's input and the cast."""

    async def asyncSetUp(self) -> None:
        """Create the service with a started play and a saved cast."""
        self.service, self.client, self.repository, _ = make_service(
            GENERATED_OUTLINE, story=StoryBible(user_input=USER_INPUT), cast=make_cast(),
        )

    async def test_saves_generated_outline(self) -> None:
        """Save the outline with trimmed text and return the Story Bible."""
        story = await self.service.generate_outline()

        self.assertEqual(story.outline, make_outline())
        self.assertEqual(self.repository.load(), story)

    async def test_sends_input_and_cast_fields(self) -> None:
        """Give the model the user's input and only the cast fields the outline needs."""
        await self.service.generate_outline()

        prompt = self.client.calls[0]["user_prompt"]
        self.assertIn(f"# IDEA\n\n{USER_INPUT}", prompt)
        self.assertIn('"goal": "Save the theatre from bankruptcy."', prompt)
        self.assertNotIn("biography", prompt)
        self.assertIn("goal", OUTLINE_CAST_FIELDS)

    async def test_rejects_second_generation(self) -> None:
        """Reject generating the outline again once it exists."""
        await self.service.generate_outline()

        with self.assertRaises(StoryOrderError):
            await self.service.generate_outline()
        self.assertEqual(len(self.client.calls), 1)

    async def test_raises_without_cast(self) -> None:
        """Report that the cast is missing before calling the model."""
        service, client, *_ = make_service(GENERATED_OUTLINE, story=StoryBible(user_input=USER_INPUT))

        with self.assertRaises(CastNotFoundError):
            await service.generate_outline()
        self.assertEqual(client.calls, [])


class EditOutlineTest(IsolatedAsyncioTestCase):
    """Test editing the outline by hand."""

    async def test_saves_edited_outline(self) -> None:
        """Replace the outline with the user's version."""
        service, _, repository, _ = make_service(story=StoryBible(user_input=USER_INPUT, outline=make_outline()))
        edited = make_outline().model_copy(update={"title": "The Lamp"})

        story = service.edit_outline(edited)

        self.assertEqual(story.outline, edited)
        self.assertEqual(repository.load().outline, edited)

    async def test_warns_when_acts_were_built_from_older_outline(self) -> None:
        """Set the warning flag when the acts were built from the outline before the edit."""
        service, *_ = make_service(story=StoryBible(outline=make_outline(), acts_built_from_outline=make_outline()))

        story = service.edit_outline(make_outline().model_copy(update={"title": "The Lamp"}))

        self.assertTrue(story.outline_changed)

    async def test_rejects_edit_before_outline(self) -> None:
        """Reject editing an outline that has not been generated yet."""
        service, *_ = make_service(story=StoryBible(user_input=USER_INPUT))

        with self.assertRaises(StoryOrderError):
            service.edit_outline(make_outline())


class ReviseOutlineTest(IsolatedAsyncioTestCase):
    """Test revising the outline through the outline chat."""

    async def asyncSetUp(self) -> None:
        """Create the service with a saved outline."""
        self.service, self.client, self.repository, self.chats = make_service(
            REVISION, story=StoryBible(user_input=USER_INPUT, outline=make_outline()),
        )

    async def test_saves_revised_outline(self) -> None:
        """Replace the outline with the revised one."""
        reply = await self.service.revise_outline("Make it darker.")

        self.assertEqual(reply.story.outline.tone, "Black comedy.")
        self.assertEqual(self.repository.load().outline.tone, "Black comedy.")

    async def test_answers_with_change_note_and_changed_fields(self) -> None:
        """Answer with the model's sentence and the keys of the fields that changed."""
        reply = await self.service.revise_outline("Make it darker.")

        self.assertEqual(reply.reply.text, "Darkened the tone.")
        self.assertEqual(reply.reply.decision, "revised")
        self.assertEqual(reply.reply.updated, ["tone"])

    async def test_notes_when_nothing_changed(self) -> None:
        """Answer without a revision when the model returned the same outline."""
        unchanged = GeneratedOutlineRevision(outline=GeneratedOutline(**make_outline().model_dump()), change_note="Nothing to change.")
        service, *_ = make_service(unchanged, story=StoryBible(outline=make_outline()))

        reply = await service.revise_outline("Is the ending clear?")

        self.assertEqual((reply.reply.decision, reply.reply.updated), ("noted", []))

    async def test_saves_request_and_answer_in_chat(self) -> None:
        """Keep both messages in the outline chat."""
        reply = await self.service.revise_outline("Make it darker.")

        chat = self.service.get_chat("outline")
        self.assertEqual(chat.messages, [ChatMessage(role="user", text="Make it darker."), reply.reply])

    async def test_sends_only_last_two_messages(self) -> None:
        """Give the model the outline, the request and only the last two chat messages."""
        self.chats.save(Chat(id="outline", messages=[
            ChatMessage(role="user", text="First request."),
            ChatMessage(role="user", text="Second request."),
            ChatMessage(role="assistant", text="Third answer."),
        ]))

        await self.service.revise_outline("Make it darker.")

        prompt = self.client.calls[0]["user_prompt"]
        self.assertNotIn("First request.", prompt)
        self.assertIn("user: Second request.\nassistant: Third answer.", prompt)
        self.assertIn("# REQUEST\n\nMake it darker.", prompt)
        self.assertIn('"synopsis"', prompt)

    async def test_rejects_revision_before_outline(self) -> None:
        """Reject revising an outline that has not been generated yet."""
        service, client, *_ = make_service(REVISION, story=StoryBible(user_input=USER_INPUT))

        with self.assertRaises(StoryOrderError):
            await service.revise_outline("Make it darker.")
        self.assertEqual(client.calls, [])
