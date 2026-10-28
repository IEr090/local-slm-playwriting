import asyncio
import json
from unittest import IsolatedAsyncioTestCase

from anton.application.edit_agent import ChatMessage, EditAgent, create_checkpointer, edit_character
from anton.application.llm_schemas.character_edit import EditChatTurn, EditedCharacter
from anton.domain.models import Character, CharacterHistoryEntry, Relationship
from anton.errors import SLMResponseError
from tests.unit.fakes import FakeSLMClient, ScriptedSLMClient, make_draft


CHANGES = "Make her ten years older and more cynical."


HISTORY = [CharacterHistoryEntry(act_number=1, scene_number=2, change="Learns about the debt.")]


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


class EditCharacterTest(IsolatedAsyncioTestCase):
    """Test applying agreed changes to a character with the model."""

    async def asyncSetUp(self) -> None:
        """Create a fake model client that returns the edited character."""
        self.edited = make_edited()
        self.client = FakeSLMClient(self.edited)
        self.character = make_character()

    async def test_takes_profile_from_model_response(self) -> None:
        """Replace the profile fields with the ones the model returned."""
        result = await edit_character(self.client, self.character, CHANGES)

        self.assertEqual(result.model_dump(exclude={"id", "relationships", "history"}), self.edited.model_dump())

    async def test_keeps_id_and_relationships(self) -> None:
        """Keep the id and the relationships of the original character."""
        result = await edit_character(self.client, self.character, CHANGES)

        self.assertEqual(result.id, "first")
        self.assertEqual(result.relationships, [Relationship(character_id="second", description="Rivals.")])

    async def test_keeps_history(self) -> None:
        """Keep the history of the original character, which the model never sees."""
        result = await edit_character(self.client, self.character, CHANGES)

        self.assertEqual(result.history, HISTORY)

    async def test_sends_character_without_id_relationships_and_history(self) -> None:
        """Pass the profile without the id, the relationships and the history to the model."""
        await edit_character(self.client, self.character, CHANGES)

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual(prompt["character"], self.character.model_dump(exclude={"id", "relationships", "history"}))

    async def test_sends_changes(self) -> None:
        """Pass the agreed changes to the model."""
        await edit_character(self.client, self.character, CHANGES)

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual(prompt["changes"], CHANGES)

    async def test_does_not_let_model_think(self) -> None:
        """Ask the model to answer without thinking, which is much faster on local hardware."""
        await edit_character(self.client, self.character, CHANGES)

        self.assertFalse(self.client.calls[0]["think"])


class EditAgentFirstMessageTest(IsolatedAsyncioTestCase):
    """Test the first message of a conversation with the edit agent."""

    def make_agent(self, *responses) -> EditAgent:
        """Create an agent whose model returns the prepared responses in order."""
        self.client = ScriptedSLMClient(*responses)
        return EditAgent(self.client, create_checkpointer())

    async def test_returns_model_reply_and_unchanged_character(self) -> None:
        """Answer with the model reply and keep the character when nothing was agreed."""
        agent = self.make_agent(EditChatTurn(reply="What should change?", apply_changes=None))

        result = await agent.send(make_character(), "Change her.")

        self.assertEqual(result.reply, "What should change?")
        self.assertEqual(result.character, make_character())

    async def test_applies_agreed_changes(self) -> None:
        """Edit the character with the agreed changes and keep its id."""
        agent = self.make_agent(EditChatTurn(reply="Applying.", apply_changes=CHANGES), make_edited())

        result = await agent.send(make_character(), "Yes.")

        self.assertEqual(result.reply, "Applying.")
        self.assertEqual(result.character.id, "first")
        self.assertEqual(result.character.age, 57)
        self.assertEqual(result.character.history, HISTORY)
        self.assertEqual(json.loads(self.client.calls[1]["user_prompt"])["changes"], CHANGES)

    async def test_resets_changes_after_edit(self) -> None:
        """Clear the agreed changes in the state once they are applied."""
        agent = self.make_agent(EditChatTurn(reply="Applying.", apply_changes=CHANGES), make_edited())

        await agent.send(make_character(), "Yes.")

        state = await agent.graph.aget_state({"configurable": {"thread_id": "first"}})
        self.assertIsNone(state.values["changes"])

    async def test_empty_changes_do_not_edit(self) -> None:
        """Treat an empty apply_changes as nothing agreed."""
        agent = self.make_agent(EditChatTurn(reply="Sure?", apply_changes=""))

        result = await agent.send(make_character(), "Hm.")

        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(result.character, make_character())

    async def test_whitespace_changes_do_not_edit(self) -> None:
        """Treat a whitespace-only apply_changes as nothing agreed."""
        agent = self.make_agent(EditChatTurn(reply="Sure?", apply_changes="  "))

        result = await agent.send(make_character(), "Hm.")

        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(result.character, make_character())

    async def test_sends_character_and_history_to_chat(self) -> None:
        """Pass the character without id, relationships and character history, and the chat history to the chat prompt."""
        agent = self.make_agent(EditChatTurn(reply="What should change?", apply_changes=None))

        await agent.send(make_character(), "Change her.")

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual(prompt["character"], make_character().model_dump(exclude={"id", "relationships", "history"}))
        self.assertEqual(prompt["history"], [])
        self.assertEqual(prompt["playwright_message"], "Change her.")
        self.assertFalse(self.client.calls[0]["think"])


