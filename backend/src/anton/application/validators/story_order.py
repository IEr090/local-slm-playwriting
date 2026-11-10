import logging

from anton.application.story_lookup import find_act
from anton.domain.models import Act, StoryBible
from anton.errors import StoryOrderError


logger = logging.getLogger(__name__)


def require_outline_open(story: StoryBible) -> None:
    """Reject writing the outline again once the acts are built from it; until then it can be written anew."""
    if story.acts:
        logger.warning("Outline is locked because acts are built from it")
        raise StoryOrderError(
            "The acts are already built from the outline. Edit the outline or ask the agent to revise it."
        )


def require_acts_not_approved(story: StoryBible) -> None:
    """Reject generating the acts again once they are approved; then they can only be edited."""
    if story.acts_approved:
        logger.warning("Acts are already approved")
        raise StoryOrderError("The acts are already approved. Edit them instead.")


def require_open_act(story: StoryBible, number: int) -> Act:
    """Return the act once the acts are approved and the text of the act before it is approved."""
    if not story.acts_approved:
        logger.warning("Acts are not approved act_number=%s", number)
        raise StoryOrderError("Approve the acts before working on their scenes.")
    act = find_act(story, number)
    if number > 1 and find_act(story, number - 1).status != "text_approved":
        logger.warning("Previous act text is not approved act_number=%s", number)
        raise StoryOrderError(f"Approve the text of Act {number - 1} before working on Act {number}.")
    return act


def require_structure_draft(story: StoryBible, number: int) -> Act:
    """Return the act while its structure can still be changed."""
    act = require_open_act(story, number)
    if act.status != "draft":
        logger.warning("Structure is already approved act_number=%s", number)
        raise StoryOrderError(f"The structure of Act {number} is already approved.")
    return act


def require_structure_approved(story: StoryBible, number: int) -> Act:
    """Return the act once its structure is approved, so its scenes can be planned."""
    act = require_open_act(story, number)
    if act.status == "draft":
        logger.warning("Structure is not approved act_number=%s", number)
        raise StoryOrderError(f"Approve the structure of Act {number} first.")
    return act


def require_scenes_open(story: StoryBible, number: int) -> Act:
    """Return the act while its scenes can be planned and changed: the structure is approved, the text is not.

    An approved text is final: the characters' histories and the next act are built from it.
    """
    act = require_structure_approved(story, number)
    if act.status == "text_approved":
        logger.warning("Text is approved, scenes are locked act_number=%s", number)
        raise StoryOrderError(f"The text of Act {number} is approved, so its scenes can no longer be changed.")
    return act


def require_scenes_approved(story: StoryBible, number: int) -> Act:
    """Return the act once every scene of it is approved, so its text can be written."""
    act = require_open_act(story, number)
    if act.status == "text_approved":
        logger.warning("Text is already approved act_number=%s", number)
        raise StoryOrderError(f"The text of Act {number} is already approved. Change its scenes to write it again.")
    if act.status != "scenes_approved":
        logger.warning("Scenes are not approved act_number=%s", number)
        raise StoryOrderError(f"Approve every scene of Act {number} before writing its text.")
    return act


def require_text_draft(story: StoryBible, number: int) -> Act:
    """Return the act while its text is written but not approved yet."""
    act = require_scenes_approved(story, number)
    if not act.scene_texts:
        logger.warning("Text is not written act_number=%s", number)
        raise StoryOrderError(f"The text of Act {number} has not been written yet.")
    return act
