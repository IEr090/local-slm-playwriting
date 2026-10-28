import json
from unittest import IsolatedAsyncioTestCase, TestCase

from anton.application.agents.chat_edit_agent import ChatEditAgent, create_checkpointer
from anton.application.agents.text_target import TextTarget
from anton.application.llm_schemas.chat_turn import ChatTurn
from anton.application.llm_schemas.text_generation import (
    EditedSceneText,
    EditedSceneTexts,
    GeneratedHistory,
    GeneratedHistoryEntry,
    GeneratedLine,
    GeneratedSceneText,
)
from anton.application.mappers.text_mapper import ending, format_lines, to_history_entries
from anton.application.scene_writer import SceneWriter
from anton.application.text_service import TextService
from anton.domain.models import Cast, CharacterHistoryEntry, SceneText
from anton.errors import SceneNotFoundError, StoryOrderError
from tests.unit.fakes import FakeSLMClient, InMemoryCastRepository, InMemoryStoryRepository
from tests.unit.test_scene_service import make_characters, make_scene, make_story


SCENE_TEXT = GeneratedSceneText(lines=[
    GeneratedLine(character="", parenthetical="", text="Late afternoon. The shutters are barred."),
    GeneratedLine(character="Elias", parenthetical="looking at the table", text="Three places."),
])
WRITTEN = "(Late afternoon. The shutters are barred.)\n\nELIAS (looking at the table): Three places."
HISTORY = GeneratedHistory(entries=[GeneratedHistoryEntry(character="Elias Hale", change=" Learns that Margit wrote to Agnes. ")])


def make_text_story(status: str = "scenes_approved", texts: bool = True):
    """Create a Story Bible whose first act has two approved scenes and, optionally, their text."""
    story = make_story(make_scene(1, status="approved"), make_scene(2, status="approved"), status=status)
    if texts:
        story.acts[0].scene_texts = [SceneText(scene_number=1, text="ELIAS: One."), SceneText(scene_number=2, text="ELIAS: Two.")]
    return story


def make_service(*responses, story=None, cast: Cast | None = None):
    """Create the text service with in-memory repositories and a fake model client."""
    client = FakeSLMClient(*responses)
    repository = InMemoryStoryRepository(story if story is not None else make_text_story())
    cast_repository = InMemoryCastRepository(cast or Cast(characters=make_characters(), cards={}))
    service = TextService(
        repository, cast_repository, ChatEditAgent(client, TextTarget(), create_checkpointer()), SceneWriter(client),
    )
    return service, client, repository, cast_repository


class FormatTest(TestCase):
    """Test writing the generated lines in play format."""

    def test_writes_speeches_and_directions(self) -> None:
        """Write speeches as NAME (note): text and stage directions in parentheses."""
        self.assertEqual(format_lines(SCENE_TEXT.lines), WRITTEN)

    def test_skips_empty_lines_and_double_parentheses(self) -> None:
        """Leave out empty lines and do not wrap a direction in parentheses twice."""
        lines = [
            GeneratedLine(character="", parenthetical="", text="(Darkness.)"),
            GeneratedLine(character="Agnes", parenthetical="", text="  "),
            GeneratedLine(character="agnes", parenthetical="(softly)", text="Eat."),
        ]

        self.assertEqual(format_lines(lines), "(Darkness.)\n\nAGNES (softly): Eat.")

    def test_ending_keeps_last_blocks(self) -> None:
        """Return the last speeches and directions of a text."""
        self.assertEqual(ending("A\n\nB\n\nC", 2), "B\n\nC")

    def test_links_history_to_act_scene_and_id(self) -> None:
        """Give every change its act, its scene and the id of its character; drop unknown names."""
        generated = GeneratedHistory(entries=HISTORY.entries + [GeneratedHistoryEntry(character="Voss", change="Leaves.")])

        entries = to_history_entries(generated, 1, 2, make_characters())

        self.assertEqual(entries, {"elias": [CharacterHistoryEntry(act_number=1, scene_number=2, change="Learns that Margit wrote to Agnes.")]})