class EditAgentConversationTest(IsolatedAsyncioTestCase):
    """Test conversations with the edit agent over several messages."""

    def make_agent(self, *responses) -> EditAgent:
        """Create an agent whose model returns or raises the prepared responses in order."""
        self.client = ScriptedSLMClient(*responses)
        return EditAgent(self.client, create_checkpointer())

    async def test_continues_conversation(self) -> None:
        """Keep both turns in the history of the same character."""
        agent = self.make_agent(
            EditChatTurn(reply="In what way?", apply_changes=None),
            EditChatTurn(reply="Older, then. Apply?", apply_changes=None),
        )

        await agent.send(make_character(), "Change her.")
        result = await agent.send(make_character(), "Make her older.")

        self.assertEqual(result.reply, "Older, then. Apply?")
        self.assertEqual(
            await agent.history("first"),
            [
                ChatMessage(role="user", content="Change her."),
                ChatMessage(role="assistant", content="In what way?"),
                ChatMessage(role="user", content="Make her older."),
                ChatMessage(role="assistant", content="Older, then. Apply?"),
            ],
        )

    async def test_sends_earlier_turns_as_history_and_latest_message_apart(self) -> None:
        """Pass the earlier turns with speakers and the latest message on its own to the chat prompt."""
        agent = self.make_agent(
            EditChatTurn(reply="In what way?", apply_changes=None),
            EditChatTurn(reply="Older, then. Apply?", apply_changes=None),
        )

        await agent.send(make_character(), "Change her.")
        await agent.send(make_character(), "Make her older.")

        prompt = json.loads(self.client.calls[1]["user_prompt"])
        self.assertEqual(
            prompt["history"],
            [{"speaker": "playwright", "text": "Change her."}, {"speaker": "dramaturg", "text": "In what way?"}],
        )
        self.assertEqual(prompt["playwright_message"], "Make her older.")

    async def test_takes_character_from_form(self) -> None:
        """Replace the character in the state with the one sent with the message."""
        agent = self.make_agent(
            EditChatTurn(reply="In what way?", apply_changes=None),
            EditChatTurn(reply="Noted.", apply_changes=None),
        )
        changed = make_character().model_copy(update={"age": 99})

        await agent.send(make_character(), "Change her.")
        result = await agent.send(changed, "I changed her age myself.")

        self.assertEqual(result.character.age, 99)
        self.assertEqual(json.loads(self.client.calls[1]["user_prompt"])["character"]["age"], 99)

    async def test_keeps_conversations_of_characters_apart(self) -> None:
        """Give every character its own history."""
        agent = self.make_agent(
            EditChatTurn(reply="Hi Elena.", apply_changes=None),
            EditChatTurn(reply="Hi Mark.", apply_changes=None),
        )
        mark = make_character().model_copy(update={"id": "second", "name": "Mark"})

        await agent.send(make_character(), "About Elena.")
        await agent.send(mark, "About Mark.")

        self.assertEqual(
            await agent.history("second"),
            [ChatMessage(role="user", content="About Mark."), ChatMessage(role="assistant", content="Hi Mark.")],
        )

    async def test_answers_after_failed_model_call(self) -> None:
        """Start a new run on the same conversation when the previous one failed."""
        agent = self.make_agent(
            EditChatTurn(reply="In what way?", apply_changes=None),
            SLMResponseError("invalid answer"),
            EditChatTurn(reply="Older, then. Apply?", apply_changes=None),
        )

        await agent.send(make_character(), "Change her.")
        with self.assertRaises(SLMResponseError):
            await agent.send(make_character(), "Make her older.")
        result = await agent.send(make_character(), "Make her older, please.")

        self.assertEqual(result.reply, "Older, then. Apply?")
        self.assertEqual(
            await agent.history("first"),
            [
                ChatMessage(role="user", content="Change her."),
                ChatMessage(role="assistant", content="In what way?"),
                ChatMessage(role="user", content="Make her older."),
                ChatMessage(role="user", content="Make her older, please."),
                ChatMessage(role="assistant", content="Older, then. Apply?"),
            ],
        )

    async def test_failed_edit_keeps_reply_out_of_history(self) -> None:
        """Leave the reply out of the history when the agreed changes could not be applied."""
        agent = self.make_agent(
            EditChatTurn(reply="Applying.", apply_changes=CHANGES),
            SLMResponseError("bad"),
            EditChatTurn(reply="Tell me more.", apply_changes=None),
        )

        with self.assertRaises(SLMResponseError):
            await agent.send(make_character(), "Yes.")

        self.assertEqual(await agent.history("first"), [ChatMessage(role="user", content="Yes.")])
        result = await agent.send(make_character(), "Try again.")
        self.assertEqual(result.reply, "Tell me more.")

    async def test_serializes_sends_for_one_character(self) -> None:
        """Keep both turns in the history when two messages for one character overlap."""
        agent = self.make_agent(
            EditChatTurn(reply="First.", apply_changes=None),
            EditChatTurn(reply="Second.", apply_changes=None),
        )

        await asyncio.gather(agent.send(make_character(), "One."), agent.send(make_character(), "Two."))

        self.assertEqual(len(await agent.history("first")), 4)

    async def test_history_without_conversation_is_empty(self) -> None:
        """Return an empty history for a character nobody has chatted about."""
        agent = self.make_agent()

        self.assertEqual(await agent.history("unknown"), [])
