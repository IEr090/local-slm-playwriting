import json
from uuid import uuid4

from pydantic import BaseModel

from anton.application.agents.chat_edit_agent import ChatEditAgent, ChatMessage
from anton.application.agents.scene_targets import SceneBoard
from anton.application.mappers.scene_mapper import add_new_places, full_name, to_scene_plans, to_scene_views, to_scenes
from anton.application.scene_planner import ScenePlanner
from anton.application.story_service import ACT_CAST_FIELDS, cast_json, find_act
from anton.domain.models import Act, Cast, Place, PlaceDraft, Scene, ScenePlan, StoryBible
from anton.errors import CastNotFoundError, CharacterNotFoundError, PlaceNotFoundError, SceneNotFoundError, StoryNotFoundError, StoryOrderError
from anton.infrastructure.storage import CastRepository, StoryRepository


OUTLINE_FIELDS = {"premise", "genre", "tone", "time_and_world", "central_conflict"}
PLAN_CHARACTER_FIELDS = {
    "name", "surname", "age", "personality",
    "goal", "motivation", "fear_weakness", "internal_conflict",
}


class SceneRevision(BaseModel):
    """Represent the answer of the act agent, the scenes as it sees them now and all places, new ones included."""

    reply: str
    scenes: list[ScenePlan]
    places: list[Place]


