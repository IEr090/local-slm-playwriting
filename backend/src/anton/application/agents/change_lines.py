import re

from anton.application.llm_schemas.text_generation import GeneratedLine


def field_values(changes: str, fields: set[str], prefix: str = "") -> dict[str, dict[str, str]]:
    """Read agreed changes written one field per line, e.g. `tone: Darker.` or `act 2 summary: ...`.

    `prefix` is "act" or "scene" for lines that name the act or scene first; the result is keyed by its number
    ("" without a prefix). A value may go on over several lines until the next field line.
    """
    head = rf"^\s*{prefix}\s+(\d+)\s*[,:]?\s*" if prefix else r"^\s*()"
    line_re = re.compile(head + r"`?(" + "|".join(map(re.escape, sorted(fields, key=len, reverse=True))) + r")`?\s*:\s*(.*)$", re.IGNORECASE)
    values: dict[str, dict[str, str]] = {}
    current: tuple[str, str] | None = None
    for line in changes.strip().splitlines():
        match = line_re.match(line)
        if match:
            number, field, value = match.groups()
            current = (number, field.lower())
            values.setdefault(number, {})[current[1]] = value.strip()
        elif current and line.strip():
            number, field = current
            values[number][field] = f"{values[number][field]}\n{line.strip()}"
    return values


# Field names as the model writes them in prose: "time and world" for `time_and_world`.
def _spoken(field: str) -> str:
    return field.replace("_", r"[ _]")


def quoted_values(text: str, fields: set[str], aliases: dict[str, str] | None = None) -> dict[str, str]:
    """Read new values from a proposal in prose, e.g. `I suggest the tone: «Darker.»` → {"tone": "Darker.", ...}.

    `aliases` maps other names of a field, e.g. in Russian, to the field: {"центральный конфликт": "central_conflict"}.
    """
    names = {_spoken(field): field for field in fields} | {re.escape(alias): field for alias, field in (aliases or {}).items()}
    pattern = "|".join(sorted(names, key=len, reverse=True))
    values = {}
    for match in re.finditer(rf"(?<!\w)({pattern})\w*(?:\s+(?:to|be|should be|will be|is|на|:)|:)?\s*{QUOTED}", text, re.IGNORECASE):
        name = match.group(1).casefold()
        field = next((f for key, f in names.items() if re.fullmatch(key, name, re.IGNORECASE)), None)
        value = next(group for group in match.groups()[1:] if group is not None)
        if field and value.strip():
            values[field] = value.strip()
    return values


# A quoted value: «…», "…", “…” or '…' (an apostrophe inside a word, as in "Elias's", does not end it).
QUOTED = r"""(?:«([^»]+)»|"([^"]+)"|“([^”]+)”|'(.+?)'(?=[\s.,;:!?)]|$))"""


NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}


def quoted_acts(text: str) -> dict[int, str]:
    """Read new act summaries from a proposal in prose, e.g. `I suggest for Act Two: «...»` → {2: "..."}."""
    acts = {}
    pattern = rf"(?:\bact\s+(\d+|one|two|three|four|five)\b|\b(first|second|third|fourth|fifth)\s+act\b)[^«\"“']{{0,25}}{QUOTED}"
    for match in re.finditer(pattern, text, re.IGNORECASE):
        word = (match.group(1) or match.group(2)).lower()
        value = next(group for group in match.groups()[2:] if group is not None)
        acts[int(word) if word.isdigit() else NUMBER_WORDS[word]] = value.strip()
    return acts


REPLACE = re.compile(r'^\s*scene\s+(\d+)\s*:?\s*replace\s+"(.+)"\s+with\s+"(.*)"\s*$', re.IGNORECASE)
SPEECH = re.compile(r"^([^():\n]+?)\s*(?:\(([^)]*)\))?\s*:\s*(.*)$")


def line_replacements(changes: str) -> list[tuple[int, str, str]]:
    """Read changes like `scene 3 replace "OLD LINE" with "NEW LINE"` as (scene number, old line, new line)."""
    replacements = []
    for line in changes.strip().splitlines():
        match = REPLACE.match(line)
        if match:
            replacements.append((int(match.group(1)), match.group(2), match.group(3)))
    return replacements


def to_line(text: str) -> GeneratedLine:
    """Turn one line in play format back into its parts: a speech `NAME (note): text` or a stage direction."""
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        return GeneratedLine(character="", parenthetical="", text=text[1:-1].strip())
    match = SPEECH.match(text)
    if match and match.group(1) == match.group(1).upper() and any(c.isalpha() for c in match.group(1)):
        return GeneratedLine(character=match.group(1).strip(), parenthetical=(match.group(2) or "").strip(), text=match.group(3).strip())
    return GeneratedLine(character="", parenthetical="", text=text)