class TextTargetTest(TestCase):
    """Test how the act agent sees and changes the text."""

    def test_replaces_only_edited_scene_text(self) -> None:
        """Rewrite the scene the model edited in play format and keep the others."""
        texts = [SceneText(scene_number=1, text="ELIAS: One."), SceneText(scene_number=2, text="ELIAS: Two.")]
        edited = EditedSceneTexts([EditedSceneText(scene_number=2, lines=SCENE_TEXT.lines)])

        result = TextTarget().apply(texts, edited)

        self.assertEqual(result, [texts[0], SceneText(scene_number=2, text=WRITTEN)])

    def test_keeps_text_when_edit_is_empty(self) -> None:
        """Keep a scene text when the model returned no lines for it."""
        texts = [SceneText(scene_number=1, text="ELIAS: One.")]

        self.assertEqual(TextTarget().apply(texts, EditedSceneTexts([EditedSceneText(scene_number=1, lines=[])])), texts)


class GenerateTextTest(IsolatedAsyncioTestCase):
    """Test writing the text of an act scene by scene."""

    async def test_writes_every_scene_and_remembers_scenes(self) -> None:
        """Store one text per scene in play format and the scenes it was written from."""
        service, client, repository, _ = make_service(SCENE_TEXT, story=make_text_story(texts=False))

        story = await service.generate_text(1)

        act = story.acts[0]
        self.assertEqual(act.scene_texts, [SceneText(scene_number=1, text=WRITTEN), SceneText(scene_number=2, text=WRITTEN)])
        self.assertEqual(act.text, f"SCENE 1\n\n{WRITTEN}\n\nSCENE 2\n\n{WRITTEN}")
        self.assertFalse(act.scenes_changed)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(repository.load(), story)

    async def test_sends_plan_place_characters_and_previous_ending(self) -> None:
        """Give the model the plan, the place, the characters and the end of the scene before."""
        service, client, *_ = make_service(SCENE_TEXT, story=make_text_story(texts=False))

        await service.generate_text(1)

        first, second = (json.loads(call["user_prompt"]) for call in client.calls)
        self.assertEqual(first["previous_scene_ending"], "")
        self.assertEqual(second["previous_scene_ending"], WRITTEN)
        self.assertEqual(second["scene"]["number"], 2)
        self.assertEqual(second["place"]["name"], "The keeper's kitchen")
        self.assertEqual([character["name"] for character in second["characters"]], ["Elias"])
        self.assertEqual(set(first["play"]), {"title", "genre", "tone", "time_and_world"})
        self.assertTrue(client.calls[0]["think"])

    async def test_rejects_before_all_scenes_are_approved(self) -> None:
        """Reject writing the text while a scene is still a draft."""
        service, client, *_ = make_service(SCENE_TEXT, story=make_text_story(status="structure_approved", texts=False))

        with self.assertRaises(StoryOrderError) as raised:
            await service.generate_text(1)
        self.assertIn("Approve every scene", str(raised.exception))
        self.assertEqual(client.calls, [])

    async def test_warns_when_scene_changes_after_text(self) -> None:
        """Set the warning flag when a scene plan changes after the text was written."""
        service, *_ = make_service(SCENE_TEXT, story=make_text_story(texts=False))
        story = await service.generate_text(1)

        story.acts[0].scenes[0].what_happens = "Elias never arrives."

        self.assertTrue(story.acts[0].scenes_changed)


