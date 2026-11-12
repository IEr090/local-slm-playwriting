from anton.application.language import language_of
from anton.application.mappers.script_parser import parse_script_blocks
from anton.domain.models import (
    DocumentAct,
    DocumentCastMember,
    DocumentScene,
    Play,
    PlayAct,
    PlayDocument,
    PlayScene,
)


NUMBER_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
}
LANGUAGE_CODES = {"English": "en", "German": "de", "Russian": "ru"}
DEFAULT_LANGUAGE_CODE = "en"


def number_in_words(number: int) -> str:
    """Return the number as an English word; numbers above ten stay digits."""
    return NUMBER_WORDS.get(number, str(number))


def to_play_document(play: Play) -> PlayDocument:
    """Turn the read model of the play into the document a renderer typesets, with the scene texts parsed."""
    cast = []
    for member in play.cast:
        cast.append(DocumentCastMember(name=member.name, description=member.description))

    acts = []
    for act in play.acts:
        acts.append(_to_document_act(act))

    return PlayDocument(
        title=play.title,
        genre=play.genre,
        premise=play.premise,
        time_and_world=play.time_and_world,
        language_code=_language_code(play),
        act_count=play.act_count,
        act_count_word=number_in_words(play.act_count),
        cast=cast,
        acts=acts,
    )


def _to_document_act(act: PlayAct) -> DocumentAct:
    """Return the act with its scenes in order."""
    scenes = []
    for scene in act.scenes:
        scenes.append(_to_document_scene(scene))
    return DocumentAct(number=act.number, number_word=number_in_words(act.number), scenes=scenes)


def _to_document_scene(scene: PlayScene) -> DocumentScene:
    """Return the scene with its text split into blocks."""
    return DocumentScene(
        number=scene.number, place_name=scene.place_name, blocks=parse_script_blocks(scene.text),
    )


def _language_code(play: Play) -> str:
    """Return the language code of the play, taken from its premise; English when it cannot be told."""
    language = language_of(play.premise)
    if language is None:
        return DEFAULT_LANGUAGE_CODE
    return LANGUAGE_CODES.get(language, DEFAULT_LANGUAGE_CODE)
