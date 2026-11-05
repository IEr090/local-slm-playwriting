import json
from unittest import IsolatedAsyncioTestCase

from anton.application.agents.act_chat import ActChat
from anton.application.agents.chat_edit_agent import create_checkpointer
from anton.application.llm_schemas.chat_turn import ChatTurn
from anton.application.llm_schemas.scene_generation import (
    EditedScene,
    EditedScenes,
    GeneratedActScene,
    GeneratedActStructure,
    GeneratedPlace,
    GeneratedScenePlan,
    GeneratedStructure,
    GeneratedStructureScene,
)
from anton.application.scene_planner import ScenePlanner
from anton.application.scene_service import SceneService
from anton.domain.models import Cast, Character, CharacterHistoryEntry, Place, PlaceDraft, Scene, ScenePlan, StoryBible
from anton.errors import CharacterNotFoundError, PlaceNotFoundError, SceneNotFoundError, StoryOrderError
from tests.unit.fakes import FakeSLMClient, InMemoryCastRepository, InMemoryStoryRepository, make_draft
from tests.unit.test_story_models import make_outline
from tests.unit.test_story_service import make_acts


KITCHEN = Place(id="kitchen", name="The keeper's kitchen", description="A stove and a table for three.", significance="Home.")
STRUCTURE = GeneratedActStructure(
    new_places=[GeneratedPlace(name=" The lamp room ", description="A great lens.", significance="The light.")],
    scenes=[
        GeneratedActScene(place="The keeper's kitchen", characters=["Elias Hale"], what_happens=" Elias arrives. "),
        GeneratedActScene(place="The lamp room", characters=["Margit", "Elias"], what_happens="Voss reads the will."),
    ],
)
PLAN = GeneratedScenePlan(place_notes=" Shutters barred ", what_happens=" Late afternoon. Elias arrives soaked. ")
PROPOSAL = ChatTurn(reply="I suggest a scene at dawn. Confirm?", apply_changes=None)
AGREED = ChatTurn(reply="Applying.", apply_changes="add after scene 2: place The landing; characters Elias")
STRUCTURE_EDIT = GeneratedStructure(
    new_places=[GeneratedPlace(name="The landing", description="A single candle.", significance="Secrets.")],
    scenes=STRUCTURE.scenes + [GeneratedStructureScene(place="The landing", characters=["Elias"], what_happens="Dawn.")],
)


def make_characters() -> list[Character]:
    """Create two characters with ids that read like names."""
    return [
        Character(id="margit", **(make_draft().model_dump() | {"name": "Margit", "surname": "Hale"})),
        Character(id="elias", **(make_draft().model_dump() | {"name": "Elias", "surname": "Hale", "gender": "male"})),
    ]


def make_scene(number: int, **changes) -> Scene:
    """Create a planned draft scene in the kitchen with Elias."""
    return Scene(**({
        "number": number, "place_id": "kitchen", "place_notes": "Dark", "character_ids": ["elias"],
        "what_happens": f"Scene {number} happens.", "planned": True,
    } | changes))


def make_story(*scenes: Scene, status: str = "draft") -> StoryBible:
    """Create a Story Bible with approved acts whose first act has the given scenes."""
    acts = make_acts()
    acts[0].scenes = list(scenes)
    acts[0].status = status
    return StoryBible(outline=make_outline(), acts=acts, acts_approved=True, places=[KITCHEN])


def make_service(*responses, story: StoryBible | None = None, cast: Cast | None = None):
    """Create the scene service with in-memory repositories and agents that share a fake model client."""
    client = FakeSLMClient(*responses)
    repository = InMemoryStoryRepository(story if story is not None else make_story())
    cast_repository = InMemoryCastRepository(cast or Cast(characters=make_characters(), cards={}))
    service = SceneService(repository, cast_repository, ActChat(client, create_checkpointer()), ScenePlanner(client))
    return service, client, repository


