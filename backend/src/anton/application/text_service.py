import logging

from pydantic import BaseModel

from anton.application.agents.act_chat import ActChat, act_thread
from anton.application.language import play_language
from anton.application.mappers.scene_mapper import full_name, to_scene_views
from anton.application.mappers.text_mapper import ending, to_history_entries
from anton.application.mappers.cast_mapper import on_stage_profiles
from anton.application.scene_writer import SceneWriter
from anton.application.story_lookup import find_place, find_scene, load_cast, load_story
from anton.application.validators.story_order import require_scenes_approved, require_text_draft
from anton.domain.models import Act, Cast, CharacterHistoryEntry, SceneText, StoryBible
from anton.errors import SceneNotFoundError
from anton.infrastructure.storage import CastRepository, StoryRepository


logger = logging.getLogger(__name__)

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
        act_chat: ActChat,
        writer: SceneWriter,
    ) -> None:
        """Initialize the service with its repositories, the chat of the act page and the scene writer."""
        self.story_repository = story_repository
        self.cast_repository = cast_repository
        self.chat = act_chat
        self.writer = writer

    async def generate_text(self, number: int) -> StoryBible:
        """Write the text of the act scene by scene from the approved plans and store it in the act."""
        logger.debug("Generating text act_number=%s", number)
        story = load_story(self.story_repository)
        act = require_scenes_approved(story, number)
        cast = load_cast(self.cast_repository)
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
                language=play_language(story.user_input),
            )
            scene_texts.append(SceneText(scene_number=scene.number, text=text))
            previous = ending(text, ENDING_BLOCKS)

        # Another request may have saved the Story Bible while the text was written.
        story = load_story(self.story_repository)
        act = require_scenes_approved(story, number)
        act.scene_texts = scene_texts
        act.text_built_from_scenes = [scene.to_plan() for scene in act.scenes]
        self.story_repository.save(story)
        logger.info("Saved generated text act_number=%s scene_count=%s", number, len(scene_texts))
        # The chat of the act page is about scenes and an earlier text; the new text starts it anew.
        await self.chat.forget(number)
        return story

    def edit_text(self, number: int, scene_texts: list[SceneText]) -> StoryBible:
        """Save the scene texts the user took over from the chat or changed by hand."""
        logger.debug("Editing text act_number=%s scene_count=%s", number, len(scene_texts))
        story = load_story(self.story_repository)
        act = require_text_draft(story, number)
        _check_scene_numbers(act, scene_texts)
        act.scene_texts = scene_texts
        self.story_repository.save(story)
        logger.info("Saved edited text act_number=%s", number)
        return story

    async def revise_text(self, number: int, scene_texts: list[SceneText], message: str) -> TextRevision:
        """Send the user's message with the scene texts from their form to the act agent; nothing is saved."""
        logger.debug("Revising text act_number=%s message_length=%s", number, len(message))
        story = load_story(self.story_repository)
        act = require_text_draft(story, number)
        _check_scene_numbers(act, scene_texts)
        context = {"act_summary": act.summary}
        result = await self.chat.text.send(act_thread(number), scene_texts, message, context=context)
        return TextRevision(reply=result.reply, scene_texts=result.data)

    async def approve_text(self, number: int) -> StoryBible:
        """Approve the text and append what each scene changed to the histories of its characters.

        The act's old entries are removed first, so an act that was written again is not recorded twice.
        """
        logger.debug("Approving text act_number=%s", number)
        story = load_story(self.story_repository)
        act = require_text_draft(story, number)
        cast = load_cast(self.cast_repository)

        # 1) Ask the model what every scene changed for its characters
        language = play_language(story.user_input)
        entries = await self._collect_history_entries(act, cast, language)

        # 2) Replace the act's entries in the cast; it is read again because it may have changed meanwhile
        cast = load_cast(self.cast_repository)
        self._replace_act_history(cast, number, entries)
        self.cast_repository.save(cast)
        logger.info("Saved character histories act_number=%s", number)

        # 3) Mark the text as approved
        story = load_story(self.story_repository)
        act = require_text_draft(story, number)
        act.status = "text_approved"
        self.story_repository.save(story)
        logger.info("Approved text act_number=%s", number)
        return story

    async def _collect_history_entries(
        self, act: Act, cast: Cast, language: str,
    ) -> dict[str, list[CharacterHistoryEntry]]:
        """Return the history entries of every character that the scenes of the act produced."""
        entries: dict[str, list[CharacterHistoryEntry]] = {}
        for scene_text in act.scene_texts:
            scene = find_scene(act, scene_text.scene_number)
            names = []
            for character in cast.characters:
                if character.id in scene.character_ids:
                    names.append(full_name(character))

            generated = await self.writer.extract_history(scene_text.text, names, language)
            scene_entries = to_history_entries(generated, act.number, scene.number, cast.characters)
            for character_id, items in scene_entries.items():
                entries.setdefault(character_id, []).extend(items)
        return entries

    def _replace_act_history(
        self, cast: Cast, number: int, entries: dict[str, list[CharacterHistoryEntry]],
    ) -> None:
        """Remove the old entries of the act from every character and add the new ones in story order."""
        for character in cast.characters:
            kept = []
            for entry in character.history:
                if entry.act_number != number:
                    kept.append(entry)

            history = kept + entries.get(character.id, [])
            character.history = sorted(history, key=lambda entry: (entry.act_number, entry.scene_number))


def _check_scene_numbers(act: Act, scene_texts: list[SceneText]) -> None:
    """Reject texts of scenes the act's text does not have."""
    known = {item.scene_number for item in act.scene_texts}
    for scene_text in scene_texts:
        if scene_text.scene_number not in known:
            logger.warning(
                "Text names an unknown scene act_number=%s scene_number=%s", act.number, scene_text.scene_number,
            )
            raise SceneNotFoundError(f"Scene {scene_text.scene_number} has no text in Act {act.number}.")


def _previous_act_ending(story: StoryBible, number: int) -> str:
    """Return the end of the text of the act before, so the first scene can continue from it."""
    for act in story.acts:
        if act.number != number - 1:
            continue
        if not act.scene_texts:
            return ""
        return ending(act.scene_texts[-1].text, ENDING_BLOCKS)
    return ""
