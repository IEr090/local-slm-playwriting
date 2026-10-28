from anton.application.llm_schemas.text_generation import GeneratedHistory, GeneratedLine
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