def plans(*scenes: Scene) -> list[ScenePlan]:
    """Keep only the plan fields, as the user's form sends them."""
    return [scene.to_plan() for scene in scenes]


class OrderTest(IsolatedAsyncioTestCase):
    """Test that the scenes of an act can only be built in order."""

    async def test_rejects_structure_before_acts_are_approved(self) -> None:
        """Reject building scenes while the acts are not approved."""
        story = make_story()
        story.acts_approved = False
        service, client, _ = make_service(STRUCTURE, story=story)

        with self.assertRaises(StoryOrderError):
            await service.generate_structure(1)
        self.assertEqual(client.calls, [])

    async def test_rejects_next_act_before_text_of_previous(self) -> None:
        """Reject building Act Two before the text of Act One is approved."""
        service, *_ = make_service(STRUCTURE, story=make_story(status="scenes_approved"))

        with self.assertRaises(StoryOrderError) as raised:
            await service.generate_structure(2)
        self.assertIn("Act 1", str(raised.exception))

    async def test_allows_next_act_after_text_of_previous(self) -> None:
        """Build Act Two once the text of Act One is approved."""
        service, *_ = make_service(STRUCTURE, story=make_story(status="text_approved"))

        story = await service.generate_structure(2)

        self.assertEqual(len(story.acts[1].scenes), 2)


class GenerateStructureTest(IsolatedAsyncioTestCase):
    """Test proposing the scenes of an act."""

    async def asyncSetUp(self) -> None:
        """Create the service with approved acts."""
        self.service, self.client, self.repository = make_service(STRUCTURE)

    async def test_saves_numbered_draft_scenes_with_ids(self) -> None:
        """Save the scenes in order with place and character ids, as unplanned drafts."""
        story = await self.service.generate_structure(1)

        scenes = story.acts[0].scenes
        lamp_room = story.places[1]
        self.assertEqual([scene.to_plan() for scene in scenes], [
            ScenePlan(place_id="kitchen", place_notes="", character_ids=["elias"], what_happens="Elias arrives."),
            ScenePlan(place_id=lamp_room.id, place_notes="", character_ids=["margit", "elias"], what_happens="Voss reads the will."),
        ])
        self.assertEqual([(scene.number, scene.planned, scene.status) for scene in scenes], [(1, False, "draft"), (2, False, "draft")])
        self.assertEqual(self.repository.load(), story)

    async def test_saves_proposed_places(self) -> None:
        """Add the places the model proposed to the places of the play."""
        story = await self.service.generate_structure(1)

        self.assertEqual(
            [place.model_dump(exclude={"id"}) for place in story.places[1:]],
            [{"name": "The lamp room", "description": "A great lens.", "significance": "The light."}],
        )

    async def test_remembers_summary_for_warning(self) -> None:
        """Remember the summary the scenes were built from, so a later edit can be noticed."""
        story = await self.service.generate_structure(1)

        self.assertEqual(story.acts[0].scenes_built_from_summary, story.acts[0].summary)
        self.assertFalse(story.acts[0].summary_changed)

    async def test_sends_act_places_and_cast(self) -> None:
        """Give the model the outline, the act, the earlier acts, the places and the cast."""
        await self.service.generate_structure(1)

        prompt = self.client.calls[0]["user_prompt"]
        for heading in ("# OUTLINE", "# ACT", "# EARLIER ACTS", "# PLACES", "# CAST"):
            self.assertIn(heading, prompt)
        self.assertIn("The siblings arrive.", prompt)
        self.assertIn("The keeper's kitchen", prompt)
        self.assertNotIn("synopsis", prompt)
        self.assertTrue(self.client.calls[0]["think"])

    async def test_regenerates_while_draft(self) -> None:
        """Replace the scenes when the structure is generated again before it is approved."""
        await self.service.generate_structure(1)

        story = await self.service.generate_structure(1)

        self.assertEqual(len(story.acts[0].scenes), 2)
        self.assertEqual(len(story.places), 2)

    async def test_rejects_after_approval(self) -> None:
        """Reject generating the structure again once it is approved."""
        await self.service.generate_structure(1)
        self.service.approve_structure(1)

        with self.assertRaises(StoryOrderError):
            await self.service.generate_structure(1)

    async def test_warns_when_summary_changes_after_scenes(self) -> None:
        """Set the warning flag when the act summary is edited after its scenes were built."""
        story = await self.service.generate_structure(1)
        story.acts[0].summary = "Margit arrives first."

        self.assertTrue(story.acts[0].summary_changed)


