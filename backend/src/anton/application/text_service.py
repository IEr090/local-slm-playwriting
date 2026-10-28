from pydantic import BaseModel

from anton.application.agents.chat_edit_agent import ChatEditAgent
from anton.application.mappers.scene_mapper import full_name, to_scene_views
from anton.application.mappers.text_mapper import ending, to_history_entries
from anton.application.scene_service import act_thread, find_place, find_scene, on_stage_profiles, require_open_act
from anton.application.scene_writer import SceneWriter
from anton.domain.models import Act, Cast, CharacterHistoryEntry, SceneText, StoryBible
from anton.errors import CastNotFoundError, SceneNotFoundError, StoryNotFoundError, StoryOrderError
from anton.infrastructure.storage import CastRepository, StoryRepository


PLAY_FIELDS = {"title", "genre", "tone", "time_and_world"}
# How many speeches and stage directions of the previous scene the next scene continues from.
ENDING_BLOCKS = 6


class TextRevision(BaseModel):
    """Represent the answer of the act agent and the scene texts as it sees them now."""

    reply: str
    scene_texts: list[SceneText]


class TextService:
    """Write the text of an act scene by scene, let the user revise it and record what it changed for the characters."""

    def __init__(
        self,
        story_repository: StoryRepository,
        cast_repository: CastRepository,
        text_agent: ChatEditAgent[list[SceneText]],
        writer: SceneWriter,
    ) -> None:
        """Initialize the service with its repositories, the text agent of the act page and the scene writer.

        The text agent shares its store of conversations with the other agents of the act page.
        """
        self.story_repository = story_repository
        self.cast_repository = cast_repository
        self.text_agent = text_agent
        self.writer = writer

    async def generate_text(self, number: int) -> StoryBible:
        """Write the text of the act scene by scene from the approved plans and store it in the act."""
        story = self._get_story()
        act = _require_scenes_approved(story, number)
        cast = self._get_cast()
        views = to_scene_views(act.scenes, story.places, cast.characters)
        previous = _previous_act_ending(story, number)

        scene_texts = []
        for scene, view in zip(act.scenes, views):
            text = await self.writer.write(
                play=story.outline.model_dump(include=PLAY_FIELDS),
                act_summary=act.summary,
                scene=view,
                place=find_place(story, scene.place_id).model_dump(include={"name", "description"}),
                characters=on_stage_profiles(cast, scene, number),
                previous_ending=previous,
            )
            scene_texts.append(SceneText(scene_number=scene.number, text=text))
            previous = ending(text, ENDING_BLOCKS)

        # Another request may have saved the Story Bible while the text was written.
        story = self._get_story()
        act = _require_scenes_approved(story, number)
        act.scene_texts = scene_texts
        act.text_built_from_scenes = [scene.to_plan() for scene in act.scenes]
        self.story_repository.save(story)
        return story

    def edit_text(self, number: int, scene_texts: list[SceneText]) -> StoryBible:
        """Save the scene texts the user took over from the chat or changed by hand."""
        story = self._get_story()
        act = _require_text_draft(story, number)
        _check_scene_numbers(act, scene_texts)
        act.scene_texts = scene_texts
        self.story_repository.save(story)
        return story

    async def revise_text(self, number: int, scene_texts: list[SceneText], message: str) -> TextRevision:
        """Send the user's message with the scene texts from their form to the act agent; nothing is saved."""
        story = self._get_story()
        act = _require_text_draft(story, number)
        _check_scene_numbers(act, scene_texts)
        result = await self.text_agent.send(act_thread(number), scene_texts, message, context={"act_summary": act.summary})
        return TextRevision(reply=result.reply, scene_texts=result.data)

    async def approve_text(self, number: int) -> StoryBible:
        """Approve the text and append what each scene changed to the histories of its characters.

        The act's old entries are removed first, so an act that was written again is not recorded twice.
        """
        story = self._get_story()
        act = _require_text_draft(story, number)
        cast = self._get_cast()

        entries: dict[str, list[CharacterHistoryEntry]] = {}
        for scene_text in act.scene_texts:
            scene = find_scene(act, scene_text.scene_number)
            names = [full_name(character) for character in cast.characters if character.id in scene.character_ids]
            generated = await self.writer.extract_history(scene_text.text, names)
            for character_id, items in to_history_entries(generated, number, scene.number, cast.characters).items():
                entries.setdefault(character_id, []).extend(items)

        cast = self._get_cast()
        for character in cast.characters:
            kept = [entry for entry in character.history if entry.act_number != number]
            character.history = sorted(
                kept + entries.get(character.id, []),
                key=lambda entry: (entry.act_number, entry.scene_number),
            )
        self.cast_repository.save(cast)

        story = self._get_story()
        act = _require_text_draft(story, number)
        act.status = "text_approved"
        self.story_repository.save(story)
        return story

    def _get_story(self) -> StoryBible:
        """Return the saved Story Bible."""
        story = self.story_repository.load()
        if story is None:
            raise StoryNotFoundError("No play has been started yet.")
        return story

    def _get_cast(self) -> Cast:
        """Return the saved cast whose characters speak in the text."""
        cast = self.cast_repository.load()
        if cast is None or not cast.characters:
            raise CastNotFoundError("No cast has been generated yet.")
        return cast


def _require_scenes_approved(story: StoryBible, number: int) -> Act:
    """Return the act once every scene of it is approved, so its text can be written."""
    act = require_open_act(story, number)
    if act.status == "text_approved":
        raise StoryOrderError(f"The text of Act {number} is already approved. Change its scenes to write it again.")
    if act.status != "scenes_approved":
        raise StoryOrderError(f"Approve every scene of Act {number} before writing its text.")
    return act


def _require_text_draft(story: StoryBible, number: int) -> Act:
    """Return the act while its text is written but not approved yet."""
    act = _require_scenes_approved(story, number)
    if not act.scene_texts:
        raise StoryOrderError(f"The text of Act {number} has not been written yet.")
    return act


def _check_scene_numbers(act: Act, scene_texts: list[SceneText]) -> None:
    """Reject texts of scenes the act's text does not have."""
    known = {item.scene_number for item in act.scene_texts}
    for scene_text in scene_texts:
        if scene_text.scene_number not in known:
            raise SceneNotFoundError(f"Scene {scene_text.scene_number} has no text in Act {act.number}.")


def _previous_act_ending(story: StoryBible, number: int) -> str:
    """Return the end of the text of the act before, so the first scene can continue from it."""
    previous = [act for act in story.acts if act.number == number - 1]
    if not previous or not previous[0].scene_texts:
        return ""
    return ending(previous[0].scene_texts[-1].text, ENDING_BLOCKS)
