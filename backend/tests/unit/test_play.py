from unittest import TestCase

from fastapi.testclient import TestClient

from anton.api.dependencies import get_play_service
from anton.application.play_service import PlayService
from anton.domain.models import Cast, CharacterCard, CharacterHistoryEntry, Place, SceneText, StoryBible
from anton.errors import ActNotFoundError, SceneNotFoundError, StoryOrderError
from anton.main import app
from tests.unit.fakes import InMemoryCastRepository, InMemoryStoryRepository
from tests.unit.test_scene_service import KITCHEN, make_characters, make_scene
from tests.unit.test_story_models import make_outline
from tests.unit.test_story_service import make_acts


LANDING = Place(id="landing", name="The landing", description="A single candle.", significance="Secrets.")
TAGLINE_CARD = CharacterCard(role_label="protagonist", tagline=" Keeper of the light ", traits=[], wants="", fears="")
EMPTY_TAGLINE_CARD = CharacterCard(role_label=None, tagline="  ", traits=[], wants="", fears="")


def make_complete_story(status: str = "text_approved") -> StoryBible:
    """Create a Story Bible with three approved acts; Act 1 has two scenes with text, the others have one."""
    acts = make_acts()
    acts[0].scenes = [make_scene(1, status="approved"), make_scene(2, status="approved", place_id="landing", place_notes="Cold")]
    acts[0].scene_texts = [SceneText(scene_number=1, text="ELIAS: One."), SceneText(scene_number=2, text="ELIAS: Two.")]
    acts[1].scenes = [make_scene(1, status="approved")]
    acts[1].scene_texts = [SceneText(scene_number=1, text="ELIAS: Three.")]
    acts[2].scenes = [make_scene(1, status="approved")]
    acts[2].scene_texts = [SceneText(scene_number=1, text="ELIAS: Four.")]
    for act in acts:
        act.status = status
    return StoryBible(outline=make_outline(), acts=acts, acts_approved=True, places=[KITCHEN, LANDING])


def make_cast() -> Cast:
    """Create two characters: Margit has a card tagline, Elias has an empty one."""
    characters = make_characters()
    characters[1].history = [CharacterHistoryEntry(act_number=1, scene_number=1, change="Arrives.")]
    return Cast(characters=characters, cards={"margit": TAGLINE_CARD, "elias": EMPTY_TAGLINE_CARD})


def make_service(story: StoryBible | None = None, cast: Cast | None = None):
    """Create the play service with in-memory repositories."""
    story_repository = InMemoryStoryRepository(story if story is not None else make_complete_story())
    cast_repository = InMemoryCastRepository(cast if cast is not None else make_cast())
    return PlayService(story_repository, cast_repository), story_repository, cast_repository


class PlayCompleteTest(TestCase):
    """Test the flag that says the whole play can be read."""

    def test_play_complete_without_acts_is_false(self) -> None:
        """Return false when there are no acts, even if they are approved."""
        story = StoryBible(outline=make_outline(), acts_approved=True)

        self.assertFalse(story.play_complete)

    def test_play_complete_with_unapproved_text_is_false(self) -> None:
        """Return false while any act text is not approved."""
        story = make_complete_story()
        story.acts[2].status = "scenes_approved"

        self.assertFalse(story.play_complete)

    def test_play_complete_without_approved_acts_is_false(self) -> None:
        """Return false when the acts themselves are not approved."""
        story = make_complete_story()
        story.acts_approved = False

        self.assertFalse(story.play_complete)

    def test_play_complete_with_every_text_approved_is_true(self) -> None:
        """Return true when every act has an approved text."""
        self.assertTrue(make_complete_story().play_complete)

    def test_play_complete_appears_in_story_json(self) -> None:
        """Write the flag into the JSON of the Story Bible like the other flags."""
        self.assertTrue(make_complete_story().model_dump()["play_complete"])


