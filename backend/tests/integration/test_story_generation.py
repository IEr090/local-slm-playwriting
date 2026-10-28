from unittest import IsolatedAsyncioTestCase

from anton.application.agents.acts_target import ActsTarget
from anton.application.agents.chat_edit_agent import ChatEditAgent, create_checkpointer
from anton.application.agents.outline_target import OutlineTarget
from anton.application.agents.scene_targets import ScenesTarget, StructureTarget
from anton.application.agents.text_target import TextTarget
from anton.application.character_service import CharacterService
from anton.application.scene_planner import ScenePlanner
from anton.application.scene_service import SceneService
from anton.application.scene_writer import SceneWriter
from anton.application.story_service import StoryService
from anton.application.text_service import TextService
from anton.domain.models import Act, Cast, StoryBible
from tests.integration import create_test_client
from tests.integration.test_character_generation import USER_PROMPT
from tests.unit.fakes import InMemoryCastRepository, InMemoryStoryRepository


class StoryGenerationTest(IsolatedAsyncioTestCase):
    """Test the whole Story Bible flow of the first act against a local Ollama model."""

    async def asyncSetUp(self) -> None:
        """Create every service with one model client and shared in-memory repositories, as the API does."""
        client = create_test_client()
        self.cast_repository = InMemoryCastRepository()
        self.story_repository = InMemoryStoryRepository()
        act_checkpointer = create_checkpointer()

        self.characters = CharacterService(client, self.cast_repository)
        self.story = StoryService(
            self.story_repository,
            self.cast_repository,
            ChatEditAgent(client, OutlineTarget(), create_checkpointer()),
            ChatEditAgent(client, ActsTarget(), create_checkpointer()),
        )
        self.scenes = SceneService(
            self.story_repository,
            self.cast_repository,
            ChatEditAgent(client, StructureTarget(), act_checkpointer),
            ChatEditAgent(client, ScenesTarget(), act_checkpointer),
            ScenePlanner(client),
        )
        self.text = TextService(
            self.story_repository, self.cast_repository, ChatEditAgent(client, TextTarget(), act_checkpointer), SceneWriter(client),
        )

    async def test_builds_first_act(self) -> None:
        """Go from the user's idea to the approved text of Act One and the characters' histories."""
        cast = await self.characters.generate_cast(USER_PROMPT)
        await self.story.start_play(USER_PROMPT)

        story = await self.story.generate_outline()
        self.assert_outline(story)

        reply = await self.story.revise_outline(story.outline, "Make the tone a little darker.")
        self.assertTrue(reply.reply.strip(), "The outline agent gave an empty answer")

        story = await self.story.generate_acts()
        self.assert_acts(story)
        self.story.approve_acts()

        story = await self.scenes.generate_structure(1)
        self.assert_structure(story.acts[0], story, cast)
        self.scenes.approve_structure(1)

        for scene in story.acts[0].scenes:
            story = await self.scenes.plan_scene(1, scene.number)
            planned = story.acts[0].scenes[scene.number - 1]
            self.assertTrue(planned.place_notes.strip() and planned.what_happens.strip(), f"Scene {scene.number} has an empty plan")
            story = self.scenes.approve_scene(1, scene.number)
        self.assertEqual(story.acts[0].status, "scenes_approved")

        story = await self.text.generate_text(1)
        self.assert_text(story.acts[0])

        story = await self.text.approve_text(1)
        self.assertEqual(story.acts[0].status, "text_approved")
        self.assert_histories(self.cast_repository.load(), story.acts[0])

    def assert_outline(self, story: StoryBible) -> None:
        """Check that every field of the outline is filled and the user's characters appear in it."""
        empty = [field for field, value in story.outline.model_dump().items() if not str(value).strip()]
        self.assertFalse(empty, f"The outline has empty fields: {empty}")

        text = story.outline.model_dump_json().casefold()
        self.assertTrue(
            any(name in text for name in ("elena", "mark", "anna")),
            f"The outline names none of the characters: {story.outline.central_conflict}",
        )

    def assert_acts(self, story: StoryBible) -> None:
        """Check that the acts are numbered in order, have summaries and start with the setup."""
        summaries = [(act.number, act.dramatic_function, act.summary) for act in story.acts]

        self.assertGreaterEqual(len(story.acts), 2, f"Generated acts: {summaries}")
        self.assertEqual([act.number for act in story.acts], list(range(1, len(story.acts) + 1)))
        self.assertTrue(all(act.summary.strip() for act in story.acts), f"Generated acts: {summaries}")
        self.assertEqual(story.acts[0].dramatic_function, "setup", f"Generated acts: {summaries}")
        self.assertFalse(story.outline_changed)

    def assert_structure(self, act: Act, story: StoryBible, cast: Cast) -> None:
        """Check that every scene has a known place, characters of the cast and events."""
        place_ids = {place.id for place in story.places}
        character_ids = {character.id for character in cast.characters}
        scenes = [(scene.place_id, scene.character_ids, scene.what_happens) for scene in act.scenes]

        self.assertTrue(act.scenes, "The act has no scenes")
        for scene in act.scenes:
            self.assertIn(scene.place_id, place_ids, f"Scene {scene.number} has no known place: {scenes}")
            self.assertTrue(scene.character_ids, f"Scene {scene.number} has nobody on stage: {scenes}")
            self.assertLessEqual(set(scene.character_ids), character_ids)
            self.assertTrue(scene.what_happens.strip(), f"Scene {scene.number} has no events")

    def assert_text(self, act: Act) -> None:
        """Check that every scene has a text with speeches of characters on stage."""
        self.assertEqual([item.scene_number for item in act.scene_texts], [scene.number for scene in act.scenes])
        for scene_text in act.scene_texts:
            self.assertIn(":", scene_text.text, f"Scene {scene_text.scene_number} has no speeches: {scene_text.text[:200]}")
        self.assertTrue(act.text.startswith("SCENE 1"))
        self.assertFalse(act.scenes_changed)

    def assert_histories(self, cast: Cast, act: Act) -> None:
        """Check that the approved act left history entries, each linked to a scene of the act."""
        entries = [entry for character in cast.characters for entry in character.history]
        scene_numbers = {scene.number for scene in act.scenes}

        self.assertTrue(entries, "No character history was recorded for the act")
        for entry in entries:
            self.assertEqual(entry.act_number, act.number)
            self.assertIn(entry.scene_number, scene_numbers)
            self.assertTrue(entry.change.strip())
