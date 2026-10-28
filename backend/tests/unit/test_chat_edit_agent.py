import asyncio
import json
from unittest import IsolatedAsyncioTestCase

from anton.application.agents.acts_target import ActsTarget
from anton.application.agents.character_target import CharacterTarget
from anton.application.agents.chat_edit_agent import ChatEditAgent, ChatMessage, create_checkpointer
from anton.application.agents.outline_target import OutlineTarget
from anton.application.llm_schemas.character_edit import EditedCharacter
from anton.application.llm_schemas.chat_turn import ChatTurn
from anton.application.llm_schemas.outline_generation import GeneratedOutline
from anton.domain.models import Character, CharacterHistoryEntry
from anton.errors import SLMResponseError
from tests.unit.fakes import ScriptedSLMClient, make_draft
from tests.unit.test_story_models import make_outline
from tests.unit.test_story_service import summaries


CHANGES = "age: 57\npersonality: Cynical and proud."
HISTORY = [CharacterHistoryEntry(act_number=1, scene_number=2, change="Learns about the debt.")]
IDEA = "A lighthouse keeper dies and leaves the house to the housekeeper."
CAST = '[{"name": "Margit"}]'


def make_character() -> Character:
    """Create a saved character with a relationship to another character and a history."""
    return Character(
        id="first",
        **(make_draft().model_dump() | {"relationships": [{"character_id": "second", "description": "Rivals."}]}),
        history=HISTORY,
    )


def make_edited() -> EditedCharacter:
    """Create a model answer with the requested changes applied."""
    return EditedCharacter(
        **(make_draft().model_dump(exclude={"relationships"}) | {"age": 57, "personality": "Cynical and proud."}),
    )


def turn(reply: str, changes: str | None = None) -> ChatTurn:
    """Create one chat answer of the model."""
    return ChatTurn(reply=reply, apply_changes=changes)


class AgentTestCase(IsolatedAsyncioTestCase):
    """Create agents whose model returns or raises prepared responses in order."""

    def make_agent(self, target, *responses) -> ChatEditAgent:
        """Create an agent for the target whose model returns or raises the prepared responses in order."""
        self.client = ScriptedSLMClient(*responses)
        return ChatEditAgent(self.client, target, create_checkpointer())


class FirstMessageTest(AgentTestCase):
    """Test the first message of a conversation, here about a character."""

    async def test_returns_model_reply_and_unchanged_data(self) -> None:
        """Answer with the model reply and keep the data when nothing was agreed."""
        agent = self.make_agent(CharacterTarget(), turn("What should change?"))

        result = await agent.send("first", make_character(), "Change her.")

        self.assertEqual(result.reply, "What should change?")
        self.assertEqual(result.data, make_character())

    async def test_applies_agreed_changes(self) -> None:
        """Edit the data with the agreed changes and answer with the held-back reply."""
        agent = self.make_agent(CharacterTarget(), turn("Applying.", CHANGES), make_edited())

        result = await agent.send("first", make_character(), "Yes.")

        self.assertEqual(result.reply, "Applying.")
        self.assertEqual((result.data.id, result.data.age, result.data.history), ("first", 57, HISTORY))
        prompt = json.loads(self.client.calls[1]["user_prompt"])
        self.assertEqual(prompt, {"character": CharacterTarget().view(make_character()), "changes": CHANGES})
        self.assertFalse(self.client.calls[1]["think"])

    async def test_resets_changes_after_edit(self) -> None:
        """Clear the agreed changes in the state once they are applied."""
        agent = self.make_agent(CharacterTarget(), turn("Applying.", CHANGES), make_edited())

        await agent.send("first", make_character(), "Yes.")

        state = await agent.graph.aget_state({"configurable": {"thread_id": "first"}})
        self.assertIsNone(state.values["changes"])

    async def test_empty_or_whitespace_changes_do_not_edit(self) -> None:
        """Treat an empty or whitespace-only apply_changes as nothing agreed."""
        agent = self.make_agent(CharacterTarget(), turn("Sure?", ""), turn("Sure?", "  "))

        await agent.send("first", make_character(), "Hm.")
        result = await agent.send("first", make_character(), "Hm.")

        self.assertEqual(len(self.client.calls), 2)
        self.assertEqual(result.data, make_character())

    async def test_sends_view_history_and_message_to_chat(self) -> None:
        """Pass what the target shows, the empty history and the message to the chat prompt, without thinking."""
        agent = self.make_agent(CharacterTarget(), turn("What should change?"))

        await agent.send("first", make_character(), "Change her.")

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual(prompt, {
            "character": make_character().model_dump(exclude={"id", "relationships", "history"}),
            "history": [],
            "playwright_message": "Change her.",
        })
        self.assertIs(self.client.calls[0]["response_model"], ChatTurn)
        self.assertFalse(self.client.calls[0]["think"])