class PlayServiceTest(TestCase):
    """Test reading the whole play and correcting its text."""

    def test_get_play_before_complete_raises_story_order_error(self) -> None:
        """Reject reading the play while an act text is not approved."""
        service, _, _ = make_service(make_complete_story(status="scenes_approved"))

        with self.assertRaises(StoryOrderError) as context:
            service.get_play()

        self.assertIn("Approve the text of every act", str(context.exception))

    def test_get_play_returns_title_page_and_counts(self) -> None:
        """Take the title page from the outline."""
        service, _, _ = make_service()

        play = service.get_play()

        self.assertEqual(play.title, "The Salt House")
        self.assertEqual(play.genre, make_outline().genre)
        self.assertEqual(play.premise, make_outline().premise)
        self.assertEqual(play.time_and_world, make_outline().time_and_world)
        self.assertEqual(play.act_count, 3)

    def test_get_play_describes_cast_by_tagline_or_occupation(self) -> None:
        """Use the trimmed card tagline and fall back to the occupation when it is empty."""
        service, _, _ = make_service()

        play = service.get_play()

        self.assertEqual(
            [(member.character_id, member.name, member.description) for member in play.cast],
            [
                ("margit", "Margit Hale", "Keeper of the light"),
                ("elias", "Elias Hale", "Artistic director of an independent theatre"),
            ],
        )

    def test_get_play_describes_cast_without_card_by_occupation(self) -> None:
        """Use the occupation when the character has no card at all."""
        service, _, _ = make_service(cast=Cast(characters=make_characters(), cards={}))

        play = service.get_play()

        self.assertEqual(play.cast[0].description, "Artistic director of an independent theatre")

    def test_get_play_returns_acts_scenes_places_and_texts_in_order(self) -> None:
        """Put place names, notes and texts into the scenes in story order."""
        service, _, _ = make_service()

        play = service.get_play()

        self.assertEqual([act.number for act in play.acts], [1, 2, 3])
        first_act = [scene.model_dump() for scene in play.acts[0].scenes]
        self.assertEqual(first_act, [
            {"number": 1, "place_name": "The keeper's kitchen", "place_notes": "Dark", "text": "ELIAS: One."},
            {"number": 2, "place_name": "The landing", "place_notes": "Cold", "text": "ELIAS: Two."},
        ])
        self.assertEqual(play.acts[2].scenes[0].text, "ELIAS: Four.")

    def test_edit_scene_text_saves_only_that_scene(self) -> None:
        """Replace one scene text and keep the statuses, the other scenes and the histories."""
        service, story_repository, cast_repository = make_service()
        cast_before = cast_repository.load()
        story_before = story_repository.load()

        play = service.edit_scene_text(1, 2, "ELIAS: Corrected.")

        saved = story_repository.load()
        self.assertEqual(saved.acts[0].scene_texts[1].text, "ELIAS: Corrected.")
        self.assertEqual(saved.acts[0].scene_texts[0], story_before.acts[0].scene_texts[0])
        self.assertEqual(saved.acts[1], story_before.acts[1])
        self.assertEqual([act.status for act in saved.acts], ["text_approved"] * 3)
        self.assertEqual(saved.acts[0].scenes, story_before.acts[0].scenes)
        self.assertEqual(saved.acts[0].text_built_from_scenes, story_before.acts[0].text_built_from_scenes)
        self.assertEqual(cast_repository.load(), cast_before)
        self.assertEqual(cast_repository.saves, 0)
        self.assertEqual(play.acts[0].scenes[1].text, "ELIAS: Corrected.")

    def test_edit_scene_text_before_complete_raises_story_order_error(self) -> None:
        """Reject a correction while an act text is not approved and save nothing."""
        service, story_repository, _ = make_service(make_complete_story(status="scenes_approved"))

        with self.assertRaises(StoryOrderError):
            service.edit_scene_text(1, 1, "ELIAS: Changed.")

        self.assertEqual(story_repository.saves, 0)

    def test_edit_scene_text_unknown_act_raises_not_found(self) -> None:
        """Reject an act that is not in the Story Bible."""
        service, _, _ = make_service()

        with self.assertRaises(ActNotFoundError):
            service.edit_scene_text(9, 1, "ELIAS: Changed.")

    def test_edit_scene_text_unknown_scene_raises_not_found(self) -> None:
        """Reject a scene that is not in the act."""
        service, story_repository, _ = make_service()

        with self.assertRaises(SceneNotFoundError):
            service.edit_scene_text(1, 9, "ELIAS: Changed.")

        self.assertEqual(story_repository.saves, 0)


class PlayRouteTest(TestCase):
    """Test the endpoints of the whole play."""

    def setUp(self) -> None:
        """Replace the play service with one that uses in-memory repositories."""
        self.service, self.story_repository, _ = make_service()
        app.dependency_overrides[get_play_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def use_incomplete_play(self) -> None:
        """Replace the service with one whose last act text is not approved."""
        self.service, self.story_repository, _ = make_service(make_complete_story(status="scenes_approved"))

    def test_get_play_returns_read_model(self) -> None:
        """Return the title page, the cast and the acts."""
        response = self.client.get("/api/story/play")

        body = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(body), {"title", "genre", "premise", "time_and_world", "act_count", "cast", "acts"})
        self.assertEqual(body["cast"][0], {"character_id": "margit", "name": "Margit Hale", "description": "Keeper of the light"})
        self.assertEqual(body["acts"][0]["scenes"][0]["place_name"], "The keeper's kitchen")

    def test_get_play_before_complete_returns_409(self) -> None:
        """Answer 409 with a clear message while the play is not complete."""
        self.use_incomplete_play()

        response = self.client.get("/api/story/play")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["message"], "Approve the text of every act before opening the whole play.")

    def test_put_scene_text_returns_updated_play(self) -> None:
        """Save the text and return the play with it."""
        response = self.client.put("/api/story/play/acts/2/scenes/1/text", json={"text": "ELIAS: Fixed."})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["acts"][1]["scenes"][0]["text"], "ELIAS: Fixed.")
        self.assertEqual(self.story_repository.load().acts[1].scene_texts[0].text, "ELIAS: Fixed.")

    def test_put_scene_text_before_complete_returns_409(self) -> None:
        """Answer 409 while the play is not complete."""
        self.use_incomplete_play()

        response = self.client.put("/api/story/play/acts/1/scenes/1/text", json={"text": "ELIAS: Fixed."})

        self.assertEqual(response.status_code, 409)

    def test_put_scene_text_unknown_act_returns_404(self) -> None:
        """Answer 404 for an unknown act."""
        response = self.client.put("/api/story/play/acts/9/scenes/1/text", json={"text": "ELIAS: Fixed."})

        self.assertEqual(response.status_code, 404)

    def test_put_scene_text_unknown_scene_returns_404(self) -> None:
        """Answer 404 for an unknown scene."""
        response = self.client.put("/api/story/play/acts/1/scenes/9/text", json={"text": "ELIAS: Fixed."})

        self.assertEqual(response.status_code, 404)

    def test_put_scene_text_empty_returns_422(self) -> None:
        """Answer 422 for an empty text."""
        response = self.client.put("/api/story/play/acts/1/scenes/1/text", json={"text": ""})

        self.assertEqual(response.status_code, 422)
