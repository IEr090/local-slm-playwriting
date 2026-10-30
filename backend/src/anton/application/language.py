import re


def language_of(text: str) -> str | None:
    """Name the language of a text from its letters: Russian, German or English; None for too few letters."""
    letters = re.findall(r"[^\W\d_]", text)
    if len(letters) < 4:
        return None
    cyrillic = sum("а" <= letter.lower() <= "я" or letter.lower() == "ё" for letter in letters)
    if cyrillic * 2 > len(letters):
        return "Russian"
    # "die" or "das" alone are English words too: German needs its letters or more German than English small words
    words = re.findall(r"\w+", text.casefold())
    german = sum(word in GERMAN_WORDS for word in words)
    english = sum(word in ENGLISH_WORDS for word in words)
    if re.search(r"[äöüß]", text, re.IGNORECASE) or german > english:
        return "German"
    return "English"


GERMAN_WORDS = {"und", "nicht", "ist", "der", "die", "das", "ein", "eine", "ich", "sie", "mit", "auf", "für", "zu", "bitte", "es"}
ENGLISH_WORDS = {"the", "and", "is", "to", "of", "in", "a", "it", "you", "with", "on", "for", "that", "this"}


def play_language(user_input: str) -> str:
    """Return the language the whole play is written in: the language of the user's idea, English by default.

    It is named in every generation input, because a small model otherwise writes in the language of its prompt.
    """
    return language_of(user_input) or "English"


# Six words in a row that also stand in the prompt are no coincidence: the model copied its instructions.
ECHO_WORDS = 6


def echoes(text: str, prompt: str) -> bool:
    """Tell whether a model answer copies a passage of its prompt instead of doing what the prompt asks."""
    words = re.findall(r"\w+", text.casefold())
    prompt_text = " ".join(re.findall(r"\w+", prompt.casefold()))
    return any(
        " ".join(words[i:i + ECHO_WORDS]) in prompt_text
        for i in range(len(words) - ECHO_WORDS + 1)
    )