class ConversationTest(AgentTestCase):
    """Test conversations over several messages."""

    async def test_continues_conversation(self) -> None:
        """Keep both turns in the history of the same thread."""
        agent = self.make_agent(CharacterTarget(), turn("In what way?"), turn("Older, then. Apply?"))

        await agent.send("first", make_character(), "Change her.")
        result = await agent.send("first", make_character(), "Make her older.")

        self.assertEqual(result.reply, "Older, then. Apply?")
        self.assertEqual(await agent.history("first"), [
            ChatMessage(role="user", content="Change her."),
            ChatMessage(role="assistant", content="In what way?"),
            ChatMessage(role="user", content="Make her older."),
            ChatMessage(role="assistant", content="Older, then. Apply?"),
        ])

    async def test_sends_earlier_turns_as_history_and_latest_message_apart(self) -> None:
        """Pass the earlier turns with speakers and the latest message on its own to the chat prompt."""
        agent = self.make_agent(CharacterTarget(), turn("In what way?"), turn("Older, then. Apply?"))

        await agent.send("first", make_character(), "Change her.")
        await agent.send("first", make_character(), "Make her older.")

        prompt = json.loads(self.client.calls[1]["user_prompt"])
        self.assertEqual(
            prompt["history"],
            [{"speaker": "playwright", "text": "Change her."}, {"speaker": "dramaturg", "text": "In what way?"}],
        )
        self.assertEqual(prompt["playwright_message"], "Make her older.")

    async def test_takes_data_from_form(self) -> None:
        """Replace the data in the state with the data sent with the message."""
        agent = self.make_agent(CharacterTarget(), turn("In what way?"), turn("Noted."))
        changed = make_character().model_copy(update={"age": 99})

        await agent.send("first", make_character(), "Change her.")
        result = await agent.send("first", changed, "I changed her age myself.")

        self.assertEqual(result.data.age, 99)
        self.assertEqual(json.loads(self.client.calls[1]["user_prompt"])["character"]["age"], 99)

    async def test_keeps_threads_apart(self) -> None:
        """Give every thread its own history, e.g. one per character."""
        agent = self.make_agent(CharacterTarget(), turn("Hi Elena."), turn("Hi Mark."))
        mark = make_character().model_copy(update={"id": "second", "name": "Mark"})

        await agent.send("first", make_character(), "About Elena.")
        await agent.send("second", mark, "About Mark.")

        self.assertEqual(
            await agent.history("second"),
            [ChatMessage(role="user", content="About Mark."), ChatMessage(role="assistant", content="Hi Mark.")],
        )

    async def test_answers_after_failed_model_call(self) -> None:
        """Start a new run on the same conversation when the previous one failed."""
        agent = self.make_agent(
            CharacterTarget(), turn("In what way?"), SLMResponseError("invalid answer"), turn("Older, then. Apply?"),
        )

        await agent.send("first", make_character(), "Change her.")
        with self.assertRaises(SLMResponseError):
            await agent.send("first", make_character(), "Make her older.")
        result = await agent.send("first", make_character(), "Make her older, please.")

        self.assertEqual(result.reply, "Older, then. Apply?")
        self.assertEqual(await agent.history("first"), [
            ChatMessage(role="user", content="Change her."),
            ChatMessage(role="assistant", content="In what way?"),
            ChatMessage(role="user", content="Make her older."),
            ChatMessage(role="user", content="Make her older, please."),
            ChatMessage(role="assistant", content="Older, then. Apply?"),
        ])

    async def test_failed_edit_keeps_reply_out_of_history(self) -> None:
        """Leave the reply out of the history when the agreed changes could not be applied."""
        agent = self.make_agent(CharacterTarget(), turn("Applying.", CHANGES), SLMResponseError("bad"), turn("Tell me more."))

        with self.assertRaises(SLMResponseError):
            await agent.send("first", make_character(), "Yes.")

        self.assertEqual(await agent.history("first"), [ChatMessage(role="user", content="Yes.")])
        result = await agent.send("first", make_character(), "Try again.")
        self.assertEqual(result.reply, "Tell me more.")

    async def test_serializes_sends_for_one_thread(self) -> None:
        """Keep both turns in the history when two messages for one thread overlap."""
        agent = self.make_agent(CharacterTarget(), turn("First."), turn("Second."))

        await asyncio.gather(
            agent.send("first", make_character(), "One."), agent.send("first", make_character(), "Two."),
        )

        self.assertEqual(len(await agent.history("first")), 4)

    async def test_forget_clears_history(self) -> None:
        """Forget the conversation of the thread, e.g. for a new play."""
        agent = self.make_agent(CharacterTarget(), turn("How?"))
        await agent.send("first", make_character(), "Change her.")

        await agent.forget("first")

        self.assertEqual(await agent.history("first"), [])

    async def test_history_without_conversation_is_empty(self) -> None:
        """Return an empty history for a thread nobody has chatted in."""
        agent = self.make_agent(CharacterTarget())

        self.assertEqual(await agent.history("unknown"), [])


