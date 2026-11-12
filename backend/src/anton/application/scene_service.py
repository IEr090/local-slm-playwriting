import json
import logging
from uuid import uuid4

from pydantic import BaseModel

from anton.application.agents.act_chat import ActChat, act_thread
from anton.application.agents.chat_edit_agent import ChatEditAgent, ChatMessage
from anton.application.agents.scene_targets import SceneBoard
from anton.application.language import play_language
from anton.application.mappers.cast_mapper import ACT_CAST_FIELDS, cast_json, on_stage_profiles
from anton.application.mappers.scene_mapper import add_new_places, full_name, to_scene_plans, to_scene_views, to_scenes
from anton.application.scene_planner import ScenePlanner
from anton.application.story_lookup import find_place, find_scene, load_cast, load_story
from anton.application.validators.story_order import (
    require_scenes_open,
    require_structure_approved,
    require_structure_draft,
)
from anton.domain.models import Act, Place, PlaceDraft, Scene, ScenePlan, StoryBible
from anton.errors import CharacterNotFoundError, PlaceNotFoundError, StoryOrderError
from anton.infrastructure.storage import CastRepository, StoryRepository


logger = logging.getLogger(__name__)

OUTLINE_FIELDS = {"premise", "genre", "tone", "time_and_world", "central_conflict"}


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
        act_chat: ActChat,
        planner: ScenePlanner,
    ) -> None:
        """Initialize the service with its repositories, the chat of the act page and the scene planner."""
        self.story_repository = story_repository
        self.cast_repository = cast_repository
        self.chat = act_chat
        self.planner = planner

    def get_places(self) -> list[Place]:
        """Return all places of the play."""
        logger.debug("Reading places")
        return load_story(self.story_repository).places

    def create_place(self, draft: PlaceDraft) -> Place:
        """Add a place the user created by hand to the places of the play."""
        logger.debug("Creating place")
        story = load_story(self.story_repository)
        place = Place(id=str(uuid4()), **draft.model_dump())
        story.places.append(place)
        self.story_repository.save(story)
        logger.info("Saved created place place_id=%s", place.id)
        return place

    async def generate_structure(self, number: int) -> StoryBible:
        """Propose the scenes of an act, picking existing places or proposing new ones; starts the act's chat anew."""
        logger.debug("Generating structure act_number=%s", number)
        story = load_story(self.story_repository)
        act = require_structure_draft(story, number)
        cast = load_cast(self.cast_repository)

        earlier_acts = []
        for earlier_act in story.acts:
            if earlier_act.number < number:
                earlier_acts.append(earlier_act.model_dump(include={"number", "summary"}))
        places = []
        for place in story.places:
            places.append(place.model_dump(include={"name", "description"}))

        board = await self.chat.structure.generate(act_thread(number), {
            "outline": story.outline.model_dump_json(include=OUTLINE_FIELDS, indent=2),
            "act": act.model_dump_json(include={"number", "dramatic_function", "summary"}, indent=2),
            "earlier_acts": _json(earlier_acts),
            "places": _json(places),
            "cast": cast_json(cast, ACT_CAST_FIELDS),
            "language": play_language(story.user_input),
        })

        # Another request may have saved the Story Bible while the structure was generated.
        story = load_story(self.story_repository)
        act = require_structure_draft(story, number)
        story.places = add_new_places(board, story.places)
        act.scenes = to_scenes(to_scene_plans(board.scenes, story.places, cast.characters))
        act.scenes_built_from_summary = act.summary
        self.story_repository.save(story)
        logger.info("Saved generated structure act_number=%s scene_count=%s", number, len(act.scenes))
        return story

    def edit_structure(self, number: int, plans: list[ScenePlan]) -> StoryBible:
        """Replace the scenes of the structure with the list the user reordered, cut or extended by hand."""
        logger.debug("Editing structure act_number=%s scene_count=%s", number, len(plans))
        story = load_story(self.story_repository)
        act = require_structure_draft(story, number)
        self._check_references(story, plans)
        act.scenes = to_scenes(plans)
        self.story_repository.save(story)
        logger.info("Saved edited structure act_number=%s", number)
        return story

    async def revise_structure(self, number: int, plans: list[ScenePlan], message: str) -> SceneRevision:
        """Send the user's message with the scenes from their form to the act agent; only new places are saved."""
        logger.debug("Revising structure act_number=%s message_length=%s", number, len(message))
        story = load_story(self.story_repository)
        act = require_structure_draft(story, number)
        return await self._revise(self.chat.structure, story, act, plans, message)

    def approve_structure(self, number: int) -> StoryBible:
        """Approve the list of scenes, so their plans can be written one by one."""
        logger.debug("Approving structure act_number=%s", number)
        story = load_story(self.story_repository)
        act = require_structure_draft(story, number)
        if not act.scenes:
            logger.warning("Structure has no scenes act_number=%s", number)
            raise StoryOrderError(f"Act {number} has no scenes yet.")
        if any(not scene.place_id for scene in act.scenes):
            logger.warning("Structure has scenes without a place act_number=%s", number)
            raise StoryOrderError("Every scene needs a place before the structure can be approved.")
        act.status = "structure_approved"
        self.story_repository.save(story)
        logger.info("Approved structure act_number=%s", number)
        return story

    async def plan_scene(self, number: int, scene_number: int) -> StoryBible:
        """Write the detailed plan of a scene once the scene before it is approved."""
        logger.debug("Planning scene act_number=%s scene_number=%s", number, scene_number)
        story = load_story(self.story_repository)
        act, scene = self._get_scene_to_plan(story, number, scene_number)
        cast = load_cast(self.cast_repository)
        views = to_scene_views(act.scenes, story.places, cast.characters)
        place = find_place(story, scene.place_id)

        generated = await self.planner.plan(
            act_summary=act.summary,
            earlier_scenes=views[:scene_number - 1],
            scene=views[scene_number - 1],
            place=place.model_dump(include={"name", "description"}),
            characters=on_stage_profiles(cast, scene, number),
            language=play_language(story.user_input),
            scenes_in_act=len(act.scenes),
        )

        story = load_story(self.story_repository)
        act, scene = self._get_scene_to_plan(story, number, scene_number)
        scene.place_notes = generated.place_notes
        scene.what_happens = generated.what_happens
        scene.planned = True
        scene.plan_built_from = [item.to_plan() for item in act.scenes[:scene_number - 1]]
        self.story_repository.save(story)
        logger.info("Saved scene plan act_number=%s scene_number=%s", number, scene_number)
        return story

    def edit_scene(self, number: int, scene_number: int, plan: ScenePlan) -> StoryBible:
        """Replace the plan of a scene with the one the user edited by hand; the scene has to be approved again."""
        logger.debug("Editing scene act_number=%s scene_number=%s", number, scene_number)
        story = load_story(self.story_repository)
        act = require_scenes_open(story, number)
        scene = find_scene(act, scene_number)
        self._check_references(story, [plan])
        scene.place_id = plan.place_id
        scene.place_notes = plan.place_notes
        scene.character_ids = plan.character_ids
        scene.what_happens = plan.what_happens
        _reopen(act, scene)
        self.story_repository.save(story)
        logger.info("Saved edited scene act_number=%s scene_number=%s", number, scene_number)
        return story

    async def revise_scenes(self, number: int, plans: list[ScenePlan], message: str) -> SceneRevision:
        """Send the user's message with the scene plans from their form to the act agent; only new places are saved."""
        logger.debug("Revising scenes act_number=%s message_length=%s", number, len(message))
        story = load_story(self.story_repository)
        act = require_scenes_open(story, number)
        return await self._revise(self.chat.scenes, story, act, plans, message)

    def approve_scene(self, number: int, scene_number: int) -> StoryBible:
        """Approve the plan of a scene; when the last scene is approved, the act's scenes are approved."""
        logger.debug("Approving scene act_number=%s scene_number=%s", number, scene_number)
        story = load_story(self.story_repository)
        act = require_scenes_open(story, number)
        scene = find_scene(act, scene_number)
        if not scene.planned:
            logger.warning("Scene has no plan act_number=%s scene_number=%s", number, scene_number)
            raise StoryOrderError(f"Scene {scene_number} has no plan yet.")
        scene.status = "approved"
        if act.status == "structure_approved" and all(item.status == "approved" for item in act.scenes):
            act.status = "scenes_approved"
        self.story_repository.save(story)
        logger.info("Approved scene act_number=%s scene_number=%s", number, scene_number)
        return story

    def reopen_scene(self, number: int, scene_number: int) -> StoryBible:
        """Take back the approval of a scene, so it can be changed again."""
        logger.debug("Reopening scene act_number=%s scene_number=%s", number, scene_number)
        story = load_story(self.story_repository)
        act = require_scenes_open(story, number)
        _reopen(act, find_scene(act, scene_number))
        self.story_repository.save(story)
        logger.info("Reopened scene act_number=%s scene_number=%s", number, scene_number)
        return story

    async def act_chat(self, number: int) -> list[ChatMessage]:
        """Return the chat history of the act page."""
        logger.debug("Reading act chat act_number=%s", number)
        return await self.chat.history(number)

    async def _revise(
        self, agent: ChatEditAgent[SceneBoard], story: StoryBible, act: Act, plans: list[ScenePlan], message: str,
    ) -> SceneRevision:
        """Let the agent answer about the scenes, save the places it proposed and turn names back into ids."""
        self._check_references(story, plans)
        cast = load_cast(self.cast_repository)
        board = SceneBoard(scenes=to_scene_views(plans, story.places, cast.characters))

        result = await agent.send(act_thread(act.number), board, message, context={
            "act_summary": act.summary,
            "places": [place.model_dump(include={"name", "description"}) for place in story.places],
            "characters": [full_name(character) for character in cast.characters],
        })

        story = load_story(self.story_repository)
        old_place_count = len(story.places)
        places = add_new_places(result.data, story.places)
        if len(places) != len(story.places):
            story.places = places
            self.story_repository.save(story)
            logger.info("Saved new places from revision new_place_count=%s", len(places) - old_place_count)
        return SceneRevision(
            reply=result.reply,
            scenes=to_scene_plans(result.data.scenes, places, cast.characters),
            places=places,
        )

    def _get_scene_to_plan(self, story: StoryBible, number: int, scene_number: int) -> tuple[Act, Scene]:
        """Return the act and the scene to plan and make sure the scene before it is approved."""
        act = require_scenes_open(story, number)
        scene = find_scene(act, scene_number)
        if scene.status == "approved":
            logger.warning("Scene is approved act_number=%s scene_number=%s", number, scene_number)
            raise StoryOrderError(f"Scene {scene_number} is approved. Reopen it to plan it again.")
        if scene_number > 1 and act.scenes[scene_number - 2].status != "approved":
            logger.warning("Previous scene is not approved act_number=%s scene_number=%s", number, scene_number)
            raise StoryOrderError(f"Approve scene {scene_number - 1} before planning scene {scene_number}.")
        return act, scene

    def _check_references(self, story: StoryBible, plans: list[ScenePlan]) -> None:
        """Reject scenes that name a place or a character the play does not have; an empty place is allowed."""
        place_ids = {place.id for place in story.places}
        character_ids = {character.id for character in load_cast(self.cast_repository).characters}
        for plan in plans:
            if plan.place_id and plan.place_id not in place_ids:
                logger.warning("Plan names an unknown place place_id=%s", plan.place_id)
                raise PlaceNotFoundError(f"Place {plan.place_id} is not in the Story Bible.")
            for character_id in plan.character_ids:
                if character_id not in character_ids:
                    logger.warning("Plan names an unknown character character_id=%s", character_id)
                    raise CharacterNotFoundError(f"Character {character_id} is not in the saved cast.")


def _reopen(act: Act, scene: Scene) -> None:
    """Make the scene a draft again; then the act's scenes are no longer all approved."""
    scene.status = "draft"
    act.status = "structure_approved"


def _json(value: object) -> str:
    """Write a value as indented JSON that keeps non-ASCII letters."""
    return json.dumps(value, ensure_ascii=False, indent=2)
