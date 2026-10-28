import asyncio
import json
from unittest import IsolatedAsyncioTestCase

from anton.application.acts_agent import ActsAgent, create_acts_checkpointer
from anton.application.agent_chat import ChatMessage
from anton.application.llm_schemas.act_generation import ActsChatTurn, EditedAct, EditedActs, GeneratedActs
from anton.errors import SLMResponseError
from tests.unit.fakes import ScriptedSLMClient
from tests.unit.test_story_service import GENERATED_ACTS, summaries


OUTLINE = '{"title": "The Salt House"}'
CAST = '[{"name": "Margit"}]'
SYNOPSIS = "The will leaves everything to Agnes. Margit burns the logbook. Agnes gives the house to Elias."
CHANGES = "act 2 summary: Margit burns the logbook rather than relight the lamp."
EDITED = EditedActs([EditedAct(number=2, summary=" Margit burns the logbook rather than relight the lamp. ", dramatic_function="climax")])


class ActsAgentTestCase(IsolatedAsyncioTestCase):
    """Create acts agents whose model returns or raises prepared responses in order."""

    def make_agent(self, *responses) -> ActsAgent:
        """Create an agent whose model returns or raises the prepared responses in order."""
        self.client = ScriptedSLMClient(*responses)
        return ActsAgent(self.client, create_acts_checkpointer())


class GenerateTest(ActsAgentTestCase):
    """Test writing the acts as the first node of the graph."""

    async def test_returns_numbered_acts(self) -> None:
        """Number the acts from one in the model's order, with trimmed text."""
        agent = self.make_agent(GENERATED_ACTS)

        acts = await agent.generate(OUTLINE, CAST)

        self.assertEqual(acts, summaries())

    async def test_sends_outline_and_cast(self) -> None:
        """Give the model the outline and the cast and let it think."""
        agent = self.make_agent(GENERATED_ACTS)

        await agent.generate(OUTLINE, CAST)

        call = self.client.calls[0]
        self.assertEqual(call["user_prompt"], f"# OUTLINE\n\n{OUTLINE}\n\n# CAST\n\n{CAST}")
        self.assertIs(call["response_model"], GeneratedActs)
        self.assertTrue(call["think"])

    async def test_raises_for_no_acts(self) -> None:
        """Report an unusable answer when the model returned no acts."""
        agent = self.make_agent(GeneratedActs([]))

        with self.assertRaises(SLMResponseError):
            await agent.generate(OUTLINE, CAST)

    async def test_waits_for_user_after_generation(self) -> None:
        """Answer the first chat message right after the acts are written, with an empty history before it."""
        agent = self.make_agent(GENERATED_ACTS, ActsChatTurn(reply="Which act?", apply_changes=None))
        acts = await agent.generate(OUTLINE, CAST)
        self.assertEqual(await agent.history(), [])

        result = await agent.send(SYNOPSIS, acts, "Make Margit crueller.")

        self.assertEqual(result.reply, "Which act?")
        self.assertEqual(await agent.history(), [
            ChatMessage(role="user", content="Make Margit crueller."),
            ChatMessage(role="assistant", content="Which act?"),
        ])

    async def test_new_generation_forgets_old_chat(self) -> None:
        """Start a new conversation when the acts are generated again."""
        agent = self.make_agent(GENERATED_ACTS, ActsChatTurn(reply="Which act?", apply_changes=None), GENERATED_ACTS)
        await agent.send(SYNOPSIS, await agent.generate(OUTLINE, CAST), "Crueller.")

        await agent.generate(OUTLINE, CAST)

        self.assertEqual(await agent.history(), [])