class SceneService:
    """Build the scenes of an act: the structure, then the detailed plan of every scene, and keep the places."""

    def __init__(
        self,
        story_repository: StoryRepository,
        cast_repository: CastRepository,
        structure_agent: ChatEditAgent[SceneBoard],
        scenes_agent: ChatEditAgent[SceneBoard],
        planner: ScenePlanner,
    ) -> None:
        """Initialize the service with its repositories, the two agents of the act page and the scene planner.

        Both agents share one store of conversations, so the act page has one chat whatever the stage.
        """
        self.story_repository = story_repository
        self.cast_repository = cast_repository
        self.structure_agent = structure_agent
        self.scenes_agent = scenes_agent
        self.planner = planner

    def get_places(self) -> list[Place]:
        """Return all places of the play."""
        return self._get_story().places

    def create_place(self, draft: PlaceDraft) -> Place:
        """Add a place the user created by hand to the places of the play."""
        story = self._get_story()
        place = Place(id=str(uuid4()), **draft.model_dump())
        story.places.append(place)
        self.story_repository.save(story)
        return place

    async def generate_structure(self, number: int) -> StoryBible:
        """Propose the scenes of an act, picking existing places or proposing new ones; starts the act's chat anew."""
        story = self._get_story()
        act = _require_structure_draft(story, number)
        cast = self._get_cast()

        board = await self.structure_agent.generate(act_thread(number), {
            "outline": story.outline.model_dump_json(include=OUTLINE_FIELDS, indent=2),
            "act": act.model_dump_json(include={"number", "dramatic_function", "summary"}, indent=2),
            "earlier_acts": _json([item.model_dump(include={"number", "summary"}) for item in story.acts if item.number < number]),
            "places": _json([place.model_dump(include={"name", "description"}) for place in story.places]),
            "cast": cast_json(cast, ACT_CAST_FIELDS),
        })

        # Another request may have saved the Story Bible while the structure was generated.
        story = self._get_story()
        act = _require_structure_draft(story, number)
        story.places = add_new_places(board, story.places)
        act.scenes = to_scenes(to_scene_plans(board.scenes, story.places, cast.characters))
        act.scenes_built_from_summary = act.summary
        self.story_repository.save(story)
        return story

    def edit_structure(self, number: int, plans: list[ScenePlan]) -> StoryBible:
        """Replace the scenes of the structure with the list the user reordered, cut or extended by hand."""
        story = self._get_story()
        act = _require_structure_draft(story, number)
        self._check_references(story, plans)
        act.scenes = to_scenes(plans)
        self.story_repository.save(story)
        return story

    async def revise_structure(self, number: int, plans: list[ScenePlan], message: str) -> SceneRevision:
        """Send the user's message with the scenes from their form to the act agent; only new places are saved."""
        story = self._get_story()
        act = _require_structure_draft(story, number)
        return await self._revise(self.structure_agent, story, act, plans, message)

    def approve_structure(self, number: int) -> StoryBible:
        """Approve the list of scenes, so their plans can be written one by one."""
        story = self._get_story()
        act = _require_structure_draft(story, number)
        if not act.scenes:
            raise StoryOrderError(f"Act {number} has no scenes yet.")
        if any(not scene.place_id for scene in act.scenes):
            raise StoryOrderError("Every scene needs a place before the structure can be approved.")
        act.status = "structure_approved"
        self.story_repository.save(story)
        return story

    async def plan_scene(self, number: int, scene_number: int) -> StoryBible:
        """Write the detailed plan of a scene once the scene before it is approved."""
        story = self._get_story()
        act, scene = self._get_scene_to_plan(story, number, scene_number)
        cast = self._get_cast()
        views = to_scene_views(act.scenes, story.places, cast.characters)
        place = find_place(story, scene.place_id)

        generated = await self.planner.plan(
            act_summary=act.summary,
            earlier_scenes=views[:scene_number - 1],
            scene=views[scene_number - 1],
            place=place.model_dump(include={"name", "description"}),
            characters=on_stage_profiles(cast, scene, number),
        )

        story = self._get_story()
        act, scene = self._get_scene_to_plan(story, number, scene_number)
        scene.place_notes = generated.place_notes
        scene.what_happens = generated.what_happens
        scene.planned = True
        scene.plan_built_from = [item.to_plan() for item in act.scenes[:scene_number - 1]]
        self.story_repository.save(story)
        return story

    def edit_scene(self, number: int, scene_number: int, plan: ScenePlan) -> StoryBible:
        """Replace the plan of a scene with the one the user edited by hand; the scene has to be approved again."""
        story = self._get_story()
        act = _require_scenes_open(story, number)
        scene = find_scene(act, scene_number)
        self._check_references(story, [plan])
        for field, value in plan.model_dump().items():
            setattr(scene, field, value)
        _reopen(act, scene)
        self.story_repository.save(story)
        return story

    async def revise_scenes(self, number: int, plans: list[ScenePlan], message: str) -> SceneRevision:
        """Send the user's message with the scene plans from their form to the act agent; only new places are saved."""
        story = self._get_story()
        act = _require_scenes_open(story, number)
        return await self._revise(self.scenes_agent, story, act, plans, message)

    def approve_scene(self, number: int, scene_number: int) -> StoryBible:
        """Approve the plan of a scene; when the last scene is approved, the act's scenes are approved."""
        story = self._get_story()
        act = _require_scenes_open(story, number)
        scene = find_scene(act, scene_number)
        if not scene.planned:
            raise StoryOrderError(f"Scene {scene_number} has no plan yet.")
        scene.status = "approved"
        if act.status == "structure_approved" and all(item.status == "approved" for item in act.scenes):
            act.status = "scenes_approved"
        self.story_repository.save(story)
        return story

    def reopen_scene(self, number: int, scene_number: int) -> StoryBible:
        """Take back the approval of a scene, so it can be changed again."""
        story = self._get_story()
        act = _require_scenes_open(story, number)
        _reopen(act, find_scene(act, scene_number))
        self.story_repository.save(story)
        return story

    async def act_chat(self, number: int) -> list[ChatMessage]:
        """Return the chat history of the act page; both agents write into the same conversation."""
        return await self.structure_agent.history(act_thread(number))

    async def forget_act_chats(self) -> None:
        """Forget the chats of every act page, e.g. when a new play is started."""
        story = self.story_repository.load()
        for act in story.acts if story is not None else []:
            await self.structure_agent.forget(act_thread(act.number))

    async def _revise(
        self, agent: ChatEditAgent[SceneBoard], story: StoryBible, act: Act, plans: list[ScenePlan], message: str,
    ) -> SceneRevision:
        """Let the agent answer about the scenes, save the places it proposed and turn names back into ids."""
        self._check_references(story, plans)
        cast = self._get_cast()
        board = SceneBoard(scenes=to_scene_views(plans, story.places, cast.characters))

        result = await agent.send(act_thread(act.number), board, message, context={
            "act_summary": act.summary,
            "places": [place.model_dump(include={"name", "description"}) for place in story.places],
            "characters": [full_name(character) for character in cast.characters],
        })

        story = self._get_story()
        places = add_new_places(result.data, story.places)
        if len(places) != len(story.places):
            story.places = places
            self.story_repository.save(story)
        return SceneRevision(
            reply=result.reply,
            scenes=to_scene_plans(result.data.scenes, places, cast.characters),
            places=places,
        )

    def _get_scene_to_plan(self, story: StoryBible, number: int, scene_number: int) -> tuple[Act, Scene]:
        """Return the act and the scene to plan and make sure the scene before it is approved."""
        act = _require_scenes_open(story, number)
        scene = find_scene(act, scene_number)
        if scene.status == "approved":
            raise StoryOrderError(f"Scene {scene_number} is approved. Reopen it to plan it again.")
        if scene_number > 1 and act.scenes[scene_number - 2].status != "approved":
            raise StoryOrderError(f"Approve scene {scene_number - 1} before planning scene {scene_number}.")
        return act, scene

    def _check_references(self, story: StoryBible, plans: list[ScenePlan]) -> None:
        """Reject scenes that name a place or a character the play does not have; an empty place is allowed."""
        place_ids = {place.id for place in story.places}
        character_ids = {character.id for character in self._get_cast().characters}
        for plan in plans:
            if plan.place_id and plan.place_id not in place_ids:
                raise PlaceNotFoundError(f"Place {plan.place_id} is not in the Story Bible.")
            for character_id in plan.character_ids:
                if character_id not in character_ids:
                    raise CharacterNotFoundError(f"Character {character_id} is not in the saved cast.")

    def _get_story(self) -> StoryBible:
        """Return the saved Story Bible."""
        story = self.story_repository.load()
        if story is None:
            raise StoryNotFoundError("No play has been started yet.")
        return story

    def _get_cast(self) -> Cast:
        """Return the saved cast whose characters appear in the scenes."""
        cast = self.cast_repository.load()
        if cast is None or not cast.characters:
            raise CastNotFoundError("No cast has been generated yet.")
        return cast


