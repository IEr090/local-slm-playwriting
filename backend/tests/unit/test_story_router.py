from unittest import TestCase

from fastapi.testclient import TestClient

from anton.api.dependencies import get_character_service, get_story_service
from anton.application.character_service import CharacterService
from anton.application.story_service import StoryService
from anton.domain.models import StoryBible
from anton.main import app
from anton.application.outline_agent import OutlineAgent, create_outline_checkpointer
from tests.unit.fakes import CARD, FakeSLMClient, InMemoryCastRepository, InMemoryStoryRepository, make_generated_cast
from tests.unit.test_story_service import GENERATED_ACTS, GENERATED_OUTLINE, PROPOSAL
from tests.unit.test_story_models import make_outline


class StoryRouteTest(TestCase):
    """Test the outline endpoints from starting a play to revising the outline in the chat."""

    def setUp(self) -> None:
        """Replace both services with ones that share a fake model client and in-memory repositories."""
        client = FakeSLMClient(make_generated_cast(), CARD, GENERATED_OUTLINE, PROPOSAL, GENERATED_ACTS)
        cast_repository = InMemoryCastRepository()
        self.story_repository = InMemoryStoryRepository()
        agent = OutlineAgent(client, create_outline_checkpointer())
        app.dependency_overrides[get_character_service] = lambda: CharacterService(client, cast_repository)
        app.dependency_overrides[get_story_service] = lambda: StoryService(client, self.story_repository, cast_repository, agent)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Remove the dependency overrides."""
        app.dependency_overrides.clear()

    def start_play(self) -> None:
        """Generate the cast, which also starts the Story Bible."""
        self.client.post("/api/characters/generate", json={"premise": "A lighthouse and a will."})

    def test_get_before_play_returns_404(self) -> None:
        """Answer 404 before the cast is generated."""
        response = self.client.get("/api/story")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(set(response.json()), {"message", "detail"})

    def test_cast_generation_starts_play(self) -> None:
        """Save the cast premise as the user's input of a new Story Bible."""
        self.start_play()

        self.assertEqual(self.story_repository.load(), StoryBible(user_input="A lighthouse and a will."))

    def test_generates_outline(self) -> None:
        """Return the Story Bible with the generated outline and its warning flag."""
        self.start_play()

        response = self.client.post("/api/story/outline/generate")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["outline"]["title"], "The Salt House")
        self.assertFalse(response.json()["outline_changed"])

    def test_second_generation_returns_409(self) -> None:
        """Reject generating the outline twice with a clear message."""
        self.start_play()
        self.client.post("/api/story/outline/generate")

        response = self.client.post("/api/story/outline/generate")

        self.assertEqual(response.status_code, 409)
        self.assertIn("outline already exists", response.json()["message"])

    def test_edit_before_outline_returns_409(self) -> None:
        """Reject editing the outline before it is generated."""
        self.start_play()

        response = self.client.put("/api/story/outline", json=make_outline().model_dump())

        self.assertEqual(response.status_code, 409)

    def test_edits_outline(self) -> None:
        """Save the edited outline so that the next read returns it."""
        self.start_play()
        self.client.post("/api/story/outline/generate")
        payload = make_outline().model_dump() | {"title": "The Lamp"}

        response = self.client.put("/api/story/outline", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/story").json()["outline"]["title"], "The Lamp")

    def test_edit_with_unknown_genre_returns_422(self) -> None:
        """Validate the genre against the fixed list."""
        self.start_play()
        self.client.post("/api/story/outline/generate")

        response = self.client.put("/api/story/outline", json=make_outline().model_dump() | {"genre": "thriller"})

        self.assertEqual(response.status_code, 422)

    def test_revises_outline_with_agent(self) -> None:
        """Return the agent's reply and the outline from the form, and keep both messages in the history."""
        self.start_play()
        self.client.post("/api/story/outline/generate")
        form = make_outline().model_dump() | {"title": "The Lamp"}

        response = self.client.post("/api/story/outline/revise", json={"message": "Make it darker.", "outline": form})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"reply": PROPOSAL.reply, "outline": form})
        history = self.client.get("/api/story/outline/revise").json()
        self.assertEqual([message["role"] for message in history], ["user", "assistant"])
        self.assertEqual(self.client.get("/api/story").json()["outline"]["title"], "The Salt House")

    def test_empty_revise_message_returns_422(self) -> None:
        """Reject an empty chat message."""
        self.start_play()

        response = self.client.post("/api/story/outline/revise", json={"message": "", "outline": make_outline().model_dump()})

        self.assertEqual(response.status_code, 422)

    def generate_acts(self) -> None:
        """Start a play and generate its outline and acts."""
        self.start_play()
        self.client.post("/api/story/outline/generate")
        self.client.post("/api/story/acts/generate")

    def test_generates_acts(self) -> None:
        """Return the Story Bible with numbered draft acts."""
        self.start_play()
        self.client.post("/api/story/outline/generate")

        response = self.client.post("/api/story/acts/generate")

        self.assertEqual(response.status_code, 200)
        acts = response.json()["acts"]
        self.assertEqual([(act["number"], act["status"]) for act in acts], [(1, "draft"), (2, "draft"), (3, "draft")])

    def test_acts_before_outline_return_409(self) -> None:
        """Reject generating acts before the outline exists."""
        self.start_play()

        response = self.client.post("/api/story/acts/generate")

        self.assertEqual(response.status_code, 409)

    def test_outline_edit_after_acts_sets_warning(self) -> None:
        """Expose the warning flag when the outline changes after the acts were built."""
        self.generate_acts()

        response = self.client.put("/api/story/outline", json=make_outline().model_dump() | {"title": "The Lamp"})

        self.assertTrue(response.json()["outline_changed"])

    def test_edits_act(self) -> None:
        """Save the edited summary and dramatic function of an act."""
        self.generate_acts()

        response = self.client.put("/api/story/acts/2", json={"summary": "Margit hides the logbook.", "dramatic_function": "development"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["acts"][1]["dramatic_function"], "development")

    def test_edit_unknown_act_returns_404(self) -> None:
        """Answer 404 for an act number that does not exist."""
        self.generate_acts()

        response = self.client.put("/api/story/acts/9", json={"summary": "Nothing.", "dramatic_function": "setup"})

        self.assertEqual(response.status_code, 404)

    def test_approves_acts(self) -> None:
        """Approve the acts and reject generating them again afterwards."""
        self.generate_acts()

        response = self.client.post("/api/story/acts/approve")

        self.assertTrue(response.json()["acts_approved"])
        self.assertEqual(self.client.post("/api/story/acts/generate").status_code, 409)
