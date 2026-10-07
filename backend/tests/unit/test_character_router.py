from unittest import TestCase

from fastapi.testclient import TestClient

from anton.api.dependencies import get_character_service
from anton.application.character_service import CharacterService
from anton.main import app
from anton.infrastructure.slm import SLMResponseError, SLMUnavailableError
from tests.unit.fakes import CARD, FailingSLMClient, FakeSLMClient, make_draft


class CreateCharacterRouteTest(TestCase):
    """Test the endpoint that creates a character."""

    def setUp(self) -> None:
        """Replace the character service with one that uses a fake model client."""
        app.dependency_overrides[get_character_service] = lambda: CharacterService(FakeSLMClient(CARD))
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def test_returns_character_with_card(self) -> None:
        """Return the created character with an id and its card."""
        response = self.client.post("/api/characters", json=make_draft().model_dump())

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["character"]["id"])
        self.assertEqual(body["character"]["name"], "Elena")
        self.assertEqual(body["card"]["tagline"], CARD.tagline)

    def test_ignores_id_from_request(self) -> None:
        """Generate a new id even if the client sends one."""
        payload = make_draft().model_dump() | {"id": "client-id"}

        response = self.client.post("/api/characters", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.json()["character"]["id"], "client-id")


class ModelErrorRouteTest(TestCase):
    """Test how the API reports model failures."""

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def generate_with(self, error: Exception):
        """Generate a cast with a model client that raises the given error."""
        app.dependency_overrides[get_character_service] = lambda: CharacterService(FailingSLMClient(error))
        return TestClient(app).post("/api/characters/generate", json={"premise": "A theatre in Vienna."})

    def test_unreachable_model_returns_503(self) -> None:
        """Ask the user to start Ollama when it cannot be reached."""
        response = self.generate_with(SLMUnavailableError("Ollama is not reachable"))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["message"], "Could not reach the local model. Is Ollama running?")
        self.assertEqual(response.json()["detail"], "Ollama is not reachable")

    def test_unusable_answer_returns_502(self) -> None:
        """Report an unusable model answer with its technical detail."""
        response = self.generate_with(SLMResponseError("qwen3:4b returned an invalid GeneratedCast"))

        self.assertEqual(response.status_code, 502)
        self.assertEqual(set(response.json()), {"message", "detail"})
        self.assertEqual(response.json()["detail"], "qwen3:4b returned an invalid GeneratedCast")
