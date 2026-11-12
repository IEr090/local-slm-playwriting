import re

from anton.application.llm_schemas.text_generation import GeneratedLine


# A quoted value: «…», "…", “…” or '…' (an apostrophe inside a word, as in "Elias's", does not end it).
QUOTED = r"""(?:«([^»]+)»|"([^"]+)"|“([^”]+)”|'(.+?)'(?=[\s.,;:!?)]|$))"""
# How many characters may stand between "Act 2" and the quoted summary, e.g. `for Act Two, I suggest: «...»`.
MAX_GAP_TO_QUOTE = 25
NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5,
}
REPLACE = re.compile(r'^\s*scene\s+(\d+)\s*:?\s*replace\s+"(.+)"\s+with\s+"(.*)"\s*$', re.IGNORECASE)
SPEECH = re.compile(r"^([^():\n]+?)\s*(?:\(([^)]*)\))?\s*:\s*(.*)$")


def field_values(changes: str, fields: set[str], prefix: str = "") -> dict[str, dict[str, str]]:
    """Read agreed changes written one field per line, e.g. `tone: Darker.` or `act 2 summary: ...`.

    `prefix` is "act" or "scene" for lines that name the act or scene first; the result is keyed by its number
    ("" without a prefix). A value may go on over several lines until the next field line.
    """
    # The longest names come first, so "time_and_world" is not cut short by a field called "time".
    longest_first = sorted(fields, key=len, reverse=True)
    escaped_names = []
    for field in longest_first:
        escaped_names.append(re.escape(field))
    field_names = "|".join(escaped_names)

    if prefix:
        head = rf"^\s*{prefix}\s+(\d+)\s*[,:]?\s*"
    else:
        head = r"^\s*()"
    line_pattern = head + r"`?(" + field_names + r")`?\s*:\s*(.*)$"
    line_re = re.compile(line_pattern, re.IGNORECASE)

    values: dict[str, dict[str, str]] = {}
    current: tuple[str, str] | None = None
    for line in changes.strip().splitlines():
        match = line_re.match(line)
        if match:
            number, field, value = match.groups()
            current = (number, field.lower())
            values.setdefault(number, {})[current[1]] = value.strip()
            continue

        if current is not None and line.strip():
            number, field = current
            values[number][field] = f"{values[number][field]}\n{line.strip()}"
    return values


def quoted_values(text: str, fields: set[str], aliases: dict[str, str] | None = None) -> dict[str, str]:
    """Read new values from a proposal in prose, e.g. `I suggest the tone: «Darker.»` → {"tone": "Darker.", ...}.

    `aliases` maps other names of a field, e.g. in Russian, to the field: {"центральный конфликт": "central_conflict"}.
    """
    names: dict[str, str] = {}
    for field in fields:
        names[_spoken(field)] = field
    for alias, field in (aliases or {}).items():
        names[re.escape(alias)] = field

    longest_first = sorted(names, key=len, reverse=True)
    name_pattern = "|".join(longest_first)
    pattern = rf"(?<!\w)({name_pattern})\w*(?:\s+(?:to|be|should be|will be|is|на|:)|:)?\s*{QUOTED}"

    values = {}
    for match in re.finditer(pattern, text, re.IGNORECASE):
        name = match.group(1).casefold()
        field = _field_for_name(names, name)
        value = _first_group(match.groups()[1:])
        if field and value.strip():
            values[field] = value.strip()
    return values


def quoted_acts(text: str) -> dict[int, str]:
    """Read new act summaries from a proposal in prose, e.g. `I suggest for Act Two: «...»` → {2: "..."}."""
    number_first = r"\bact\s+(\d+|one|two|three|four|five)\b"
    number_last = r"\b(first|second|third|fourth|fifth)\s+act\b"
    gap = rf"[^«\"“']{{0,{MAX_GAP_TO_QUOTE}}}"
    pattern = rf"(?:{number_first}|{number_last}){gap}{QUOTED}"

    acts = {}
    for match in re.finditer(pattern, text, re.IGNORECASE):
        word = (match.group(1) or match.group(2)).lower()
        value = _first_group(match.groups()[2:])
        if word.isdigit():
            number = int(word)
        else:
            number = NUMBER_WORDS[word]
        acts[number] = value.strip()
    return acts


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
    if match is not None:
        speaker = match.group(1)
        speaker_is_upper_case = speaker == speaker.upper()
        speaker_has_letters = any(char.isalpha() for char in speaker)
        if speaker_is_upper_case and speaker_has_letters:
            note = match.group(2) or ""
            return GeneratedLine(character=speaker.strip(), parenthetical=note.strip(), text=match.group(3).strip())
    return GeneratedLine(character="", parenthetical="", text=text)


def _spoken(field: str) -> str:
    """Return a pattern for the field name as the model writes it in prose: "time and world" for `time_and_world`."""
    return field.replace("_", r"[ _]")


def _field_for_name(names: dict[str, str], name: str) -> str | None:
    """Return the field whose pattern matches the whole name, or None."""
    for pattern, field in names.items():
        if re.fullmatch(pattern, name, re.IGNORECASE):
            return field
    return None


def _first_group(groups: tuple[str | None, ...]) -> str:
    """Return the first group that matched; the quoted value is in exactly one of the quote styles."""
    for group in groups:
        if group is not None:
            return group
    return ""
