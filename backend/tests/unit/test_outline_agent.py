import asyncio
import json
from unittest import IsolatedAsyncioTestCase

from anton.application.agent_chat import ChatMessage
from anton.application.llm_schemas.outline_generation import GeneratedOutline, OutlineChatTurn
from anton.application.outline_agent import OutlineAgent, create_outline_checkpointer
from anton.errors import SLMResponseError
from tests.unit.fakes import ScriptedSLMClient
from tests.unit.test_story_models import make_outline


IDEA = "A lighthouse keeper dies and leaves the house to the housekeeper."
CAST = '[{"name": "Margit"}]'
CHANGES = "tone: Black comedy."


def make_generated(**changes) -> GeneratedOutline:
    """Create a model answer with the outline, optionally with some fields changed."""
    return GeneratedOutline(**(make_outline().model_dump() | changes))


class OutlineAgentTestCase(IsolatedAsyncioTestCase):
    """Create outline agents whose model returns or raises prepared responses in order."""

    def make_agent(self, *responses) -> OutlineAgent:
        """Create an agent whose model returns or raises the prepared responses in order."""
        self.client = ScriptedSLMClient(*responses)
        return OutlineAgent(self.client, create_outline_checkpointer())


class GenerateTest(OutlineAgentTestCase):
    """Test writing the outline as the first node of the graph."""

    async def test_returns_generated_outline(self) -> None:
        """Return the outline the model wrote, with trimmed text."""
        agent = self.make_agent(make_generated(title="  The Salt House  "))

        outline = await agent.generate(IDEA, CAST)

        self.assertEqual(outline, make_outline())

    async def test_sends_idea_and_cast(self) -> None:
        """Give the model the user's idea and the cast and let it think."""
        agent = self.make_agent(make_generated())

        await agent.generate(IDEA, CAST)

        call = self.client.calls[0]
        self.assertEqual(call["user_prompt"], f"# IDEA\n\n{IDEA}\n\n# CAST\n\n{CAST}")
        self.assertIs(call["response_model"], GeneratedOutline)
        self.assertTrue(call["think"])

    async def test_starts_with_empty_history(self) -> None:
        """Write no chat message when the outline is generated."""
        agent = self.make_agent(make_generated())

        await agent.generate(IDEA, CAST)

        self.assertEqual(await agent.history(), [])

    async def test_waits_for_user_after_generation(self) -> None:
        """Answer the first chat message right after the outline is written."""
        agent = self.make_agent(make_generated(), OutlineChatTurn(reply="Darker in what way?", apply_changes=None))
        outline = await agent.generate(IDEA, CAST)

        result = await agent.send(outline, "Make it darker.")

        self.assertEqual(result.reply, "Darker in what way?")
        self.assertEqual(await agent.history(), [
            ChatMessage(role="user", content="Make it darker."),
            ChatMessage(role="assistant", content="Darker in what way?"),
        ])

    async def test_new_generation_forgets_old_chat(self) -> None:
        """Start a new conversation when the outline is generated again."""
        agent = self.make_agent(make_generated(), OutlineChatTurn(reply="How?", apply_changes=None), make_generated())
        await agent.send(await agent.generate(IDEA, CAST), "Make it darker.")

        await agent.generate(IDEA, CAST)

        self.assertEqual(await agent.history(), [])


