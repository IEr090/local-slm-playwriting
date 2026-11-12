import logging

from anton.application.file_name import pdf_file_name
from anton.application.mappers.document_mapper import to_play_document
from anton.application.mappers.play_mapper import to_play
from anton.application.story_lookup import find_act, find_scene, load_cast, load_story
from anton.application.validators.story_order import require_play_complete
from anton.domain.models import Play, StoryBible
from anton.errors import SceneNotFoundError
from anton.infrastructure.pdf import PdfRenderer
from anton.infrastructure.storage import CastRepository, StoryRepository


logger = logging.getLogger(__name__)


class PlayService:
    """Show the finished play as one read model and take the user's last corrections of its text."""

    def __init__(
        self, story_repository: StoryRepository, cast_repository: CastRepository, pdf_renderer: PdfRenderer,
    ) -> None:
        """Initialize the service with the repositories of the Story Bible and the cast and the PDF renderer."""
        self.story_repository = story_repository
        self.cast_repository = cast_repository
        self.pdf_renderer = pdf_renderer

    def get_play(self) -> Play:
        """Return the whole play once the text of every act is approved."""
        logger.debug("Reading the whole play")
        story = load_story(self.story_repository)
        require_play_complete(story)
        return self._build(story)

    def edit_scene_text(self, number: int, scene_number: int, text: str) -> Play:
        """Replace the text of one scene of the finished play and return the play.

        This is a final correction: the act statuses, the other scenes, the histories and the chats stay as they are.
        """
        logger.debug("Editing scene text of the finished play act_number=%s scene_number=%s", number, scene_number)
        story = load_story(self.story_repository)
        require_play_complete(story)
        act = find_act(story, number)
        find_scene(act, scene_number)

        scene_text = None
        for item in act.scene_texts:
            if item.scene_number == scene_number:
                scene_text = item
        if scene_text is None:
            logger.warning("Scene has no text act_number=%s scene_number=%s", number, scene_number)
            raise SceneNotFoundError(f"Scene {scene_number} has no text in Act {number}.")

        scene_text.text = text
        self.story_repository.save(story)
        logger.info("Saved scene text of the finished play act_number=%s scene_number=%s", number, scene_number)
        return self._build(story)

    def export_pdf(self) -> tuple[str, bytes]:
        """Typeset the finished play, with the texts as saved, into a PDF.

        Returns:
            The file name made from the play title and the bytes of the PDF.
        """
        logger.debug("Exporting the whole play to PDF")
        story = load_story(self.story_repository)
        require_play_complete(story)
        play = self._build(story)
        document = to_play_document(play)
        pdf_bytes = self.pdf_renderer.render(document)
        file_name = pdf_file_name(play.title)
        logger.info("Exported the play to PDF file_name=%s size=%s", file_name, len(pdf_bytes))
        return file_name, pdf_bytes

    def _build(self, story: StoryBible) -> Play:
        """Join the Story Bible with the saved cast."""
        cast = load_cast(self.cast_repository)
        return to_play(story, cast)
