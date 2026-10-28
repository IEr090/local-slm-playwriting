from unittest import TestCase

from pydantic import ValidationError

from anton.domain.models import (
    Act,
    Cast,
    Character,
    Outline,
    Place,
    Scene,
    ScenePlan,
    SceneText,
    StoryBible,
)
from tests.unit.fakes import make_draft


def make_outline() -> Outline:
    """Create a complete play outline."""
    return Outline(
        title="The Salt House",
        premise="Greed costs you the very thing it tries to keep.",
        genre="drama",
        tone="Chamber and cold, with a quiet irony.",
        time_and_world="A North Sea island in the late 1920s.",
        central_conflict="Margit wants to sell the house; Elias wants to keep the light burning.",
        synopsis="The will leaves everything to Agnes. Margit burns the logbook. Agnes gives the house to Elias.",
    )


def make_scene(number: int, what_happens: str = "Voss reads the will.") -> Scene:
    """Create a planned draft scene in the kitchen with two characters."""
    return Scene(
        number=number,
        place_id="kitchen",
        place_notes="Shutters barred against the storm",
        character_ids=["agnes", "elias"],
        what_happens=what_happens,
        planned=True,
    )


def make_act(*scenes: Scene) -> Act:
    """Create the first act with the given scenes."""
    return Act(number=1, summary="The siblings arrive.", dramatic_function="setup", scenes=list(scenes))


def plans(*scenes: Scene) -> list[ScenePlan]:
    """Keep only the plan fields of the scenes."""
    return [ScenePlan(**scene.model_dump(include=set(ScenePlan.model_fields))) for scene in scenes]


class ValidationTest(TestCase):
    """Test that only the allowed values pass validation."""

    def test_rejects_unknown_genre(self) -> None:
        """Allow only comedy, drama, tragedy, tragicomedy and farce."""
        with self.assertRaises(ValidationError):
            Outline(**(make_outline().model_dump() | {"genre": "thriller"}))

    def test_rejects_unknown_dramatic_function(self) -> None:
        """Allow only setup, development, climax and resolution."""
        with self.assertRaises(ValidationError):
            Act(number=1, summary="", dramatic_function="prologue")

    def test_rejects_unknown_act_status(self) -> None:
        """Allow only the four act statuses."""
        with self.assertRaises(ValidationError):
            Act(number=1, summary="", dramatic_function="setup", status="planned")

    def test_rejects_unknown_scene_status(self) -> None:
        """Allow only draft and approved scenes."""
        with self.assertRaises(ValidationError):
            Scene.model_validate(make_scene(1).model_dump() | {"status": "done"})

    def test_starts_act_empty(self) -> None:
        """Start a new act as a draft without scenes and text."""
        act = Act(number=1, summary="The siblings arrive.", dramatic_function="setup")

        self.assertEqual(act.status, "draft")
        self.assertEqual(act.scenes, [])
        self.assertEqual(act.text, "")

    def test_starts_scene_as_unplanned_draft(self) -> None:
        """Start a scene of a proposed structure without a plan and unapproved."""
        scene = Scene(number=1, place_id="kitchen", place_notes="", character_ids=[], what_happens="Elias arrives.")

        self.assertFalse(scene.planned)
        self.assertEqual(scene.status, "draft")

    def test_starts_story_bible_empty(self) -> None:
        """Start the Story Bible without outline, acts and places."""
        story = StoryBible()

        self.assertIsNone(story.outline)
        self.assertEqual((story.acts, story.places, story.acts_approved), ([], [], False))


class SerializationTest(TestCase):
    """Test that the models survive a round trip through JSON."""

    def test_round_trips_story_bible(self) -> None:
        """Read back the same Story Bible that was written, computed fields included."""
        act = make_act(make_scene(1), make_scene(2))
        act.scene_texts = [SceneText(scene_number=1, text="AGNES: Eat.")]
        story = StoryBible(
            user_input="A lighthouse, a will, two siblings.",
            outline=make_outline(),
            acts=[act],
            acts_approved=True,
            places=[Place(id="kitchen", name="The keeper's kitchen", description="A stove.", significance="Home.")],
            acts_built_from_outline=make_outline(),
        )

        restored = StoryBible.model_validate_json(story.model_dump_json())

        self.assertEqual(restored, story)
        self.assertEqual(restored.acts[0].text, act.text)

    def test_writes_computed_fields(self) -> None:
        """Include the act text and the warning flags in the JSON for the UI."""
        data = StoryBible(acts=[make_act()]).model_dump()

        self.assertIn("outline_changed", data)
        self.assertTrue({"text", "summary_changed", "scenes_changed", "outdated_plans"} <= set(data["acts"][0]))


