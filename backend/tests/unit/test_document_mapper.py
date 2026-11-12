from unittest import TestCase

from anton.application.file_name import pdf_file_name
from anton.application.mappers.document_mapper import number_in_words, to_play_document
from anton.domain.models import BlockKind, Play, PlayAct, PlayCastMember, PlayScene


def make_play() -> Play:
    """Create a play with two acts; Act 1 has two scenes."""
    return Play(
        title="The Salt House",
        genre="drama",
        premise="Greed costs you the very thing it tries to keep.",
        time_and_world="A North Sea island.",
        act_count=2,
        cast=[PlayCastMember(character_id="elias", name="Elias Hale", description="Keeper of the light")],
        acts=[
            PlayAct(number=1, scenes=[
                PlayScene(number=1, place_name="The kitchen", place_notes="", text="ELIAS: One.\n\n(Pause)"),
                PlayScene(number=2, place_name="The landing", place_notes="", text="Later: Two."),
            ]),
            PlayAct(number=2, scenes=[PlayScene(number=1, place_name="The lamp room", place_notes="", text="ELIAS: Three.")]),
        ],
    )


class PlayDocumentMapperTest(TestCase):
    """Test building the document that is typeset from the read model of the play."""

    def test_to_play_document_copies_title_page_and_writes_act_count_in_words(self) -> None:
        """Take the title page from the play and spell the number of acts."""
        document = to_play_document(make_play())

        self.assertEqual(document.title, "The Salt House")
        self.assertEqual(document.act_count, 2)
        self.assertEqual(document.act_count_word, "two")
        self.assertEqual(document.language_code, "en")
        self.assertEqual(document.cast[0].name, "Elias Hale")

    def test_to_play_document_keeps_acts_and_scenes_in_order_with_parsed_blocks(self) -> None:
        """Keep the order of acts and scenes and parse every scene text."""
        document = to_play_document(make_play())

        self.assertEqual([act.number_word for act in document.acts], ["one", "two"])
        self.assertEqual([scene.place_name for scene in document.acts[0].scenes], ["The kitchen", "The landing"])
        first_blocks = document.acts[0].scenes[0].blocks
        self.assertEqual([block.kind for block in first_blocks], [BlockKind.SPEECH, BlockKind.DIRECTION])
        self.assertEqual(document.acts[0].scenes[1].blocks[0].kind, BlockKind.PLAIN)

    def test_to_play_document_russian_premise_returns_russian_language_code(self) -> None:
        """Take the language of the text from the premise."""
        play = make_play()
        play.premise = "Жадность отнимает то, что она хочет сохранить."

        self.assertEqual(to_play_document(play).language_code, "ru")

    def test_number_in_words_above_ten_returns_digits(self) -> None:
        """Keep the digits when there is no word for the number."""
        self.assertEqual(number_in_words(12), "12")


class PdfFileNameTest(TestCase):
    """Test making a play title safe for a file name."""

    def test_pdf_file_name_plain_title_keeps_title(self) -> None:
        """Add only the extension to a title that is safe."""
        self.assertEqual(pdf_file_name("The Salt House"), "The Salt House.pdf")

    def test_pdf_file_name_unsafe_characters_are_removed(self) -> None:
        """Replace characters a file system does not accept."""
        self.assertEqual(pdf_file_name('Who/what: "Why"?'), "Who what Why.pdf")

    def test_pdf_file_name_nothing_left_returns_fallback(self) -> None:
        """Fall back to play.pdf when the title has nothing usable."""
        self.assertEqual(pdf_file_name(' ?*: . '), "play.pdf")

    def test_pdf_file_name_keeps_non_ascii_letters(self) -> None:
        """Keep letters of any language."""
        self.assertEqual(pdf_file_name("Соляной дом"), "Соляной дом.pdf")
