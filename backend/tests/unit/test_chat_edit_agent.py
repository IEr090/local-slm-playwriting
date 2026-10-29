import asyncio
import json
import tempfile
from pathlib import Path
from unittest import IsolatedAsyncioTestCase, TestCase

from anton.application.agents.acts_target import ActsTarget
from anton.application.agents.character_target import CharacterTarget
from anton.application.agents.chat_edit_agent import ChatEditAgent, ChatMessage, create_checkpointer, is_agreement, language_of
from anton.application.agents.outline_target import OutlineTarget
from anton.application.llm_schemas.character_edit import EditedCharacter
from anton.application.llm_schemas.chat_turn import ChatTurn
from anton.application.llm_schemas.outline_generation import GeneratedOutline
from anton.domain.models import Character, CharacterHistoryEntry
from anton.errors import SLMResponseError
from tests.unit.fakes import ScriptedSLMClient, make_draft
from tests.unit.test_story_models import make_outline
from tests.unit.test_story_service import summaries


# Free text, so the edit goes to the model; changes written as `field: value` are applied without it.
CHANGES = "Make her 57 and cynical."
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
            "reply_language": "English",
            "text_language": "English",
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


class LanguageTest(AgentTestCase):
    """Test that the reply and the edited text keep their own languages."""

    async def test_names_reply_and_text_language(self) -> None:
        """Take the reply language from the message and the text language from the data."""
        agent = self.make_agent(CharacterTarget(), turn("Что изменить?"))

        await agent.send("first", make_character(), "Сделай её старше")

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual((prompt["reply_language"], prompt["text_language"]), ("Russian", "English"))

    async def test_short_answer_keeps_language_of_earlier_message(self) -> None:
        """Answer "ok" in the language of the playwright's earlier, longer message."""
        agent = self.make_agent(CharacterTarget(), turn("Что изменить?"), turn("Хорошо."))

        await agent.send("first", make_character(), "Сделай её старше")
        await agent.send("first", make_character(), "ok")

        self.assertEqual(json.loads(self.client.calls[1]["user_prompt"])["reply_language"], "Russian")


class ReplyLanguageTest(AgentTestCase):
    """Test that the reply comes in the language of the playwright's message."""

    async def test_asks_again_when_the_reply_is_in_another_language(self) -> None:
        """Ask once more, naming the language, when a Russian message got an English reply."""
        agent = self.make_agent(
            CharacterTarget(),
            turn("I suggest the age: «57». Do you agree?"),
            turn("Предлагаю возраст: «57». Согласны?"),
        )

        result = await agent.send("first", make_character(), "Сделай её старше")

        self.assertEqual(result.reply, "Предлагаю возраст: «57». Согласны?")
        self.assertIn("Write `reply` in Russian", self.client.calls[1]["user_prompt"])

    async def test_keeps_quoted_values_in_the_text_language(self) -> None:
        """Accept a Russian reply that quotes English values without asking again."""
        agent = self.make_agent(CharacterTarget(), turn("Предлагаю тон: «Darker and colder.» Согласны?"))

        result = await agent.send("first", make_character(), "Сделай тон мрачнее")

        self.assertEqual(len(self.client.calls), 1)
        self.assertTrue(result.reply.startswith("Предлагаю"))


class LanguageOfTest(TestCase):
    """Test naming the language of a text and recognising a yes."""

    def test_names_language(self) -> None:
        """Recognise Russian, German and English and give up on too few letters."""
        self.assertEqual(language_of("Сделай тон мрачнее"), "Russian")
        self.assertEqual(language_of("Mach den Ton düsterer"), "German")
        self.assertEqual(language_of("Make the tone darker"), "English")
        self.assertIsNone(language_of("ok"))

    def test_recognises_agreement(self) -> None:
        """Take short answers that start with a yes as agreement, and nothing else."""
        for text in ("Yes.", "yes, apply it", "OK, do it", "да", "Давай!", "Sure, go ahead."):
            self.assertTrue(is_agreement(text), text)
        for text in ("No.", "Yesterday the plan changed and I want a new scene at dawn instead", "Make it darker"):
            self.assertFalse(is_agreement(text), text)


