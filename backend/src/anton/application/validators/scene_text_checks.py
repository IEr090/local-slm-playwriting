import re
from difflib import SequenceMatcher

from anton.application.llm_schemas.text_generation import GeneratedLine
from anton.application.mappers.text_mapper import normalize_line


# Two speeches this similar say the same thing, only in slightly other words.
SAME_SPEECH = 0.85
# A shorter speech must have this many characters to count as part of a longer one, and the longer one
# may add at most this many characters to it.
MIN_SPEECH_LENGTH = 8
MAX_ADDED_LENGTH = 12
# A five-word phrase in three speeches is a character saying the same thing over and over.
LOOP_PHRASE_WORDS = 5
LOOP_PHRASE_LINES = 3


def unknown_speakers(lines: list[GeneratedLine], characters: list[dict]) -> list[str]:
    """Return the speakers of the lines who are not among the characters on stage, by name, surname or both."""
    known = set()
    for character in characters:
        name = character.get("name", "").strip()
        surname = character.get("surname", "").strip()
        for spelling in (name, surname, f"{name} {surname}"):
            normalized = normalize_line(spelling)
            if normalized:
                known.add(normalized)

    strangers: dict[str, str] = {}
    for line in lines:
        speaker = line.character.strip()
        if not speaker or not line.text.strip():
            continue
        key = normalize_line(speaker)
        if key not in known:
            strangers.setdefault(key, speaker)
    return list(strangers.values())


def repeated_lines(lines: list[GeneratedLine]) -> int:
    """Count the lines that repeat an earlier line, word for word or nearly so."""
    texts = [normalize_line(line.text) for line in lines]
    count = 0
    for index, text in enumerate(texts):
        if text and _says_same_as_any(text, texts[:index]):
            count += 1
    return count


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
        speaker = normalize_line(line.character)
        if not speaker:
            continue

        names = {speaker}
        for character in characters:
            name = normalize_line(character.get("name", ""))
            if name and name in speaker:
                names.add(name)

        text = normalize_line(line.text)
        for name in names:
            if text.startswith(f"{name} ") or text.startswith(f"{name},"):
                count += 1
                break
    return count


def without_repeats(lines: list[GeneratedLine]) -> list[GeneratedLine]:
    """Drop the lines that repeat an earlier line, or bring back a phrase two earlier speeches already said."""
    kept: list[GeneratedLine] = []
    kept_texts: list[str] = []
    phrase_counts: dict[str, int] = {}
    for line in lines:
        text = normalize_line(line.text)
        phrases = _line_phrases(line.text)

        repeats = bool(text) and _says_same_as_any(text, kept_texts)
        loops = _brings_back_phrase(phrases, phrase_counts)
        if repeats or loops:
            continue

        kept.append(line)
        kept_texts.append(text)
        for phrase in phrases:
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1
    return kept


def _says_same_as_any(text: str, earlier_texts: list[str]) -> bool:
    """Tell whether the speech says the same as any of the earlier speeches."""
    for earlier in earlier_texts:
        if _same_speech(text, earlier):
            return True
    return False


def _brings_back_phrase(phrases: set[str], phrase_counts: dict[str, int]) -> bool:
    """Tell whether one of the phrases was already said in all but one of the speeches that make a loop."""
    for phrase in phrases:
        if phrase_counts.get(phrase, 0) >= LOOP_PHRASE_LINES - 1:
            return True
    return False


def _same_speech(a: str, b: str) -> bool:
    """Tell whether two speeches say the same: nearly the same words, or one only adds a word to the other."""
    if a == b:
        return True

    shorter, longer = sorted((a, b), key=len)
    if len(shorter) < MIN_SPEECH_LENGTH:
        return False

    added_length = len(longer) - len(shorter)
    only_adds_a_word = shorter in longer and added_length <= MAX_ADDED_LENGTH
    if only_adds_a_word:
        return True
    return SequenceMatcher(None, a, b).ratio() >= SAME_SPEECH


def _line_phrases(text: str) -> set[str]:
    """Return the five-word phrases of a speech."""
    words = re.findall(r"\w+", text.casefold())
    phrases = set()
    for start in range(len(words) - LOOP_PHRASE_WORDS + 1):
        phrases.add(" ".join(words[start:start + LOOP_PHRASE_WORDS]))
    return phrases
