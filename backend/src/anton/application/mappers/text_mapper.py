import re

from anton.application.llm_schemas.text_generation import GeneratedHistory, GeneratedLine, LineEdit
from anton.application.mappers.scene_mapper import find_character
from anton.domain.models import Character, CharacterHistoryEntry


def format_lines(lines: list[GeneratedLine]) -> str:
    """Write the lines in play format: speeches as 'NAME (note): text', stage directions in parentheses."""
    blocks = []
    for line in lines:
        text = line.text.strip()
        if not text:
            continue
        if not line.character.strip():
            blocks.append(f"({text.strip('()')})")
            continue
        note = f" ({line.parenthetical.strip().strip('()')})" if line.parenthetical.strip() else ""
        blocks.append(f"{line.character.strip().upper()}{note}: {text}")
    return "\n\n".join(blocks)


# An old line counts as found when this share of its words is in a line of the scene.
MIN_LINE_MATCH = 0.6


def apply_line_edits(text: str, edits: list[LineEdit]) -> str:
    """Put the new lines in place of the old ones; lines the edits do not name stay as they are.

    The model may copy an old line not quite exactly, so the line of the scene with the most of its words is taken.
    An old line that is not in the scene is ignored; an empty one adds the new lines at the end.
    """
    blocks = [block for block in text.split("\n\n") if block.strip()]
    for edit in edits:
        new_blocks = [block for block in format_lines(edit.new_lines).split("\n\n") if block]
        if not edit.old_line.strip():
            blocks.extend(new_blocks)
            continue
        index = _find_line(blocks, edit.old_line)
        if index is not None:
            blocks[index:index + 1] = new_blocks
    return "\n\n".join(blocks)


def _find_line(blocks: list[str], old_line: str) -> int | None:
    """Return the index of the line that is the old line, exactly or with the most of its words."""
    key = _normalize_line(old_line)
    for index, block in enumerate(blocks):
        if _normalize_line(block) == key:
            return index
    words = _words(old_line)
    if not words:
        return None
    scores = [len(words & _words(block)) / len(words) for block in blocks]
    best = max(range(len(blocks)), key=lambda index: scores[index], default=None)
    return best if best is not None and scores[best] >= MIN_LINE_MATCH else None


def _normalize_line(line: str) -> str:
    """Make lines comparable regardless of case, spaces and the parentheses of a stage direction."""
    return " ".join(line.strip().strip("()").casefold().split())


def _words(line: str) -> set[str]:
    """Return the words of a line in lower case."""
    return set(re.findall(r"\w+", line.casefold()))


def unknown_speakers(lines: list[GeneratedLine], characters: list[dict]) -> list[str]:
    """Return the speakers of the lines who are not among the characters on stage, by name, surname or both."""
    known = set()
    for character in characters:
        name, surname = character.get("name", "").strip(), character.get("surname", "").strip()
        known |= {_normalize_line(name), _normalize_line(surname), _normalize_line(f"{name} {surname}")} - {""}
    strangers: dict[str, str] = {}
    for line in lines:
        speaker = line.character.strip()
        if speaker and line.text.strip() and _normalize_line(speaker) not in known:
            strangers.setdefault(_normalize_line(speaker), speaker)
    return list(strangers.values())


def ending(text: str, blocks: int) -> str:
    """Return the last speeches and stage directions of a scene text, so the next scene can continue from them."""
    return "\n\n".join(text.split("\n\n")[-blocks:])


def to_history_entries(
    generated: GeneratedHistory, act_number: int, scene_number: int, characters: list[Character],
) -> dict[str, list[CharacterHistoryEntry]]:
    """Link every change to its act and scene and to the id of its character; unknown names are dropped."""
    entries: dict[str, list[CharacterHistoryEntry]] = {}
    for item in generated.entries:
        character_id = find_character(item.character, characters)
        change = item.change.strip()
        if character_id and change:
            entries.setdefault(character_id, []).append(
                CharacterHistoryEntry(act_number=act_number, scene_number=scene_number, change=change),
            )
    return entries
