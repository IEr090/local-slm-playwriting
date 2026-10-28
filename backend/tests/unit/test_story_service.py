from unittest import IsolatedAsyncioTestCase

from anton.application.agents.acts_target import ActsTarget
from anton.application.agents.chat_edit_agent import ChatEditAgent, create_checkpointer
from anton.application.agents.outline_target import OutlineTarget
from anton.application.llm_schemas.act_generation import GeneratedAct, GeneratedActs
from anton.application.llm_schemas.chat_turn import ChatTurn
from anton.application.llm_schemas.outline_generation import GeneratedOutline
from anton.application.story_service import OUTLINE_CAST_FIELDS, StoryService
from anton.domain.models import Act, ActSummary, Cast, Character, StoryBible
from anton.errors import ActNotFoundError, CastNotFoundError, StoryNotFoundError, StoryOrderError
from tests.unit.fakes import FakeSLMClient, InMemoryCastRepository, InMemoryStoryRepository, make_draft
from tests.unit.test_story_models import make_outline


USER_INPUT = "A lighthouse keeper dies and leaves the house to the housekeeper."
GENERATED_OUTLINE = GeneratedOutline(**(make_outline().model_dump() | {"title": "  The Salt House  "}))
PROPOSAL = ChatTurn(reply="I suggest a darker tone. Confirm?", apply_changes=None)
ACTS_PROPOSAL = ChatTurn(reply="I suggest a crueller Margit in Act 2. Confirm?", apply_changes=None)

GENERATED_ACTS = GeneratedActs([
    GeneratedAct(summary=" The siblings arrive. ", dramatic_function="setup"),
    GeneratedAct(summary="Margit burns the logbook.", dramatic_function="climax"),
    GeneratedAct(summary="Agnes gives the house to Elias.", dramatic_function="resolution"),
])


def make_acts() -> list[Act]:
    """Create the three acts that GENERATED_ACTS describes."""
    return [
        Act(number=1, summary="The siblings arrive.", dramatic_function="setup"),
        Act(number=2, summary="Margit burns the logbook.", dramatic_function="climax"),
        Act(number=3, summary="Agnes gives the house to Elias.", dramatic_function="resolution"),
    ]


def summaries() -> list[ActSummary]:
    """Create the acts as the user's form sends them."""
    return [ActSummary(**act.model_dump(include=set(ActSummary.model_fields))) for act in make_acts()]


def make_cast() -> Cast:
    """Create a cast of one character."""
    return Cast(characters=[Character(id="elena", **make_draft().model_dump())], cards={})


def make_service(
    *responses,
    story: StoryBible | None = None,
    cast: Cast | None = None,
) -> tuple[StoryService, FakeSLMClient, InMemoryStoryRepository, ChatEditAgent]:
    """Create the story service with in-memory repositories and page agents that share a fake model client."""
    client = FakeSLMClient(*responses)
    story_repository = InMemoryStoryRepository(story)
    outline_agent = ChatEditAgent(client, OutlineTarget(), create_checkpointer())
    acts_agent = ChatEditAgent(client, ActsTarget(), create_checkpointer())
    service = StoryService(story_repository, InMemoryCastRepository(cast), outline_agent, acts_agent)
    return service, client, story_repository, outline_agent