class SendTest(OutlineAgentTestCase):
    """Test chatting with the outline agent about the outline from the user's form."""

    async def test_returns_reply_and_unchanged_outline(self) -> None:
        """Answer with the model reply and keep the outline when nothing was agreed."""
        agent = self.make_agent(OutlineChatTurn(reply="I suggest a colder tone. Confirm?", apply_changes=None))

        result = await agent.send(make_outline(), "Make it darker.")

        self.assertEqual(result.reply, "I suggest a colder tone. Confirm?")
        self.assertEqual(result.outline, make_outline())
        self.assertEqual(len(self.client.calls), 1)

    async def test_applies_agreed_changes(self) -> None:
        """Edit the outline with the agreed changes and answer with the held-back reply."""
        agent = self.make_agent(OutlineChatTurn(reply="Applying.", apply_changes=CHANGES), make_generated(tone="Black comedy."))

        result = await agent.send(make_outline(), "Yes.")

        self.assertEqual(result.reply, "Applying.")
        self.assertEqual(result.outline.tone, "Black comedy.")
        prompt = json.loads(self.client.calls[1]["user_prompt"])
        self.assertEqual(prompt, {"outline": make_outline().model_dump(), "changes": CHANGES})
        self.assertFalse(self.client.calls[1]["think"])

    async def test_whitespace_changes_do_not_edit(self) -> None:
        """Treat a whitespace-only apply_changes as nothing agreed."""
        agent = self.make_agent(OutlineChatTurn(reply="Sure?", apply_changes="  "))

        result = await agent.send(make_outline(), "Hm.")

        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(result.outline, make_outline())

    async def test_sends_outline_history_and_latest_message_apart(self) -> None:
        """Pass the outline, the earlier turns with speakers and the latest message on its own to the chat prompt."""
        agent = self.make_agent(
            OutlineChatTurn(reply="In what way?", apply_changes=None),
            OutlineChatTurn(reply="Colder, then. Confirm?", apply_changes=None),
        )

        await agent.send(make_outline(), "Change the tone.")
        await agent.send(make_outline(), "Colder.")

        prompt = json.loads(self.client.calls[1]["user_prompt"])
        self.assertEqual(prompt["outline"], make_outline().model_dump())
        self.assertEqual(
            prompt["history"],
            [{"speaker": "playwright", "text": "Change the tone."}, {"speaker": "dramaturg", "text": "In what way?"}],
        )
        self.assertEqual(prompt["playwright_message"], "Colder.")
        self.assertFalse(self.client.calls[1]["think"])

    async def test_takes_outline_from_form(self) -> None:
        """Replace the outline in the state with the one sent with the message."""
        agent = self.make_agent(
            OutlineChatTurn(reply="In what way?", apply_changes=None),
            OutlineChatTurn(reply="Noted.", apply_changes=None),
        )
        changed = make_outline().model_copy(update={"title": "The Lamp"})

        await agent.send(make_outline(), "Change it.")
        result = await agent.send(changed, "I renamed it myself.")

        self.assertEqual(result.outline.title, "The Lamp")
        self.assertEqual(json.loads(self.client.calls[1]["user_prompt"])["outline"]["title"], "The Lamp")

    async def test_answers_after_failed_model_call(self) -> None:
        """Start a new run on the same conversation when the previous one failed."""
        agent = self.make_agent(
            OutlineChatTurn(reply="In what way?", apply_changes=None),
            SLMResponseError("invalid answer"),
            OutlineChatTurn(reply="Colder, then. Confirm?", apply_changes=None),
        )

        await agent.send(make_outline(), "Change the tone.")
        with self.assertRaises(SLMResponseError):
            await agent.send(make_outline(), "Colder.")
        result = await agent.send(make_outline(), "Colder, please.")

        self.assertEqual(result.reply, "Colder, then. Confirm?")
        self.assertEqual(len(await agent.history()), 5)

    async def test_failed_edit_keeps_reply_out_of_history(self) -> None:
        """Leave the reply out of the history when the agreed changes could not be applied."""
        agent = self.make_agent(
            OutlineChatTurn(reply="Applying.", apply_changes=CHANGES),
            SLMResponseError("bad"),
            OutlineChatTurn(reply="Tell me more.", apply_changes=None),
        )

        with self.assertRaises(SLMResponseError):
            await agent.send(make_outline(), "Yes.")

        self.assertEqual(await agent.history(), [ChatMessage(role="user", content="Yes.")])
        result = await agent.send(make_outline(), "Try again.")
        self.assertEqual(result.reply, "Tell me more.")

    async def test_serializes_overlapping_sends(self) -> None:
        """Keep both turns in the history when two messages overlap."""
        agent = self.make_agent(
            OutlineChatTurn(reply="First.", apply_changes=None),
            OutlineChatTurn(reply="Second.", apply_changes=None),
        )

        await asyncio.gather(agent.send(make_outline(), "One."), agent.send(make_outline(), "Two."))

        self.assertEqual(len(await agent.history()), 4)

    async def test_forget_clears_history(self) -> None:
        """Forget the conversation, e.g. for a new play."""
        agent = self.make_agent(OutlineChatTurn(reply="How?", apply_changes=None))
        await agent.send(make_outline(), "Change it.")

        await agent.forget()

        self.assertEqual(await agent.history(), [])

    async def test_history_without_conversation_is_empty(self) -> None:
        """Return an empty history before anybody chatted about the outline."""
        agent = self.make_agent()

        self.assertEqual(await agent.history(), [])