class AgreementTest(AgentTestCase):
    """Test what happens when the playwright agrees but the model does not hand over the changes."""

    async def test_applies_proposal_the_playwright_agreed_to(self) -> None:
        """Apply the agent's last proposal when the playwright says yes and the model asks again."""
        proposal = "I suggest age 57 and a cynical personality. Do you agree?"
        agent = self.make_agent(CharacterTarget(), turn(proposal), turn("Do you agree?"), make_edited())

        await agent.send("first", make_character(), "Make her older.")
        result = await agent.send("first", make_character(), "Yes.")

        self.assertEqual(result.reply, "Applying the change.")
        self.assertEqual(result.data.age, 57)
        self.assertEqual(json.loads(self.client.calls[2]["user_prompt"])["changes"], proposal)

    async def test_does_not_apply_without_a_proposal(self) -> None:
        """Answer a yes normally when there is no proposal to agree to."""
        agent = self.make_agent(CharacterTarget(), turn("What should change?"))

        result = await agent.send("first", make_character(), "Yes.")

        self.assertEqual((result.reply, len(self.client.calls)), ("What should change?", 1))

    async def test_says_so_when_the_edit_changed_nothing(self) -> None:
        """Replace "applying" with an honest answer when the edit left the data as it was."""
        unchanged = EditedCharacter(**make_draft().model_dump(exclude={"relationships"}))
        agent = self.make_agent(CharacterTarget(), turn("Применяю.", CHANGES), unchanged)

        result = await agent.send("first", make_character(), "Да, применяй изменения")

        self.assertTrue(result.reply.startswith("Не получилось применить"))
        self.assertEqual(result.data, make_character())


class FileCheckpointerTest(AgentTestCase):
    """Test that conversations written to a file survive a new agent, as after a restart."""

    async def test_keeps_and_forgets_conversation_in_file(self) -> None:
        """Read the history from the file with a new store and remove it when the thread is forgotten."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chats" / "characters.pickle"
            agent = ChatEditAgent(ScriptedSLMClient(turn("What should change?")), CharacterTarget(), create_checkpointer(path))
            await agent.send("first", make_character(), "Change her.")

            restarted = ChatEditAgent(ScriptedSLMClient(), CharacterTarget(), create_checkpointer(path))
            self.assertEqual([m.content for m in await restarted.history("first")], ["Change her.", "What should change?"])

            await restarted.forget("first")
            again = ChatEditAgent(ScriptedSLMClient(), CharacterTarget(), create_checkpointer(path))
            self.assertEqual(await again.history("first"), [])


class EchoTest(AgentTestCase):
    """Test that the agent answers instead of repeating the playwright's message."""

    async def test_asks_again_when_the_reply_repeats_the_message(self) -> None:
        """Ask the model once more with a hint when its reply only repeats the message."""
        agent = self.make_agent(CharacterTarget(), turn("Сделай её старше."), turn("Предлагаю возраст 57. Согласны?"))

        result = await agent.send("first", make_character(), "Сделай её старше")

        self.assertEqual(result.reply, "Предлагаю возраст 57. Согласны?")
        self.assertIn("only repeated the playwright's message", self.client.calls[1]["user_prompt"])


class DirectChangesTest(AgentTestCase):
    """Test applying agreed changes written as the prompt asks without a second model call."""

    async def test_applies_field_lines_without_the_model(self) -> None:
        """Take `field: value` lines straight into the character; the model is called once, for the chat."""
        agent = self.make_agent(CharacterTarget(), turn("Applying.", "age: 57\npersonality: Cynical\nand proud."))

        result = await agent.send("first", make_character(), "Yes.")

        self.assertEqual((result.data.age, result.data.personality, result.data.id), (57, "Cynical\nand proud.", "first"))
        self.assertEqual((result.reply, len(self.client.calls)), ("Applying.", 1))

    async def test_falls_back_to_the_model_for_unknown_fields(self) -> None:
        """Let the model apply changes that name no field of the target."""
        agent = self.make_agent(CharacterTarget(), turn("Applying.", "colour: blue"), make_edited())

        result = await agent.send("first", make_character(), "Yes.")

        self.assertEqual((result.data.age, len(self.client.calls)), (57, 2))

    async def test_outline_and_acts_fields(self) -> None:
        """Apply outline fields and act summaries named by number; an unknown genre falls back to the model."""
        outline = make_outline()
        self.assertEqual(OutlineTarget().parse_changes(outline, "tone: Darker.\ngenre: Tragedy.").tone, "Darker.")
        self.assertEqual(OutlineTarget().parse_changes(outline, "genre: Tragedy.").genre, "tragedy")
        self.assertIsNone(OutlineTarget().parse_changes(outline, "genre: opera"))
        acts = ActsTarget().parse_changes(summaries(), "act 2 summary: The storm wins.")
        self.assertEqual([act.summary for act in acts][1], "The storm wins.")
        self.assertEqual(acts[0], summaries()[0])

    async def test_takes_values_from_an_agreed_proposal_in_prose(self) -> None:
        """Apply the quoted values of a proposal: fields by name, acts by number or word."""
        proposal = "I suggest the time and world: «Today, a city.» and the synopsis: «They part.» Do you agree?"
        revised = OutlineTarget().parse_changes(make_outline(), proposal)
        self.assertEqual((revised.time_and_world, revised.synopsis, revised.tone), ("Today, a city.", "They part.", make_outline().tone))
        acts = ActsTarget().parse_changes(summaries(), "Предлагаю для Act Two: «The storm wins.» Подтверждаете?")
        self.assertEqual(acts[1].summary, "The storm wins.")
        self.assertIsNone(ActsTarget().parse_changes(summaries(), "I suggest making it darker."))
