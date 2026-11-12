import re

from anton.domain.models import BlockKind, ScriptBlock


# The same rule as the parser of the frontend (features/story/model/script.ts): "NAME (note): text".
SPEECH_PATTERN = re.compile(r"^([^():\n]+?)\s*(?:\(([^)]*)\))?\s*:\s*([\s\S]*)$")
BLOCK_SEPARATOR = re.compile(r"\n\s*\n")


def parse_script_blocks(text: str) -> list[ScriptBlock]:
    """Split a scene text into speeches, stage directions and plain blocks.

    Blocks are separated by an empty line; empty blocks are dropped.
    """
    blocks = []
    for raw_block in BLOCK_SEPARATOR.split(text):
        block_text = raw_block.strip()
        if not block_text:
            continue
        blocks.append(_parse_block(block_text))
    return blocks


def _parse_block(block_text: str) -> ScriptBlock:
    """Read one stripped block: a stage direction, a speech or, when it is neither, plain text."""
    if block_text.startswith("(") and block_text.endswith(")"):
        direction = block_text[1:-1].strip()
        return ScriptBlock(kind=BlockKind.DIRECTION, speaker="", note="", text=direction)

    match = SPEECH_PATTERN.match(block_text)
    if match is None:
        return ScriptBlock(kind=BlockKind.PLAIN, speaker="", note="", text=block_text)

    speaker = match.group(1)
    # A speaker is written in capitals, so "Later: ..." is not a speech.
    if speaker != speaker.upper() or not _has_letter(speaker):
        return ScriptBlock(kind=BlockKind.PLAIN, speaker="", note="", text=block_text)

    note = match.group(2) or ""
    return ScriptBlock(
        kind=BlockKind.SPEECH, speaker=speaker.strip(), note=note.strip(), text=match.group(3).strip(),
    )


def _has_letter(text: str) -> bool:
    """Tell whether the text has at least one letter."""
    for character in text:
        if character.isalpha():
            return True
    return False
