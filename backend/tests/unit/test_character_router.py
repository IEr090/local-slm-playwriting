from unittest import TestCase

from fastapi.testclient import TestClient

from anton.api.dependencies import get_character_service, get_edit_agent, get_slm_client
from anton.application.character_service import CharacterService
from anton.application.agents.character_target import CharacterTarget
from anton.application.agents.chat_edit_agent import ChatEditAgent, create_checkpointer
from anton.application.llm_schemas.chat_turn import ChatTurn
from anton.errors import SLMResponseError, SLMUnavailableError
from anton.main import app
from tests.unit.fakes import CARD, FailingSLMClient, FakeSLMClient, InMemoryCastRepository, ScriptedSLMClient, make_draft


def make_service(client, repository: InMemoryCastRepository) -> CharacterService:
    """Create the character service with an edit agent that is never used to chat."""
    edit_agent = ChatEditAgent(FakeSLMClient(), CharacterTarget(), create_checkpointer())
    return CharacterService(client, repository, edit_agent)


class CreateCharacterRouteTest(TestCase):
    """Test the endpoint that creates a character."""

    def setUp(self) -> None:
        """Replace the character service with one that uses a fake model client."""
        app.dependency_overrides[get_character_service] = lambda: make_service(FakeSLMClient(CARD), InMemoryCastRepository())
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


class SavedCastRouteTest(TestCase):
    """Test the endpoints that read and edit the saved cast."""

    def setUp(self) -> None:
        """Replace the character service with one that uses a fake model client and an in-memory cast."""
        repository = InMemoryCastRepository()
        app.dependency_overrides[get_character_service] = lambda: make_service(FakeSLMClient(CARD), repository)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def test_get_without_cast_returns_404(self) -> None:
        """Answer 404 before any cast is generated."""
        response = self.client.get("/api/characters")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(set(response.json()), {"message", "detail"})

    def test_get_returns_created_character(self) -> None:
        """Return the character created before with its card."""
        created = self.client.post("/api/characters", json=make_draft().model_dump()).json()

        response = self.client.get("/api/characters")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual([character["id"] for character in body["characters"]], [created["character"]["id"]])
        self.assertEqual(body["cards"][created["character"]["id"]]["tagline"], CARD.tagline)

    def test_put_updates_character(self) -> None:
        """Save the edited profile so that the next read returns it."""
        character_id = self.client.post("/api/characters", json=make_draft().model_dump()).json()["character"]["id"]
        payload = make_draft().model_dump() | {"age": 48}

        response = self.client.put(f"/api/characters/{character_id}", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["character"]["age"], 48)
        self.assertEqual(self.client.get("/api/characters").json()["characters"][0]["age"], 48)

    def test_put_unknown_character_returns_404(self) -> None:
        """Answer 404 when the character is not in the saved cast."""
        self.client.post("/api/characters", json=make_draft().model_dump())

        response = self.client.put("/api/characters/unknown", json=make_draft().model_dump())

        self.assertEqual(response.status_code, 404)


class ModelErrorRouteTest(TestCase):
    """Test how the API reports model failures."""

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def generate_with(self, error: Exception):
        """Generate a cast with a model client that raises the given error."""
        app.dependency_overrides[get_character_service] = lambda: make_service(FailingSLMClient(error), InMemoryCastRepository())
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


class ReviseRouteTest(TestCase):
    """Test the endpoints of the chat that revises a character."""

    def setUp(self) -> None:
        """Replace the edit agent with one that uses a scripted model client."""
        self.model = ScriptedSLMClient(ChatTurn(reply="In what way?", apply_changes=None))
        agent = ChatEditAgent(self.model, CharacterTarget(), create_checkpointer())
        app.dependency_overrides[get_edit_agent] = lambda: agent
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def test_post_returns_reply_and_character(self) -> None:
        """Answer with the model reply and the character under the id from the path."""
        response = self.client.post(
            "/api/characters/first/revise",
            json={"message": "Change her.", "character": make_draft().model_dump()},
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["reply"], "In what way?")
        self.assertEqual(body["character"]["id"], "first")
        self.assertEqual(body["character"]["name"], "Elena")

    def test_post_ignores_id_in_body(self) -> None:
        """Use the id from the path even if the body character has another one."""
        character = make_draft().model_dump() | {"id": "client-id"}

        response = self.client.post("/api/characters/first/revise", json={"message": "Change her.", "character": character})

        self.assertEqual(response.json()["character"]["id"], "first")
        self.assertEqual(len(self.client.get("/api/characters/first/revise").json()), 2)

    def test_post_rejects_empty_message(self) -> None:
        """Answer 422 without calling the model when the message is empty."""
        response = self.client.post("/api/characters/first/revise", json={"message": "", "character": make_draft().model_dump()})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.model.calls, [])

    def test_post_model_error_returns_502(self) -> None:
        """Report an unusable model answer of the chat as 502."""
        agent = ChatEditAgent(ScriptedSLMClient(SLMResponseError("bad")), CharacterTarget(), create_checkpointer())
        app.dependency_overrides[get_edit_agent] = lambda: agent

        response = self.client.post(
            "/api/characters/first/revise",
            json={"message": "Change her.", "character": make_draft().model_dump()},
        )

        self.assertEqual(response.status_code, 502)

    def test_get_returns_history(self) -> None:
        """Return the chat history of the character."""
        self.client.post("/api/characters/first/revise", json={"message": "Change her.", "character": make_draft().model_dump()})

        response = self.client.get("/api/characters/first/revise")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            [{"role": "user", "content": "Change her."}, {"role": "assistant", "content": "In what way?"}],
        )

    def test_get_without_conversation_returns_empty_list(self) -> None:
        """Return an empty history, not 404, for a character nobody has chatted about."""
        response = self.client.get("/api/characters/unknown/revise")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])


class LifespanTest(TestCase):
    """Test what the application does when it stops."""

    def test_closes_model_client_on_shutdown(self) -> None:
        """Close the shared model client once the application stops."""
        model = get_slm_client()

        with TestClient(app):
            pass

        self.assertTrue(model.client._client.is_closed)
        get_slm_client.cache_clear()
