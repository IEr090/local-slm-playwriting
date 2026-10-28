from unittest import TestCase

from anton.application.agents.scene_targets import SceneBoard, SceneView
from anton.application.mappers.scene_mapper import add_new_places, to_scene_plans, to_scene_views, to_scenes
from anton.domain.models import PlaceDraft, ScenePlan
from tests.unit.test_scene_service import KITCHEN, make_characters


def view(place: str, *characters: str, number: int = 1) -> SceneView:
    """Create a scene as the model sees it."""
    return SceneView(number=number, place=place, place_notes="", characters=list(characters), what_happens="Margit arrives.")


class ToSceneViewsTest(TestCase):
    """Test replacing ids with names for the model."""

    def test_writes_names_and_numbers(self) -> None:
        """Show the place name and the full names of the characters, numbered in order."""
        plans = [ScenePlan(place_id="kitchen", place_notes="Dark", character_ids=["margit", "elias"], what_happens="Margit arrives.")]

        views = to_scene_views(plans, [KITCHEN], make_characters())

        self.assertEqual(views, [SceneView(
            number=1, place="The keeper's kitchen", place_notes="Dark", characters=["Margit Hale", "Elias Hale"],
            what_happens="Margit arrives.",
        )])

    def test_leaves_unknown_ids_out(self) -> None:
        """Show an empty place and skip characters that are not in the cast."""
        plans = [ScenePlan(place_id="", place_notes="", character_ids=["ghost"], what_happens="Nobody.")]

        views = to_scene_views(plans, [KITCHEN], make_characters())

        self.assertEqual((views[0].place, views[0].characters), ("", []))


class AddNewPlacesTest(TestCase):
    """Test adding the places the model proposed or named."""

    def test_adds_proposed_place_with_description(self) -> None:
        """Add a proposed place with its description and a new id."""
        board = SceneBoard(
            scenes=[view("The lamp room")],
            new_places=[PlaceDraft(name="The lamp room", description="A lens.", significance="The light.")],
        )

        places = add_new_places(board, [KITCHEN])

        self.assertEqual(places[0], KITCHEN)
        self.assertEqual(places[1].model_dump(exclude={"id"}), {"name": "The lamp room", "description": "A lens.", "significance": "The light."})
        self.assertTrue(places[1].id)

    def test_adds_named_place_without_description(self) -> None:
        """Add a place a scene names even if the model did not describe it."""
        places = add_new_places(SceneBoard(scenes=[view("The landing")]), [KITCHEN])

        self.assertEqual((places[1].name, places[1].description), ("The landing", ""))

    def test_does_not_duplicate_places(self) -> None:
        """Match places regardless of case and add every new place once."""
        board = SceneBoard(
            scenes=[view("the keeper's KITCHEN"), view("The landing", number=2), view("the landing", number=3)],
            new_places=[PlaceDraft(name="The landing", description="Dark.", significance="")],
        )

        places = add_new_places(board, [KITCHEN])

        self.assertEqual([place.name for place in places], ["The keeper's kitchen", "The landing"])

    def test_ignores_empty_place(self) -> None:
        """Add nothing for a scene without a place."""
        self.assertEqual(add_new_places(SceneBoard(scenes=[view("")]), [KITCHEN]), [KITCHEN])


class ToScenePlansTest(TestCase):
    """Test replacing the names the model wrote with ids."""

    def test_finds_ids_by_full_or_first_name(self) -> None:
        """Match characters by full name or by a unique first name, and places by name."""
        plans = to_scene_plans([view("The keeper's kitchen", "Margit Hale", "elias")], [KITCHEN], make_characters())

        self.assertEqual(plans, [ScenePlan(place_id="kitchen", place_notes="", character_ids=["margit", "elias"], what_happens="Margit arrives.")])

    def test_drops_unknown_names(self) -> None:
        """Leave out characters the cast does not have and repeated ones, and keep an unknown place empty."""
        plans = to_scene_plans([view("Nowhere", "Margit", "Voss", "Margit Hale")], [KITCHEN], make_characters())

        self.assertEqual((plans[0].place_id, plans[0].character_ids), ("", ["margit"]))

    def test_numbers_new_scenes(self) -> None:
        """Number scenes from one as unplanned drafts."""
        plan = ScenePlan(place_id="kitchen", place_notes="", character_ids=[], what_happens="Rain.")

        scenes = to_scenes([plan, plan])

        self.assertEqual([(scene.number, scene.planned, scene.status) for scene in scenes], [(1, False, "draft"), (2, False, "draft")])

