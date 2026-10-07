from unittest import TestCase

from fastapi.testclient import TestClient

from anton.api.dependencies import get_character_service
from anton.application.character_service import CharacterService
from anton.main import app
from tests.unit.fakes import CARD, FakeSLMClient, make_draft


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