class EditStructureTest(IsolatedAsyncioTestCase):
    """Test reordering, cutting and adding scenes by hand."""

    async def test_saves_scenes_in_new_order(self) -> None:
        """Number the scenes in the order the user sent them."""
        service, _, repository = make_service(story=make_story(make_scene(1), make_scene(2)))
        new = ScenePlan(place_id="", place_notes="", character_ids=[], what_happens="A new scene.")

        story = service.edit_structure(1, [make_scene(2).to_plan(), new])

        self.assertEqual([scene.what_happens for scene in story.acts[0].scenes], ["Scene 2 happens.", "A new scene."])
        self.assertEqual([scene.number for scene in repository.load().acts[0].scenes], [1, 2])

    async def test_rejects_unknown_place(self) -> None:
        """Reject a scene that names a place the play does not have."""
        service, *_ = make_service()

        with self.assertRaises(PlaceNotFoundError):
            service.edit_structure(1, [ScenePlan(place_id="moon", place_notes="", character_ids=[], what_happens="")])

    async def test_rejects_unknown_character(self) -> None:
        """Reject a scene with a character the cast does not have."""
        service, *_ = make_service()

        with self.assertRaises(CharacterNotFoundError):
            service.edit_structure(1, [ScenePlan(place_id="", place_notes="", character_ids=["ghost"], what_happens="")])

    async def test_rejects_after_approval(self) -> None:
        """Reject changing the list of scenes once the structure is approved."""
        service, *_ = make_service(story=make_story(make_scene(1), status="structure_approved"))

        with self.assertRaises(StoryOrderError):
            service.edit_structure(1, plans(make_scene(1)))


class ReviseStructureTest(IsolatedAsyncioTestCase):
    """Test the act chat while the structure is a draft."""

    async def test_returns_reply_scenes_and_places_without_saving_scenes(self) -> None:
        """Answer with the scenes from the form and leave the saved scenes unchanged."""
        story = make_story(make_scene(1))
        service, _, repository = make_service(PROPOSAL, story=story)

        result = await service.revise_structure(1, plans(make_scene(1, what_happens="Edited in the form.")), "Add a scene.")

        self.assertEqual(result.reply, PROPOSAL.reply)
        self.assertEqual(result.scenes[0].what_happens, "Edited in the form.")
        self.assertEqual(result.places, [KITCHEN])
        self.assertEqual(repository.load(), story)

    async def test_sends_names_and_context_to_chat(self) -> None:
        """Show the model place and character names, the act summary, the places and the cast."""
        service, client, _ = make_service(PROPOSAL, story=make_story(make_scene(1)))

        await service.revise_structure(1, plans(make_scene(1)), "Add a scene.")

        prompt = json.loads(client.calls[0]["user_prompt"])
        self.assertEqual(prompt["scenes"], [{"number": 1, "place": "The keeper's kitchen", "characters": ["Elias Hale"], "what_happens": "Scene 1 happens."}])
        self.assertEqual(prompt["act_summary"], "The siblings arrive.")
        self.assertEqual(prompt["characters"], ["Margit Hale", "Elias Hale"])
        self.assertEqual(prompt["places"], [{"name": "The keeper's kitchen", "description": KITCHEN.description}])

    async def test_applies_agreed_change_and_saves_new_place(self) -> None:
        """Return the edited scenes with the id of the new place, which is saved right away."""
        service, _, repository = make_service(AGREED, STRUCTURE_EDIT, story=make_story(make_scene(1)))

        result = await service.revise_structure(1, plans(make_scene(1)), "Yes.")

        landing = next(place for place in result.places if place.name == "The landing")
        self.assertEqual(len(result.scenes), 3)
        self.assertEqual(result.scenes[2].place_id, landing.id)
        self.assertEqual(repository.load().places, result.places)
        self.assertEqual(repository.load().acts[0].scenes, [make_scene(1)])

    async def test_rejects_after_approval(self) -> None:
        """Reject chatting about the structure once it is approved."""
        service, *_ = make_service(PROPOSAL, story=make_story(make_scene(1), status="structure_approved"))

        with self.assertRaises(StoryOrderError):
            await service.revise_structure(1, plans(make_scene(1)), "Add a scene.")


