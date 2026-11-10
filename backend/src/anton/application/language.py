import re


# Fewer letters than this are too little to tell a language.
MIN_LETTERS = 4
# Six words in a row that also stand in the prompt are no coincidence: the model copied its instructions.
ECHO_WORDS = 6
GERMAN_WORDS = {
    "und", "nicht", "ist", "der", "die", "das", "ein", "eine", "ich", "sie", "mit", "auf", "für", "zu", "bitte", "es",
}
ENGLISH_WORDS = {"the", "and", "is", "to", "of", "in", "a", "it", "you", "with", "on", "for", "that", "this"}


def language_of(text: str) -> str | None:
    """Name the language of a text from its letters: Russian, German or English; None for too few letters."""
    letters = re.findall(r"[^\W\d_]", text)
    if len(letters) < MIN_LETTERS:
        return None

    cyrillic = 0
    for letter in letters:
        lowered = letter.lower()
        if "а" <= lowered <= "я" or lowered == "ё":
            cyrillic += 1
    if cyrillic * 2 > len(letters):
        return "Russian"
    # "die" or "das" alone are English words too: German needs its letters or more German than English small words
    words = re.findall(r"\w+", text.casefold())
    german = 0
    english = 0
    for word in words:
        if word in GERMAN_WORDS:
            german += 1
        if word in ENGLISH_WORDS:
            english += 1
    if re.search(r"[äöüß]", text, re.IGNORECASE) or german > english:
        return "German"
    return "English"


def play_language(user_input: str) -> str:
    """Return the language the whole play is written in: the language of the user's idea, English by default.

    It is named in every generation input, because a small model otherwise writes in the language of its prompt.
    """
    return language_of(user_input) or "English"


def echoes(text: str, prompt: str) -> bool:
    """Tell whether a model answer copies a passage of its prompt instead of doing what the prompt asks."""
    words = re.findall(r"\w+", text.casefold())
    prompt_text = " ".join(re.findall(r"\w+", prompt.casefold()))
    for start in range(len(words) - ECHO_WORDS + 1):
        phrase = " ".join(words[start:start + ECHO_WORDS])
        if phrase in prompt_text:
            return True
    return False
