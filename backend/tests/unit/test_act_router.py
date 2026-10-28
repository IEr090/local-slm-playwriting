from unittest import TestCase

from fastapi.testclient import TestClient

from anton.api.dependencies import get_scene_service, get_text_service
from anton.main import app
from tests.unit.test_scene_service import KITCHEN, PLAN, PROPOSAL, STRUCTURE, make_scene, make_service, make_story
from tests.unit.test_text_service import HISTORY, SCENE_TEXT, make_text_story
from tests.unit.test_text_service import make_service as make_text_service


class ActRouteTest(TestCase):
    """Test the endpoints of the act page from the structure to the approved scenes."""

    def setUp(self) -> None:
        """Replace the scene service with one that uses a fake model client and in-memory repositories."""
        self.service, _, self.repository = make_service(STRUCTURE, PLAN, PROPOSAL)
        app.dependency_overrides[get_scene_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def test_builds_act_from_structure_to_approved_scenes(self) -> None:
        """Generate the structure, approve it, plan and approve both scenes in order."""
        response = self.client.post("/api/story/acts/1/structure/generate")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["acts"][0]["scenes"]), 2)

        self.assertEqual(self.client.post("/api/story/acts/1/structure/approve").json()["acts"][0]["status"], "structure_approved")
        self.assertEqual(self.client.post("/api/story/acts/1/scenes/2/plan").status_code, 409)

        for scene in (1, 2):
            self.assertTrue(self.client.post(f"/api/story/acts/1/scenes/{scene}/plan").json()["acts"][0]["scenes"][scene - 1]["planned"])
            approved = self.client.post(f"/api/story/acts/1/scenes/{scene}/approve").json()

        self.assertEqual(approved["acts"][0]["status"], "scenes_approved")

    def test_next_act_before_text_returns_409(self) -> None:
        """Reject building Act Two before the text of Act One is approved, with a clear message."""
        response = self.client.post("/api/story/acts/2/structure/generate")

        self.assertEqual(response.status_code, 409)
        self.assertIn("Act 1", response.json()["message"])

    def test_edits_structure_by_hand(self) -> None:
        """Save the scenes the user reordered."""
        plans = [make_scene(2).to_plan().model_dump(), make_scene(1).to_plan().model_dump()]

        response = self.client.put("/api/story/acts/1/scenes", json=plans)

        self.assertEqual([scene["what_happens"] for scene in response.json()["acts"][0]["scenes"]], ["Scene 2 happens.", "Scene 1 happens."])

    def test_unknown_place_returns_404(self) -> None:
        """Answer 404 when a scene names a place that does not exist."""
        plan = make_scene(1, place_id="moon").to_plan().model_dump()

        response = self.client.put("/api/story/acts/1/scenes", json=[plan])

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["message"], "This place does not exist.")

    def test_unknown_scene_returns_404(self) -> None:
        """Answer 404 for a scene number the act does not have."""
        self.repository.save(make_story(make_scene(1), status="structure_approved"))

        response = self.client.post("/api/story/acts/1/scenes/9/approve")

        self.assertEqual(response.status_code, 404)

    def test_revises_structure_in_chat(self) -> None:
        """Return the agent's reply, the scenes from the form and the places, and keep the chat history."""
        self.repository.save(make_story(make_scene(1)))
        body = {"message": "Add a scene.", "scenes": [make_scene(1).to_plan().model_dump()]}

        response = self.client.post("/api/story/acts/1/structure/revise", json=body)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], PROPOSAL.reply)
        self.assertEqual(response.json()["places"], [KITCHEN.model_dump()])
        self.assertEqual(len(self.client.get("/api/story/acts/1/chat").json()), 2)

    def test_creates_and_lists_places(self) -> None:
        """Create a place by hand and return it with the others."""
        created = self.client.post("/api/story/places", json={"name": "The landing", "description": "Dark.", "significance": ""}).json()

        response = self.client.get("/api/story/places")

        self.assertEqual([place["name"] for place in response.json()], ["The keeper's kitchen", "The landing"])
        self.assertTrue(created["id"])


class TextRouteTest(TestCase):
    """Test the endpoints of the act text, from writing it to recording the character histories."""

    def setUp(self) -> None:
        """Replace the text service with one that uses a fake model client and in-memory repositories."""
        self.service, _, self.repository, self.cast_repository = make_text_service(
            SCENE_TEXT, HISTORY, story=make_text_story(texts=False),
        )
        app.dependency_overrides[get_text_service] = lambda: self.service
        self.client = TestClient(app)

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def test_writes_and_approves_text(self) -> None:
        """Write the text, approve it and append the character histories."""
        written = self.client.post("/api/story/acts/1/text/generate").json()
        self.assertTrue(written["acts"][0]["text"].startswith("SCENE 1"))

        approved = self.client.post("/api/story/acts/1/text/approve").json()

        self.assertEqual(approved["acts"][0]["status"], "text_approved")
        self.assertEqual(len(self.cast_repository.load().characters[1].history), 2)

    def test_approve_before_text_returns_409(self) -> None:
        """Reject approving before the text is written."""
        response = self.client.post("/api/story/acts/1/text/approve")

        self.assertEqual(response.status_code, 409)
        self.assertIn("has not been written", response.json()["message"])

    def test_saves_text_from_form(self) -> None:
        """Save the scene texts the user took over."""
        self.client.post("/api/story/acts/1/text/generate")
        texts = [{"scene_number": 1, "text": "ELIAS: Changed."}, {"scene_number": 2, "text": "ELIAS: Two."}]

        response = self.client.put("/api/story/acts/1/text", json=texts)

        self.assertEqual(response.json()["acts"][0]["scene_texts"], texts)
