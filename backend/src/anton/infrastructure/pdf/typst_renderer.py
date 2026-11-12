import logging
from pathlib import Path

import typst

from anton.domain.models import PlayDocument
from anton.errors import PdfRenderError


logger = logging.getLogger(__name__)

PACKAGE_DIRECTORY = Path(__file__).parent
TEMPLATE_PATH = PACKAGE_DIRECTORY / "play.typ"
FONTS_DIRECTORY = PACKAGE_DIRECTORY / "fonts"
# The template reads the play from this system input, as JSON.
PLAY_INPUT_NAME = "play"


class TypstRenderer:
    """Typeset the play into an A4 PDF with the Typst compiler that comes with the typst package."""

    def render(self, document: PlayDocument) -> bytes:
        """Compile the template with the play as JSON and return the PDF bytes; nothing is written to disk.

        Raises:
            PdfRenderError: If Typst cannot compile the template.
        """
        logger.debug("Compiling the play to PDF title=%s", document.title)
        play_json = document.model_dump_json()
        try:
            pdf_bytes = typst.compile(
                TEMPLATE_PATH,
                font_paths=[FONTS_DIRECTORY],
                # Only the bundled fonts are used, so the result is the same on every machine.
                ignore_system_fonts=True,
                sys_inputs={PLAY_INPUT_NAME: play_json},
                format="pdf",
            )
        except Exception as error:
            logger.error("Typst could not compile the play error=%s", error)
            raise PdfRenderError(f"Typst could not compile the play: {error}") from error

        logger.info("Compiled the play to PDF title=%s size=%s", document.title, len(pdf_bytes))
        return pdf_bytes
