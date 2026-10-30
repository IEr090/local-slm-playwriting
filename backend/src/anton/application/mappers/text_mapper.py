import re
from difflib import SequenceMatcher

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


# Two speeches this similar say the same thing, only in slightly other words.
SAME_SPEECH = 0.85


def repeated_lines(lines: list[GeneratedLine]) -> int:
    """Count the lines that repeat an earlier line, word for word or nearly so."""
    texts = [_normalize_line(line.text) for line in lines]
    return sum(
        any(_same_speech(text, earlier) for earlier in texts[:index])
        for index, text in enumerate(texts)
        if text
    )


def _same_speech(a: str, b: str) -> bool:
    """Tell whether two speeches say the same: nearly the same words, or one only adds a word to the other."""
    if a == b:
        return True
    shorter, longer = sorted((a, b), key=len)
    return len(shorter) >= 8 and (shorter in longer and len(longer) - len(shorter) <= 12 or SequenceMatcher(None, a, b).ratio() >= SAME_SPEECH)


# A five-word phrase in three speeches is a character saying the same thing over and over.
LOOP_PHRASE_WORDS = 5
LOOP_PHRASE_LINES = 3


def looping_phrases(lines: list[GeneratedLine]) -> list[str]:
    """Return the phrases that come back in several speeches of a scene."""
    counts: dict[str, int] = {}
    for line in lines:
        for phrase in _line_phrases(line.text):
            counts[phrase] = counts.get(phrase, 0) + 1
    return [phrase for phrase, count in counts.items() if count >= LOOP_PHRASE_LINES]


def narrated_lines(lines: list[GeneratedLine], characters: list[dict]) -> int:
    """Count the speeches in which a character tells about themselves by name, like a plan, instead of speaking."""
    count = 0
    for line in lines:
        speaker = _normalize_line(line.character)
        if not speaker:
            continue
        text = _normalize_line(line.text)
        names = {_normalize_line(c.get("name", "")) for c in characters if _normalize_line(c.get("name", "")) in speaker} - {""}
        count += any(text.startswith(f"{name} ") or text.startswith(f"{name},") for name in names | {speaker})
    return count


def without_repeats(lines: list[GeneratedLine]) -> list[GeneratedLine]:
    """Drop the lines that repeat an earlier line, or bring back a phrase two earlier speeches already said."""
    kept: list[GeneratedLine] = []
    phrase_counts: dict[str, int] = {}
    for line in lines:
        text = _normalize_line(line.text)
        phrases = _line_phrases(line.text)
        repeats = any(_same_speech(text, _normalize_line(earlier.text)) for earlier in kept if text)
        loops = any(phrase_counts.get(phrase, 0) >= LOOP_PHRASE_LINES - 1 for phrase in phrases)
        if repeats or loops:
            continue
        kept.append(line)
        for phrase in phrases:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
    return kept


def _line_phrases(text: str) -> set[str]:
    """Return the five-word phrases of a speech."""
    words = re.findall(r"\w+", text.casefold())
    return {" ".join(words[i:i + LOOP_PHRASE_WORDS]) for i in range(len(words) - LOOP_PHRASE_WORDS + 1)}


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
