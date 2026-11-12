from unittest import TestCase

from anton.application.mappers.script_parser import parse_script_blocks
from anton.domain.models import BlockKind


class ParseScriptBlocksTest(TestCase):
    """Test splitting a scene text into speeches, stage directions and plain blocks."""

    def test_parse_script_blocks_speech_without_note_returns_speech(self) -> None:
        """Read 'NAME: text' as a speech with an empty note."""
        blocks = parse_script_blocks("ELIAS: The light is out.")

        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].kind, BlockKind.SPEECH)
        self.assertEqual(blocks[0].speaker, "ELIAS")
        self.assertEqual(blocks[0].note, "")
        self.assertEqual(blocks[0].text, "The light is out.")

    def test_parse_script_blocks_speech_with_note_returns_note(self) -> None:
        """Read 'NAME (note): text' as a speech with its note."""
        blocks = parse_script_blocks("MARGIT (quietly): Sell it.")

        self.assertEqual(blocks[0].kind, BlockKind.SPEECH)
        self.assertEqual(blocks[0].speaker, "MARGIT")
        self.assertEqual(blocks[0].note, "quietly")
        self.assertEqual(blocks[0].text, "Sell it.")

    def test_parse_script_blocks_parentheses_returns_direction(self) -> None:
        """Read a block in parentheses as a stage direction without the parentheses."""
        blocks = parse_script_blocks("(Elias crosses to the window.)")

        self.assertEqual(blocks[0].kind, BlockKind.DIRECTION)
        self.assertEqual(blocks[0].text, "Elias crosses to the window.")

    def test_parse_script_blocks_text_without_speaker_returns_plain(self) -> None:
        """Keep any other text as a plain block."""
        blocks = parse_script_blocks("Just some words without a speaker.")

        self.assertEqual(blocks[0].kind, BlockKind.PLAIN)
        self.assertEqual(blocks[0].text, "Just some words without a speaker.")

    def test_parse_script_blocks_lower_case_name_returns_plain(self) -> None:
        """Do not take 'Later: ...' for a speech, because a speaker is written in capitals."""
        blocks = parse_script_blocks("Later: they meet again.")

        self.assertEqual(blocks[0].kind, BlockKind.PLAIN)
        self.assertEqual(blocks[0].text, "Later: they meet again.")

    def test_parse_script_blocks_extra_empty_lines_are_skipped(self) -> None:
        """Split on empty lines of any length and drop empty blocks."""
        blocks = parse_script_blocks("\n\n ELIAS: One.\n\n\n\n(Pause)\n \n  \nMARGIT: Two.\n\n")

        self.assertEqual([block.kind for block in blocks], [BlockKind.SPEECH, BlockKind.DIRECTION, BlockKind.SPEECH])

    def test_parse_script_blocks_empty_text_returns_no_blocks(self) -> None:
        """Return nothing for a text with no blocks."""
        self.assertEqual(parse_script_blocks("  \n\n "), [])
