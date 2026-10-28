from unittest import IsolatedAsyncioTestCase, TestCase

from anton.application.agents.scene_targets import SceneBoard, SceneView, ScenesTarget, StructureTarget
from anton.application.llm_schemas.scene_generation import EditedScene, EditedScenes, GeneratedPlace
from anton.application.scene_planner import ScenePlanner
from anton.domain.models import PlaceDraft
from tests.unit.fakes import FakeSLMClient
from tests.unit.test_scene_service import PLAN, STRUCTURE


def make_board() -> SceneBoard:
    """Create two planned scenes as the model sees them."""
    return SceneBoard(scenes=[
        SceneView(number=1, place="The keeper's kitchen", place_notes="Dark", characters=["Elias Hale"], what_happens="Elias arrives."),
        SceneView(number=2, place="The lamp room", place_notes="Wind", characters=["Margit Hale"], what_happens="Voss reads the will."),
    ])


class StructureTargetTest(TestCase):
    """Test how the act agent writes, sees and changes the structure."""

    def test_numbers_generated_scenes_and_keeps_new_places(self) -> None:
        """Number the scenes from one, trim the text and keep the proposed places."""
        board = StructureTarget().from_generated(STRUCTURE)

        self.assertEqual([(scene.number, scene.place, scene.what_happens) for scene in board.scenes], [
            (1, "The keeper's kitchen", "Elias arrives."), (2, "The lamp room", "Voss reads the will."),
        ])
        self.assertEqual(board.new_places, [PlaceDraft(name="The lamp room", description="A great lens.", significance="The light.")])

    def test_hides_place_notes_of_structure(self) -> None:
        """Show the model place, characters and events of every scene, without the notes of a later plan."""
        self.assertEqual(StructureTarget().view(make_board())[0], {
            "number": 1, "place": "The keeper's kitchen", "characters": ["Elias Hale"], "what_happens": "Elias arrives.",
        })

    def test_builds_input_from_sections(self) -> None:
        """Put the outline, the act, the earlier acts, the places and the cast under their headings."""
        source = {"outline": "O", "act": "A", "earlier_acts": "E", "places": "P", "cast": "C"}

        self.assertEqual(
            StructureTarget().generate_input(source),
            "# OUTLINE\n\nO\n\n# ACT\n\nA\n\n# EARLIER ACTS\n\nE\n\n# PLACES\n\nP\n\n# CAST\n\nC",
        )


class ScenesTargetTest(TestCase):
    """Test how the act agent sees and changes the scene plans."""

    def test_replaces_only_edited_scene(self) -> None:
        """Change the scene the model edited, keep the others and take the proposed places."""
        edited = EditedScenes(
            new_places=[GeneratedPlace(name="The landing", description="Dark.", significance="")],
            scenes=[EditedScene(number=2, place="The landing", place_notes="Candle", characters=["Margit Hale"], what_happens=" Later. ")],
        )

        board = ScenesTarget().apply(make_board(), edited)

        self.assertEqual(board.scenes[0], make_board().scenes[0])
        self.assertEqual((board.scenes[1].place, board.scenes[1].what_happens), ("The landing", "Later."))
        self.assertEqual([place.name for place in board.new_places], ["The landing"])

    def test_ignores_scene_that_does_not_exist(self) -> None:
        """Keep the scenes unchanged when the model edited a scene number the act does not have."""
        edited = EditedScenes(new_places=[], scenes=[EditedScene(number=9, place="", place_notes="", characters=[], what_happens="")])

        self.assertEqual(ScenesTarget().apply(make_board(), edited).scenes, make_board().scenes)


class ScenePlannerTest(IsolatedAsyncioTestCase):
    """Test writing the plan of one scene without a conversation."""

    async def test_trims_plan_and_lets_model_think(self) -> None:
        """Return the plan with trimmed text after a call that may think."""
        client = FakeSLMClient(PLAN)

        plan = await ScenePlanner(client).plan("Act.", [], make_board().scenes[0], {"name": "Kitchen"}, [])

        self.assertEqual((plan.place_notes, plan.what_happens), ("Shutters barred", "Late afternoon. Elias arrives soaked."))
        self.assertTrue(client.calls[0]["think"])
        self.assertIn('"act_summary": "Act."', client.calls[0]["user_prompt"])