class ApproveStructureTest(IsolatedAsyncioTestCase):
    """Test approving the list of scenes."""

    async def test_approves_structure(self) -> None:
        """Mark the structure as approved."""
        service, _, repository = make_service(story=make_story(make_scene(1)))

        service.approve_structure(1)

        self.assertEqual(repository.load().acts[0].status, "structure_approved")

    async def test_rejects_empty_structure(self) -> None:
        """Reject approving an act without scenes."""
        service, *_ = make_service()

        with self.assertRaises(StoryOrderError):
            service.approve_structure(1)

    async def test_rejects_scene_without_place(self) -> None:
        """Reject approving while a scene has no place."""
        service, *_ = make_service(story=make_story(make_scene(1, place_id="")))

        with self.assertRaises(StoryOrderError):
            service.approve_structure(1)


class PlanSceneTest(IsolatedAsyncioTestCase):
    """Test writing the plans of the scenes one by one."""

    def make(self, *scenes: Scene, cast: Cast | None = None):
        """Create the service with an approved structure of the given scenes."""
        self.service, self.client, self.repository = make_service(
            PLAN, story=make_story(*scenes, status="structure_approved"), cast=cast,
        )

    async def test_saves_plan_with_trimmed_text(self) -> None:
        """Save the place notes and the detailed events, and mark the scene as planned."""
        self.make(make_scene(1, planned=False, place_notes=""))

        story = await self.service.plan_scene(1, 1)

        scene = story.acts[0].scenes[0]
        self.assertEqual((scene.place_notes, scene.what_happens), ("Shutters barred", "Late afternoon. Elias arrives soaked."))
        self.assertEqual((scene.planned, scene.status), (True, "draft"))
        self.assertEqual(self.repository.load(), story)

    async def test_plans_next_scene_after_previous_is_approved(self) -> None:
        """Plan scene two once scene one is approved and remember what it was built from."""
        self.make(make_scene(1, status="approved"), make_scene(2, planned=False))

        story = await self.service.plan_scene(1, 2)

        self.assertEqual(story.acts[0].scenes[1].plan_built_from, [make_scene(1).to_plan()])
        self.assertEqual(story.acts[0].outdated_plans, [])

    async def test_rejects_scene_before_previous_is_approved(self) -> None:
        """Reject planning scene two while scene one is a draft."""
        self.make(make_scene(1), make_scene(2, planned=False))

        with self.assertRaises(StoryOrderError):
            await self.service.plan_scene(1, 2)
        self.assertEqual(self.client.calls, [])

    async def test_rejects_approved_scene(self) -> None:
        """Reject planning a scene that is already approved."""
        self.make(make_scene(1, status="approved"))

        with self.assertRaises(StoryOrderError):
            await self.service.plan_scene(1, 1)

    async def test_rejects_before_structure_is_approved(self) -> None:
        """Reject planning while the structure is a draft."""
        service, *_ = make_service(PLAN, story=make_story(make_scene(1)))

        with self.assertRaises(StoryOrderError):
            await service.plan_scene(1, 1)

    async def test_raises_for_unknown_scene(self) -> None:
        """Report a scene number the act does not have."""
        self.make(make_scene(1))

        with self.assertRaises(SceneNotFoundError):
            await self.service.plan_scene(1, 9)

    async def test_sends_earlier_scenes_place_and_characters_with_history(self) -> None:
        """Give the planner the approved earlier scenes, the place and the profiles and history up to this scene."""
        characters = make_characters()
        characters[1].history = [
            CharacterHistoryEntry(act_number=0, scene_number=1, change="Left the island."),
            CharacterHistoryEntry(act_number=1, scene_number=5, change="Later change."),
        ]
        self.make(make_scene(1, status="approved"), make_scene(2, planned=False), cast=Cast(characters=characters, cards={}))

        await self.service.plan_scene(1, 2)

        prompt = json.loads(self.client.calls[0]["user_prompt"])
        self.assertEqual([scene["number"] for scene in prompt["earlier_scenes"]], [1])
        self.assertEqual(prompt["scene"]["number"], 2)
        self.assertEqual(prompt["place"], {"name": "The keeper's kitchen", "description": KITCHEN.description})
        self.assertEqual([character["name"] for character in prompt["characters"]], ["Elias"])
        self.assertEqual(prompt["characters"][0]["history"], ["Left the island."])
        self.assertNotIn("biography", prompt["characters"][0])