class ContextTest(AgentTestCase):
    """Test what the model reads but never changes, here the synopsis while the acts are edited."""

    async def test_sends_context_to_chat(self) -> None:
        """Pass the context next to the data to the chat prompt."""
        agent = self.make_agent(ActsTarget(), turn("Which act?"))

        await agent.send("acts", summaries(), "Crueller Margit.", context={"synopsis": "Agnes keeps the light."})

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual(prompt["synopsis"], "Agnes keeps the light.")
        self.assertEqual(prompt["acts"], ActsTarget().view(summaries()))

    async def test_takes_context_from_form(self) -> None:
        """Use the context sent with the latest message."""
        agent = self.make_agent(ActsTarget(), turn("Which act?"), turn("Act 2, then?"))

        await agent.send("acts", summaries(), "Crueller.", context={"synopsis": "Old."})
        await agent.send("acts", summaries(), "The second.", context={"synopsis": "New."})

        self.assertEqual(json.loads(self.client.calls[1]["user_prompt"])["synopsis"], "New.")


class GenerateTest(AgentTestCase):
    """Test writing the data as the first node of the graph, here the outline."""

    async def test_returns_generated_data(self) -> None:
        """Return the data the model wrote, mapped by the target."""
        agent = self.make_agent(OutlineTarget(), GeneratedOutline(**(make_outline().model_dump() | {"title": " The Salt House "})))

        outline = await agent.generate("outline", {"idea": IDEA, "cast": CAST})

        self.assertEqual(outline, make_outline())

    async def test_sends_target_input_and_lets_model_think(self) -> None:
        """Give the model the input the target builds from the source and let it think."""
        agent = self.make_agent(OutlineTarget(), GeneratedOutline(**make_outline().model_dump()))

        await agent.generate("outline", {"idea": IDEA, "cast": CAST})

        call = self.client.calls[0]
        self.assertEqual(call["user_prompt"], OutlineTarget().generate_input({"idea": IDEA, "cast": CAST}))
        self.assertIs(call["response_model"], GeneratedOutline)
        self.assertTrue(call["think"])

    async def test_waits_for_user_after_generation(self) -> None:
        """Answer the first chat message right after the data is written, with an empty history before it."""
        agent = self.make_agent(OutlineTarget(), GeneratedOutline(**make_outline().model_dump()), turn("Darker in what way?"))
        outline = await agent.generate("outline", {"idea": IDEA, "cast": CAST})
        self.assertEqual(await agent.history("outline"), [])

        result = await agent.send("outline", outline, "Make it darker.")

        self.assertEqual(result.reply, "Darker in what way?")
        self.assertEqual(len(await agent.history("outline")), 2)

    async def test_new_generation_forgets_old_chat(self) -> None:
        """Start a new conversation when the data is generated again."""
        generated = GeneratedOutline(**make_outline().model_dump())
        agent = self.make_agent(OutlineTarget(), generated, turn("How?"), generated)
        await agent.send("outline", await agent.generate("outline", {"idea": IDEA, "cast": CAST}), "Darker.")

        await agent.generate("outline", {"idea": IDEA, "cast": CAST})

        self.assertEqual(await agent.history("outline"), [])