class StartPlayTest(IsolatedAsyncioTestCase):
    """Test starting a new Story Bible from the user's initial input."""

    async def test_saves_user_input_in_new_story(self) -> None:
        """Replace the old Story Bible with an empty one that keeps the input."""
        service, _, repository, _ = make_service(story=StoryBible(user_input="Old.", outline=make_outline()))

        await service.start_play(USER_INPUT)

        self.assertEqual(repository.load(), StoryBible(user_input=USER_INPUT))

    async def test_forgets_old_chats(self) -> None:
        """Forget the conversations about the outline and the acts of the previous play."""
        service, *_ = make_service(PROPOSAL, story=StoryBible(outline=make_outline(), acts=make_acts()))
        await service.revise_outline(make_outline(), "Make it darker.")
        await service.revise_acts(summaries(), "Act Two: crueller Margit.")

        await service.start_play(USER_INPUT)

        self.assertEqual(await service.outline_history(), [])
        self.assertEqual(await service.acts_history(), [])

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
    """Test sending a chat message about the outline to the outline agent."""

    async def test_returns_agent_reply_and_outline_from_form(self) -> None:
        """Answer with the agent's reply and the outline the user sent from the form."""
        form = make_outline().model_copy(update={"title": "The Lamp"})
        service, *_ = make_service(PROPOSAL, story=StoryBible(outline=make_outline()))

        reply = await service.revise_outline(form, "Make it darker.")

        self.assertEqual(reply.reply, PROPOSAL.reply)
        self.assertEqual(reply.data, form)

    async def test_does_not_save(self) -> None:
        """Leave the saved outline unchanged; the user saves it from the form."""
        service, _, repository, _ = make_service(PROPOSAL, story=StoryBible(outline=make_outline()))

        await service.revise_outline(make_outline().model_copy(update={"title": "The Lamp"}), "Make it darker.")

        self.assertEqual(repository.load().outline, make_outline())
        self.assertEqual(repository.saves, 0)

    async def test_keeps_history(self) -> None:
        """Return the user's message and the agent's answer as the chat history."""
        service, *_ = make_service(PROPOSAL, story=StoryBible(outline=make_outline()))

        await service.revise_outline(make_outline(), "Make it darker.")

        history = await service.outline_history()
        self.assertEqual([(message.role, message.content) for message in history], [
            ("user", "Make it darker."), ("assistant", PROPOSAL.reply),
        ])

    async def test_rejects_revision_before_outline(self) -> None:
        """Reject chatting about an outline that has not been generated yet."""
        service, client, *_ = make_service(PROPOSAL, story=StoryBible(user_input=USER_INPUT))

        with self.assertRaises(StoryOrderError):
            await service.revise_outline(make_outline(), "Make it darker.")
        self.assertEqual(client.calls, [])


class GenerateActsTest(IsolatedAsyncioTestCase):
    """Test generating the act summaries from the outline and the cast."""

    async def asyncSetUp(self) -> None:
        """Create the service with a saved outline and cast."""
        self.service, self.client, self.repository, _ = make_service(
            GENERATED_ACTS, story=StoryBible(user_input=USER_INPUT, outline=make_outline()), cast=make_cast(),
        )

    async def test_saves_numbered_acts(self) -> None:
        """Number the acts from one in the model's order, as drafts without scenes."""
        story = await self.service.generate_acts()

        self.assertEqual(story.acts, make_acts())
        self.assertEqual(self.repository.load().acts, make_acts())

    async def test_remembers_outline_for_warning(self) -> None:
        """Remember the outline the acts were built from, so a later edit can be noticed."""
        story = await self.service.generate_acts()

        self.assertEqual(story.acts_built_from_outline, make_outline())
        self.assertFalse(story.outline_changed)

    async def test_sends_outline_and_short_cast(self) -> None:
        """Give the model the outline and only the names, roles and goals of the cast."""
        await self.service.generate_acts()

        prompt = self.client.calls[0]["user_prompt"]
        self.assertIn('"synopsis"', prompt)
        self.assertIn('"dramatic_role": "protagonist"', prompt)
        self.assertNotIn("internal_conflict", prompt)

    async def test_regenerates_before_approval(self) -> None:
        """Replace the acts when they are generated again before they are approved."""
        await self.service.generate_acts()

        story = await self.service.generate_acts()

        self.assertEqual(len(story.acts), 3)
        self.assertEqual(len(self.client.calls), 2)

    async def test_rejects_generation_after_approval(self) -> None:
        """Reject generating the acts again once they are approved."""
        await self.service.generate_acts()
        self.service.approve_acts()

        with self.assertRaises(StoryOrderError):
            await self.service.generate_acts()

    async def test_rejects_generation_before_outline(self) -> None:
        """Reject generating acts before the outline exists."""
        service, client, *_ = make_service(GENERATED_ACTS, story=StoryBible(user_input=USER_INPUT), cast=make_cast())

        with self.assertRaises(StoryOrderError):
            await service.generate_acts()
        self.assertEqual(client.calls, [])