class EditAndReviseTextTest(IsolatedAsyncioTestCase):
    """Test saving and revising the text before it is approved."""

    async def test_saves_texts_from_form(self) -> None:
        """Replace the scene texts with the ones the user sent."""
        service, _, repository, _ = make_service()
        texts = [SceneText(scene_number=1, text="ELIAS: Changed."), SceneText(scene_number=2, text="ELIAS: Two.")]

        story = service.edit_text(1, texts)

        self.assertEqual(story.acts[0].scene_texts, texts)
        self.assertEqual(repository.load().acts[0].scene_texts, texts)

    async def test_rejects_text_of_unknown_scene(self) -> None:
        """Reject a text for a scene the act's text does not have."""
        service, *_ = make_service()

        with self.assertRaises(SceneNotFoundError):
            service.edit_text(1, [SceneText(scene_number=9, text="Nothing.")])

    async def test_revises_named_scene_without_saving(self) -> None:
        """Answer with the edited scene text and leave the saved text unchanged."""
        edited = EditedSceneTexts([EditedSceneText(scene_number=2, lines=SCENE_TEXT.lines)])
        story = make_text_story()
        service, client, repository, _ = make_service(ChatTurn(reply="Applying.", apply_changes="scene 2 ..."), edited, story=story)

        result = await service.revise_text(1, story.acts[0].scene_texts, "Yes.")

        self.assertEqual(result.reply, "Applying.")
        self.assertEqual(result.scene_texts[1].text, WRITTEN)
        self.assertEqual(repository.load(), story)
        self.assertEqual(json.loads(client.calls[0]["user_prompt"])["act_summary"], "The siblings arrive.")

    async def test_rejects_revision_before_text(self) -> None:
        """Reject chatting about a text that has not been written yet."""
        service, *_ = make_service(ChatTurn(reply="?", apply_changes=None), story=make_text_story(texts=False))

        with self.assertRaises(StoryOrderError):
            await service.revise_text(1, [SceneText(scene_number=1, text="ELIAS: One.")], "Sharper.")


class ApproveTextTest(IsolatedAsyncioTestCase):
    """Test approving the text and recording the character histories."""

    async def test_approves_text_and_appends_history(self) -> None:
        """Mark the text as approved and give every changed character an entry per scene."""
        service, client, repository, cast_repository = make_service(HISTORY)

        story = await service.approve_text(1)

        self.assertEqual(story.acts[0].status, "text_approved")
        self.assertEqual(repository.load().acts[0].status, "text_approved")
        elias = cast_repository.load().characters[1]
        self.assertEqual([(entry.act_number, entry.scene_number) for entry in elias.history], [(1, 1), (1, 2)])
        self.assertEqual(cast_repository.load().characters[0].history, [])
        self.assertEqual(json.loads(client.calls[0]["user_prompt"]), {"scene_text": "ELIAS: One.", "characters": ["Elias Hale"]})

    async def test_replaces_old_entries_of_the_act(self) -> None:
        """Remove the entries of an act written before and keep the entries of other acts."""
        characters = make_characters()
        characters[1].history = [
            CharacterHistoryEntry(act_number=1, scene_number=1, change="Old version."),
            CharacterHistoryEntry(act_number=2, scene_number=1, change="Another act."),
        ]
        service, _, _, cast_repository = make_service(HISTORY, cast=Cast(characters=characters, cards={}))

        await service.approve_text(1)

        changes = [entry.change for entry in cast_repository.load().characters[1].history]
        self.assertEqual(changes, ["Learns that Margit wrote to Agnes.", "Learns that Margit wrote to Agnes.", "Another act."])

    async def test_rejects_approval_before_text(self) -> None:
        """Reject approving a text that has not been written yet."""
        service, *_ = make_service(HISTORY, story=make_text_story(texts=False))

        with self.assertRaises(StoryOrderError):
            await service.approve_text(1)

    async def test_rejects_second_approval(self) -> None:
        """Reject approving the text again; change its scenes to write it again."""
        service, *_ = make_service(HISTORY, story=make_text_story(status="text_approved"))

        with self.assertRaises(StoryOrderError) as raised:
            await service.approve_text(1)
        self.assertIn("already approved", str(raised.exception))
