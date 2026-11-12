from io import BytesIO
from unittest import TestCase

from fastapi.testclient import TestClient
from pypdf import PdfReader

from anton.api.content_disposition import attachment_header
from anton.api.dependencies import get_play_service
from anton.application.mappers.document_mapper import to_play_document
from anton.domain.models import Play, PlayAct, PlayCastMember, PlayScene
from anton.errors import PdfRenderError, StoryOrderError
from anton.infrastructure.pdf import TypstRenderer
from anton.main import app
from tests.unit.test_document_mapper import make_play
from tests.unit.test_play import make_complete_story, make_service


MARKUP_TEXT = "ELIAS: Say #hello *bold* _it_ $x$ [a] @b <c> & back\\slash `raw` // 100%."


class PdfExportServiceTest(TestCase):
    """Test the service method that exports the play with a fake renderer."""

    def test_export_pdf_before_complete_raises_story_order_error(self) -> None:
        """Reject the export while an act text is not approved."""
        service, _, _ = make_service(make_complete_story(status="scenes_approved"))

        with self.assertRaises(StoryOrderError):
            service.export_pdf()

    def test_export_pdf_returns_file_name_and_renderer_bytes(self) -> None:
        """Name the file after the play title and return the bytes of the renderer."""
        service, _, _ = make_service()

        file_name, pdf_bytes = service.export_pdf()

        self.assertEqual(file_name, "The Salt House.pdf")
        self.assertEqual(pdf_bytes, b"%PDF-fake")

    def test_export_pdf_renders_the_saved_text(self) -> None:
        """Typeset the text after the corrections made on the page of the whole play."""
        service, _, _ = make_service()
        service.edit_scene_text(1, 1, "ELIAS: Corrected.")

        service.export_pdf()

        document = service.pdf_renderer.documents[0]
        self.assertEqual(document.acts[0].scenes[0].blocks[0].text, "Corrected.")


class PdfExportRouteTest(TestCase):
    """Test the endpoint that downloads the play as a PDF."""

    def tearDown(self) -> None:
        """Remove the dependency override."""
        app.dependency_overrides.clear()

    def use_service(self, status: str):
        """Serve the endpoint with a service over an in-memory play and return the service."""
        service, _, _ = make_service(make_complete_story(status=status))
        app.dependency_overrides[get_play_service] = lambda: service
        return service

    def test_get_pdf_before_complete_returns_409(self) -> None:
        """Answer 409 while the play is not complete."""
        self.use_service("scenes_approved")

        response = TestClient(app).get("/api/story/play/pdf")

        self.assertEqual(response.status_code, 409)
        self.assertIn("message", response.json())

    def test_get_pdf_returns_attachment_with_renderer_bytes(self) -> None:
        """Answer the bytes of the renderer as a PDF download named after the play."""
        self.use_service("text_approved")

        response = TestClient(app).get("/api/story/play/pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertEqual(
            response.headers["content-disposition"],
            "attachment; filename=\"The Salt House.pdf\"; filename*=UTF-8''The%20Salt%20House.pdf",
        )
        self.assertEqual(response.content, b"%PDF-fake")

    def test_get_pdf_render_error_returns_500_with_message(self) -> None:
        """Answer 500 in the usual error format when Typst fails."""
        service = self.use_service("text_approved")
        service.pdf_renderer = RaisingRenderer()

        response = TestClient(app, raise_server_exceptions=False).get("/api/story/play/pdf")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(set(response.json()), {"message", "detail"})


class RaisingRenderer:
    """Fail like a renderer whose compiler rejected the template."""

    def render(self, document) -> bytes:
        """Raise the render error."""
        raise PdfRenderError("Typst could not compile the play: broken")


class AttachmentHeaderTest(TestCase):
    """Test the Content-Disposition value of a download."""

    def test_attachment_header_non_ascii_name_has_utf8_form(self) -> None:
        """Give an ASCII fallback and the RFC 5987 form for a title in Cyrillic."""
        header = attachment_header("Соляной дом.pdf")

        self.assertEqual(header, "attachment; filename=\"play.pdf\"; filename*=UTF-8''%D0%A1%D0%BE%D0%BB%D1%8F%D0%BD%D0%BE%D0%B9%20%D0%B4%D0%BE%D0%BC.pdf")


def read_pdf(pdf_bytes: bytes) -> PdfReader:
    """Open PDF bytes with pypdf."""
    return PdfReader(BytesIO(pdf_bytes))


class TypstRendererTest(TestCase):
    """Test the real Typst compiler on a small play."""

    def render(self, play: Play) -> bytes:
        """Typeset the play."""
        return TypstRenderer().render(to_play_document(play))

    def test_render_returns_pdf_with_title_page_cast_and_one_page_per_act(self) -> None:
        """Make a PDF of at least four pages: the title, Dramatis Personae and two acts."""
        pdf_bytes = self.render(make_play())

        reader = read_pdf(pdf_bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreaterEqual(len(reader.pages), 4)
        self.assertEqual(reader.metadata.title, "The Salt House")
        self.assertIn("The Salt House", reader.pages[0].extract_text())

    def test_render_markup_characters_come_out_as_written(self) -> None:
        """Compile a text full of Typst markup characters and find them unchanged in the PDF."""
        play = make_play()
        play.acts[0].scenes[0].text = MARKUP_TEXT

        reader = read_pdf(self.render(play))

        text = " ".join(page.extract_text() for page in reader.pages)
        expected = "Say #hello *bold* _it_ $x$ [a] @b <c> & back\\slash `raw` // 100%."
        self.assertIn(expected, " ".join(text.split()))

    def test_render_cyrillic_title_and_text_compile(self) -> None:
        """Compile a play in Russian."""
        play = Play(
            title="Соляной дом", genre="драма", premise="Жадность отнимает то, что она хочет сохранить.",
            time_and_world="Остров, 1920-е.", act_count=1,
            cast=[PlayCastMember(character_id="a", name="ЭЛИАС", description="Смотритель маяка")],
            acts=[PlayAct(number=1, scenes=[PlayScene(number=1, place_name="Кухня", place_notes="", text="ЭЛИАС: Свет погас.")])],
        )

        reader = read_pdf(self.render(play))

        self.assertIn("Соляной дом", reader.pages[0].extract_text())
