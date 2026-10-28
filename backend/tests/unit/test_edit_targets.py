from unittest import TestCase

from anton.application.agents.acts_target import ActsTarget
from anton.application.agents.character_target import CharacterTarget
from anton.application.agents.outline_target import OutlineTarget
from anton.application.llm_schemas.act_generation import EditedAct, EditedActs, GeneratedActs
from anton.application.llm_schemas.outline_generation import GeneratedOutline
from anton.domain.models import Relationship
from anton.errors import SLMResponseError
from tests.unit.test_chat_edit_agent import HISTORY, make_character, make_edited
from tests.unit.test_story_models import make_outline
from tests.unit.test_story_service import GENERATED_ACTS, summaries


class CharacterTargetTest(TestCase):
    """Test how the edit agent sees and changes a character."""

    def test_hides_id_relationships_and_history(self) -> None:
        """Show the model only the profile it may change."""
        view = CharacterTarget().view(make_character())

        self.assertEqual(view, make_character().model_dump(exclude={"id", "relationships", "history"}))

    def test_takes_profile_from_model(self) -> None:
        """Replace the profile fields with the ones the model returned."""
        result = CharacterTarget().apply(make_character(), make_edited())

        self.assertEqual(result.model_dump(exclude={"id", "relationships", "history"}), make_edited().model_dump())

    def test_keeps_id_relationships_and_history(self) -> None:
        """Keep what the model never saw from the original character."""
        result = CharacterTarget().apply(make_character(), make_edited())

        self.assertEqual(result.id, "first")
        self.assertEqual(result.relationships, [Relationship(character_id="second", description="Rivals.")])
        self.assertEqual(result.history, HISTORY)


class OutlineTargetTest(TestCase):
    """Test how the outline agent writes, sees and changes the outline."""

    def test_builds_input_from_idea_and_cast(self) -> None:
        """Put the idea and the cast under the headings of the generation prompt."""
        self.assertEqual(OutlineTarget().generate_input({"idea": "An idea.", "cast": "[]"}), "# IDEA\n\nAn idea.\n\n# CAST\n\n[]")

    def test_takes_whole_outline_with_trimmed_text(self) -> None:
        """Take every field from the model and trim stray spaces."""
        edited = GeneratedOutline(**(make_outline().model_dump() | {"tone": "  Black comedy.  "}))

        result = OutlineTarget().apply(make_outline(), edited)

        self.assertEqual(result, make_outline().model_copy(update={"tone": "Black comedy."}))


class ActsTargetTest(TestCase):
    """Test how the acts agent writes, sees and changes the acts."""

    def test_builds_input_from_outline_and_cast(self) -> None:
        """Put the outline and the cast under the headings of the generation prompt."""
        self.assertEqual(ActsTarget().generate_input({"outline": "{}", "cast": "[]"}), "# OUTLINE\n\n{}\n\n# CAST\n\n[]")

    def test_numbers_generated_acts(self) -> None:
        """Number the acts from one in the model's order, with trimmed text."""
        self.assertEqual(ActsTarget().from_generated(GENERATED_ACTS), summaries())

    def test_raises_for_no_acts(self) -> None:
        """Report an unusable answer when the model returned no acts."""
        with self.assertRaises(SLMResponseError):
            ActsTarget().from_generated(GeneratedActs([]))

    def test_replaces_only_edited_act(self) -> None:
        """Change the act the model edited and keep the others."""
        edited = EditedActs([EditedAct(number=2, summary=" Margit hides the logbook. ", dramatic_function="development")])

        result = ActsTarget().apply(summaries(), edited)

        self.assertEqual((result[1].summary, result[1].dramatic_function), ("Margit hides the logbook.", "development"))
        self.assertEqual([result[0], result[2]], [summaries()[0], summaries()[2]])

    def test_ignores_act_that_does_not_exist(self) -> None:
        """Keep the acts unchanged when the model edited an act number the play does not have."""
        edited = EditedActs([EditedAct(number=9, summary="Storm.", dramatic_function="climax")])

        self.assertEqual(ActsTarget().apply(summaries(), edited), summaries())
