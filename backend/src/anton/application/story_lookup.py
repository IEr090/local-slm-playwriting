import logging

from anton.domain.models import Act, Cast, Place, Scene, StoryBible
from anton.errors import ActNotFoundError, CastNotFoundError, PlaceNotFoundError, SceneNotFoundError, StoryNotFoundError
from anton.infrastructure.storage import CastRepository, StoryRepository


logger = logging.getLogger(__name__)


def load_story(story_repository: StoryRepository) -> StoryBible:
    """Return the saved Story Bible."""
    story = story_repository.load()
    if story is None:
        logger.warning("Story Bible is missing")
        raise StoryNotFoundError("No play has been started yet.")
    return story


def load_cast(cast_repository: CastRepository) -> Cast:
    """Return the saved cast, which every step of the Story Bible builds on."""
    cast = cast_repository.load()
    if cast is None or not cast.characters:
        logger.warning("Cast is missing or has no characters")
        raise CastNotFoundError("No cast has been generated yet.")
    return cast


def find_act(story: StoryBible, number: int) -> Act:
    """Return the act with the given number."""
    for act in story.acts:
        if act.number == number:
            return act
    logger.warning("Act is missing act_number=%s", number)
    raise ActNotFoundError(f"Act {number} is not in the Story Bible.")


def find_scene(act: Act, scene_number: int) -> Scene:
    """Return the scene with the given number."""
    for scene in act.scenes:
        if scene.number == scene_number:
            return scene
    logger.warning("Scene is missing act_number=%s scene_number=%s", act.number, scene_number)
    raise SceneNotFoundError(f"Scene {scene_number} is not in Act {act.number}.")


def find_place(story: StoryBible, place_id: str) -> Place:
    """Return the place with the given id."""
    for place in story.places:
        if place.id == place_id:
            return place
    logger.warning("Place is missing place_id=%s", place_id)
    raise PlaceNotFoundError(f"Place {place_id} is not in the Story Bible.")