class SceneApprovalTest(IsolatedAsyncioTestCase):
    """Test editing, approving and reopening the scene plans."""

    async def test_approving_last_scene_approves_scenes(self) -> None:
        """Move the act to scenes approved when every scene is approved."""
        service, _, repository = make_service(story=make_story(make_scene(1, status="approved"), make_scene(2), status="structure_approved"))

        story = service.approve_scene(1, 2)

        self.assertEqual(story.acts[0].status, "scenes_approved")

    async def test_approving_one_of_two_keeps_structure_approved(self) -> None:
        """Keep the act at structure approved while a scene is still a draft."""
        service, *_ = make_service(story=make_story(make_scene(1), make_scene(2), status="structure_approved"))

        story = service.approve_scene(1, 1)

        self.assertEqual((story.acts[0].scenes[0].status, story.acts[0].status), ("approved", "structure_approved"))

    async def test_rejects_scene_without_plan(self) -> None:
        """Reject approving a scene whose plan has not been written."""
        service, *_ = make_service(story=make_story(make_scene(1, planned=False), status="structure_approved"))

        with self.assertRaises(StoryOrderError):
            service.approve_scene(1, 1)

    async def test_reopening_takes_back_scenes_approval(self) -> None:
        """Make the scene a draft and move the act back to structure approved."""
        service, *_ = make_service(story=make_story(make_scene(1, status="approved"), status="scenes_approved"))

        story = service.reopen_scene(1, 1)

        self.assertEqual((story.acts[0].scenes[0].status, story.acts[0].status), ("draft", "structure_approved"))

    async def test_editing_approved_scene_reopens_it(self) -> None:
        """Save the edited plan and make the scene a draft again."""
        service, *_ = make_service(story=make_story(make_scene(1, status="approved"), status="scenes_approved"))
        plan = make_scene(1, what_happens="Elias arrives at night.").to_plan()

        story = service.edit_scene(1, 1, plan)

        self.assertEqual(story.acts[0].scenes[0].to_plan(), plan)
        self.assertEqual((story.acts[0].scenes[0].status, story.acts[0].status), ("draft", "structure_approved"))

    async def test_scenes_of_approved_text_are_final(self) -> None:
        """Reject planning, editing, approving and reopening scenes once the act's text is approved."""
        service, *_ = make_service(story=make_story(make_scene(1, status="approved"), status="text_approved"))

        for change in (
            lambda: service.reopen_scene(1, 1),
            lambda: service.approve_scene(1, 1),
            lambda: service.edit_scene(1, 1, make_scene(1).to_plan()),
        ):
            with self.assertRaises(StoryOrderError):
                change()
        with self.assertRaises(StoryOrderError):
            await service.plan_scene(1, 1)
        with self.assertRaises(StoryOrderError):
            await service.revise_scenes(1, [make_scene(1).to_plan()], "Change it.")

    async def test_editing_earlier_scene_marks_later_plans_outdated(self) -> None:
        """Expose the later scenes whose plans were written from the earlier version."""
        second = make_scene(2, plan_built_from=[make_scene(1).to_plan()])
        service, *_ = make_service(story=make_story(make_scene(1, status="approved"), second, status="structure_approved"))

        story = service.edit_scene(1, 1, make_scene(1, what_happens="Elias never arrives.").to_plan())

        self.assertEqual(story.acts[0].outdated_plans, [2])

    async def test_rejects_editing_before_structure_is_approved(self) -> None:
        """Reject editing a plan while the structure is a draft."""
        service, *_ = make_service(story=make_story(make_scene(1)))

        with self.assertRaises(StoryOrderError):
            service.edit_scene(1, 1, make_scene(1).to_plan())