class ActTextTest(TestCase):
    """Test joining the scene texts into the text of the act."""

    def test_joins_scene_texts_with_headings(self) -> None:
        """Put a scene heading before every scene text."""
        act = make_act()
        act.scene_texts = [SceneText(scene_number=1, text="AGNES: Eat."), SceneText(scene_number=2, text="MARGIT: Oak.")]

        self.assertEqual(act.text, "SCENE 1\n\nAGNES: Eat.\n\nSCENE 2\n\nMARGIT: Oak.")


class WarningTest(TestCase):
    """Test the flags that tell the UI that later steps were built from an older version."""

    def test_no_outline_warning_before_acts(self) -> None:
        """Do not warn while no acts were built from the outline."""
        self.assertFalse(StoryBible(outline=make_outline()).outline_changed)

    def test_warns_when_outline_changed_after_acts(self) -> None:
        """Warn when the outline differs from the one the acts were built from."""
        story = StoryBible(outline=make_outline(), acts_built_from_outline=make_outline())
        story.outline.tone = "Black comedy."

        self.assertTrue(story.outline_changed)

    def test_clears_outline_warning_when_change_is_undone(self) -> None:
        """Stop warning when the outline is the same as before again."""
        story = StoryBible(outline=make_outline(), acts_built_from_outline=make_outline())

        self.assertFalse(story.outline_changed)

    def test_warns_when_summary_changed_after_scenes(self) -> None:
        """Warn when the summary differs from the one the scenes were built from."""
        act = make_act(make_scene(1))
        act.scenes_built_from_summary = act.summary

        self.assertFalse(act.summary_changed)
        act.summary = "Margit arrives first."
        self.assertTrue(act.summary_changed)

    def test_warns_when_scenes_changed_after_text(self) -> None:
        """Warn when a scene plan differs from the one the text was written from."""
        act = make_act(make_scene(1), make_scene(2))
        act.text_built_from_scenes = plans(*act.scenes)

        self.assertFalse(act.scenes_changed)
        act.scenes[1].what_happens = "Margit laughs."
        self.assertTrue(act.scenes_changed)

    def test_ignores_approval_when_comparing_scenes(self) -> None:
        """Do not warn when a scene was only approved or reopened."""
        act = make_act(make_scene(1))
        act.text_built_from_scenes = plans(*act.scenes)
        act.scenes[0].status = "approved"

        self.assertFalse(act.scenes_changed)

    def test_warns_when_scene_was_cut_after_text(self) -> None:
        """Warn when a scene was removed after the text was written."""
        act = make_act(make_scene(1), make_scene(2))
        act.text_built_from_scenes = plans(*act.scenes)
        act.scenes.pop()

        self.assertTrue(act.scenes_changed)

    def test_lists_plans_written_before_earlier_scene_changed(self) -> None:
        """Return the scenes whose plan was written from an older version of an earlier scene."""
        first, second, third = make_scene(1), make_scene(2), make_scene(3)
        second.plan_built_from = plans(first)
        third.plan_built_from = plans(first, second)
        act = make_act(first, second, third)

        self.assertEqual(act.outdated_plans, [])
        act.scenes[1].what_happens = "Margit arrives with Voss."
        self.assertEqual(act.outdated_plans, [3])


class CharacterHistoryTest(TestCase):
    """Test that the history extends the character without breaking saved casts."""

    def test_starts_with_empty_history(self) -> None:
        """Give a new character an empty history."""
        self.assertEqual(Character(id="first", **make_draft().model_dump()).history, [])

    def test_reads_cast_saved_without_history(self) -> None:
        """Read a cast.json written before characters had a history."""
        character = Character(id="first", **make_draft().model_dump()).model_dump(exclude={"history"})
        cast = Cast.model_validate({"characters": [character], "cards": {}})

        self.assertEqual(cast.characters[0].history, [])