class EditActTest(IsolatedAsyncioTestCase):
    """Test editing an act by hand."""

    async def asyncSetUp(self) -> None:
        """Create the service with saved acts."""
        self.service, _, self.repository, _ = make_service(story=StoryBible(outline=make_outline(), acts=make_acts()))

    async def test_saves_edited_act(self) -> None:
        """Replace the summary and dramatic function of only the edited act."""
        story = self.service.edit_act(2, "Margit hides the logbook.", "development")

        self.assertEqual(story.acts[1].summary, "Margit hides the logbook.")
        self.assertEqual(story.acts[1].dramatic_function, "development")
        self.assertEqual(self.repository.load().acts[0], make_acts()[0])

    async def test_warns_when_scenes_were_built_from_older_summary(self) -> None:
        """Set the warning flag when the act's scenes were built from the summary before the edit."""
        acts = make_acts()
        acts[0].scenes_built_from_summary = acts[0].summary
        service, *_ = make_service(story=StoryBible(outline=make_outline(), acts=acts))

        story = service.edit_act(1, "Margit arrives first.", "setup")

        self.assertTrue(story.acts[0].summary_changed)

    async def test_raises_for_unknown_act(self) -> None:
        """Report an act number that does not exist."""
        with self.assertRaises(ActNotFoundError):
            self.service.edit_act(9, "Nothing.", "setup")


class ReviseActsTest(IsolatedAsyncioTestCase):
    """Test sending a chat message about the acts to the acts agent."""

    async def test_returns_agent_reply_and_acts_from_form(self) -> None:
        """Answer with the agent's reply and the acts the user sent from the form."""
        form = summaries()
        form[1].summary = "Margit hides the logbook."
        service, *_ = make_service(ACTS_PROPOSAL, story=StoryBible(outline=make_outline(), acts=make_acts()))

        reply = await service.revise_acts(form, "Act Two: crueller Margit.")

        self.assertEqual(reply.reply, ACTS_PROPOSAL.reply)
        self.assertEqual(reply.data, form)

    async def test_sends_saved_synopsis(self) -> None:
        """Give the agent the synopsis of the saved outline."""
        service, client, *_ = make_service(ACTS_PROPOSAL, story=StoryBible(outline=make_outline(), acts=make_acts()))

        await service.revise_acts(summaries(), "Act Two: crueller Margit.")

        self.assertIn(make_outline().synopsis, client.calls[0]["user_prompt"])

    async def test_does_not_save(self) -> None:
        """Leave the saved acts unchanged; the user saves them from the form."""
        service, _, repository, _ = make_service(ACTS_PROPOSAL, story=StoryBible(outline=make_outline(), acts=make_acts()))

        await service.revise_acts(summaries(), "Act Two: crueller Margit.")

        self.assertEqual(repository.load().acts, make_acts())
        self.assertEqual(repository.saves, 0)

    async def test_keeps_history(self) -> None:
        """Return the user's message and the agent's answer as the chat history."""
        service, *_ = make_service(ACTS_PROPOSAL, story=StoryBible(outline=make_outline(), acts=make_acts()))

        await service.revise_acts(summaries(), "Act Two: crueller Margit.")

        self.assertEqual([message.role for message in await service.acts_history()], ["user", "assistant"])

    async def test_rejects_revision_before_acts(self) -> None:
        """Reject chatting about acts that have not been generated yet."""
        service, client, *_ = make_service(ACTS_PROPOSAL, story=StoryBible(outline=make_outline()))

        with self.assertRaises(StoryOrderError):
            await service.revise_acts(summaries(), "Act Two: crueller Margit.")
        self.assertEqual(client.calls, [])


class ApproveActsTest(IsolatedAsyncioTestCase):
    """Test approving the acts."""

    async def test_approves_acts(self) -> None:
        """Mark the acts as approved and save it."""
        service, _, repository, _ = make_service(story=StoryBible(outline=make_outline(), acts=make_acts()))

        story = service.approve_acts()

        self.assertTrue(story.acts_approved)
        self.assertTrue(repository.load().acts_approved)

    async def test_rejects_approval_before_acts(self) -> None:
        """Reject approving acts that have not been generated yet."""
        service, *_ = make_service(story=StoryBible(outline=make_outline()))

        with self.assertRaises(StoryOrderError):
            service.approve_acts()