class ReviseScenesTest(IsolatedAsyncioTestCase):
    """Test the act chat once the structure is approved."""

    async def test_applies_agreed_change_to_named_scene(self) -> None:
        """Change only the scene the model edited and save nothing but new places."""
        edited = EditedScenes(new_places=[], scenes=[EditedScene(
            number=1, place="The keeper's kitchen", place_notes="Candles", characters=["Margit"], what_happens=" Agnes already knows. ",
        )])
        story = make_story(make_scene(1), make_scene(2), status="structure_approved")
        service, client, repository = make_service(ChatTurn(reply="Applying.", apply_changes="scene 1 ..."), edited, story=story)

        result = await service.revise_scenes(1, plans(make_scene(1), make_scene(2)), "Yes.")

        self.assertEqual(result.scenes[0], ScenePlan(place_id="kitchen", place_notes="Candles", character_ids=["margit"], what_happens="Agnes already knows."))
        self.assertEqual(result.scenes[1], make_scene(2).to_plan())
        self.assertEqual(repository.load(), story)
        self.assertIn('"place_notes": "Dark"', client.calls[0]["user_prompt"])

    async def test_shares_chat_with_structure(self) -> None:
        """Keep one conversation for the act page across the structure and the plans."""
        story = make_story(make_scene(1))
        service, _, repository = make_service(PROPOSAL, story=story)
        await service.revise_structure(1, plans(make_scene(1)), "Add a scene.")
        service.approve_structure(1)

        await service.revise_scenes(1, plans(make_scene(1)), "Scene 1: at night.")

        self.assertEqual([message.content for message in await service.act_chat(1)], [
            "Add a scene.", PROPOSAL.reply, "Scene 1: at night.", PROPOSAL.reply,
        ])

    async def test_rejects_before_structure_is_approved(self) -> None:
        """Reject chatting about plans while the structure is a draft."""
        service, *_ = make_service(PROPOSAL, story=make_story(make_scene(1)))

        with self.assertRaises(StoryOrderError):
            await service.revise_scenes(1, plans(make_scene(1)), "Scene 1: at night.")


class PlacesAndChatsTest(IsolatedAsyncioTestCase):
    """Test the places of the play and forgetting the act chats."""

    async def test_creates_place_by_hand(self) -> None:
        """Give the new place an id and add it to the places of the play."""
        service, _, repository = make_service()

        place = service.create_place(PlaceDraft(name="The landing", description="Dark.", significance="Secrets."))

        self.assertTrue(place.id)
        self.assertEqual(service.get_places(), [KITCHEN, place])
        self.assertEqual(repository.load().places, [KITCHEN, place])

    async def test_forgets_act_chats(self) -> None:
        """Forget the conversation of every act page."""
        service, *_ = make_service(PROPOSAL, story=make_story(make_scene(1)))
        await service.revise_structure(1, plans(make_scene(1)), "Add a scene.")

        await service.forget_act_chats()

        self.assertEqual(await service.act_chat(1), [])