class SendTest(ActsAgentTestCase):
    """Test chatting with the acts agent about the acts from the user's form."""

    async def test_returns_reply_and_unchanged_acts(self) -> None:
        """Answer with the model reply and keep the acts when nothing was agreed."""
        agent = self.make_agent(ActsChatTurn(reply="I suggest a crueller Margit in Act 2. Confirm?", apply_changes=None))

        result = await agent.send(SYNOPSIS, summaries(), "Act Two: crueller Margit.")

        self.assertEqual(result.reply, "I suggest a crueller Margit in Act 2. Confirm?")
        self.assertEqual(result.acts, summaries())
        self.assertEqual(len(self.client.calls), 1)

    async def test_applies_agreed_changes_to_named_act(self) -> None:
        """Replace only the act the model edited and answer with the held-back reply."""
        agent = self.make_agent(ActsChatTurn(reply="Applying.", apply_changes=CHANGES), EDITED)

        result = await agent.send(SYNOPSIS, summaries(), "Yes.")

        self.assertEqual(result.reply, "Applying.")
        self.assertEqual(result.acts[1].summary, "Margit burns the logbook rather than relight the lamp.")
        self.assertEqual([result.acts[0], result.acts[2]], [summaries()[0], summaries()[2]])
        prompt = json.loads(self.client.calls[1]["user_prompt"])
        self.assertEqual(prompt, {"acts": [act.model_dump() for act in summaries()], "changes": CHANGES})
        self.assertFalse(self.client.calls[1]["think"])

    async def test_ignores_edited_act_that_does_not_exist(self) -> None:
        """Keep the acts unchanged when the model edited an act number the play does not have."""
        unknown = EditedActs([EditedAct(number=9, summary="Storm.", dramatic_function="climax")])
        agent = self.make_agent(ActsChatTurn(reply="Applying.", apply_changes="act 9 summary: Storm."), unknown)

        result = await agent.send(SYNOPSIS, summaries(), "Yes.")

        self.assertEqual(result.acts, summaries())

    async def test_sends_synopsis_acts_history_and_latest_message_apart(self) -> None:
        """Pass the synopsis, the acts, the earlier turns and the latest message on its own to the chat prompt."""
        agent = self.make_agent(
            ActsChatTurn(reply="Which act?", apply_changes=None),
            ActsChatTurn(reply="Act 2, then. Confirm?", apply_changes=None),
        )

        await agent.send(SYNOPSIS, summaries(), "Crueller Margit.")
        await agent.send(SYNOPSIS, summaries(), "The second.")

        prompt = json.loads(self.client.calls[1]["user_prompt"])
        self.assertEqual(prompt["synopsis"], SYNOPSIS)
        self.assertEqual(prompt["acts"], [act.model_dump() for act in summaries()])
        self.assertEqual(
            prompt["history"],
            [{"speaker": "playwright", "text": "Crueller Margit."}, {"speaker": "dramaturg", "text": "Which act?"}],
        )
        self.assertEqual(prompt["playwright_message"], "The second.")
        self.assertFalse(self.client.calls[1]["think"])

    async def test_takes_acts_from_form(self) -> None:
        """Replace the acts in the state with the ones sent with the message."""
        agent = self.make_agent(
            ActsChatTurn(reply="Which act?", apply_changes=None),
            ActsChatTurn(reply="Noted.", apply_changes=None),
        )
        changed = summaries()
        changed[0].summary = "Margit arrives first."

        await agent.send(SYNOPSIS, summaries(), "Change it.")
        result = await agent.send(SYNOPSIS, changed, "I rewrote Act One myself.")

        self.assertEqual(result.acts[0].summary, "Margit arrives first.")
        self.assertEqual(json.loads(self.client.calls[1]["user_prompt"])["acts"][0]["summary"], "Margit arrives first.")

    async def test_answers_after_failed_model_call(self) -> None:
        """Start a new run on the same conversation when the previous one failed."""
        agent = self.make_agent(
            ActsChatTurn(reply="Which act?", apply_changes=None),
            SLMResponseError("invalid answer"),
            ActsChatTurn(reply="Act 2, then. Confirm?", apply_changes=None),
        )

        await agent.send(SYNOPSIS, summaries(), "Crueller Margit.")
        with self.assertRaises(SLMResponseError):
            await agent.send(SYNOPSIS, summaries(), "The second.")
        result = await agent.send(SYNOPSIS, summaries(), "The second act.")

        self.assertEqual(result.reply, "Act 2, then. Confirm?")
        self.assertEqual(len(await agent.history()), 5)

    async def test_failed_edit_keeps_reply_out_of_history(self) -> None:
        """Leave the reply out of the history when the agreed changes could not be applied."""
        agent = self.make_agent(
            ActsChatTurn(reply="Applying.", apply_changes=CHANGES),
            SLMResponseError("bad"),
            ActsChatTurn(reply="Tell me more.", apply_changes=None),
        )

        with self.assertRaises(SLMResponseError):
            await agent.send(SYNOPSIS, summaries(), "Yes.")

        self.assertEqual(await agent.history(), [ChatMessage(role="user", content="Yes.")])
        result = await agent.send(SYNOPSIS, summaries(), "Try again.")
        self.assertEqual(result.reply, "Tell me more.")

    async def test_serializes_overlapping_sends(self) -> None:
        """Keep both turns in the history when two messages overlap."""
        agent = self.make_agent(
            ActsChatTurn(reply="First.", apply_changes=None),
            ActsChatTurn(reply="Second.", apply_changes=None),
        )

        await asyncio.gather(agent.send(SYNOPSIS, summaries(), "One."), agent.send(SYNOPSIS, summaries(), "Two."))

        self.assertEqual(len(await agent.history()), 4)

    async def test_forget_clears_history(self) -> None:
        """Forget the conversation, e.g. for a new play."""
        agent = self.make_agent(ActsChatTurn(reply="Which act?", apply_changes=None))
        await agent.send(SYNOPSIS, summaries(), "Change it.")

        await agent.forget()

        self.assertEqual(await agent.history(), [])