def require_open_act(story: StoryBible, number: int) -> Act:
    """Return the act once the acts are approved and the text of the act before it is approved."""
    if not story.acts_approved:
        raise StoryOrderError("Approve the acts before working on their scenes.")
    act = find_act(story, number)
    if number > 1 and find_act(story, number - 1).status != "text_approved":
        raise StoryOrderError(f"Approve the text of Act {number - 1} before working on Act {number}.")
    return act


def _require_structure_draft(story: StoryBible, number: int) -> Act:
    """Return the act while its structure can still be changed."""
    act = require_open_act(story, number)
    if act.status != "draft":
        raise StoryOrderError(f"The structure of Act {number} is already approved.")
    return act


def _require_structure_approved(story: StoryBible, number: int) -> Act:
    """Return the act once its structure is approved, so its scenes can be planned."""
    act = require_open_act(story, number)
    if act.status == "draft":
        raise StoryOrderError(f"Approve the structure of Act {number} first.")
    return act


def _require_scenes_open(story: StoryBible, number: int) -> Act:
    """Return the act while its scenes can be planned and changed: the structure is approved, the text is not.

    An approved text is final: the characters' histories and the next act are built from it.
    """
    act = _require_structure_approved(story, number)
    if act.status == "text_approved":
        raise StoryOrderError(f"The text of Act {number} is approved, so its scenes can no longer be changed.")
    return act


def _reopen(act: Act, scene: Scene) -> None:
    """Make the scene a draft again; then the act's scenes are no longer all approved."""
    scene.status = "draft"
    act.status = "structure_approved"


def find_scene(act: Act, scene_number: int) -> Scene:
    """Return the scene with the given number."""
    for scene in act.scenes:
        if scene.number == scene_number:
            return scene
    raise SceneNotFoundError(f"Scene {scene_number} is not in Act {act.number}.")


def find_place(story: StoryBible, place_id: str) -> Place:
    """Return the place with the given id."""
    for place in story.places:
        if place.id == place_id:
            return place
    raise PlaceNotFoundError(f"Place {place_id} is not in the Story Bible.")


def on_stage_profiles(cast: Cast, scene: Scene, act_number: int) -> list[dict]:
    """Return the profiles of the characters on stage with what changed for them before this scene."""
    return [
        character.model_dump(include=PLAN_CHARACTER_FIELDS) | {
            "history": [
                entry.change for entry in character.history
                if (entry.act_number, entry.scene_number) < (act_number, scene.number)
            ],
        }
        for character in cast.characters
        if character.id in scene.character_ids
    ]


def act_thread(number: int) -> str:
    """Return the id of the conversation of an act page."""
    return f"act-{number}"


def _json(value: object) -> str:
    """Write a value as indented JSON that keeps non-ASCII letters."""
    return json.dumps(value, ensure_ascii=False, indent=2)
