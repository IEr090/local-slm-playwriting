from enum import Enum

from pydantic import BaseModel


class BlockKind(str, Enum):
    """Name the kinds of block a scene text is made of."""

    SPEECH = "speech"
    DIRECTION = "direction"
    PLAIN = "plain"


class ScriptBlock(BaseModel):
    """Represent one block of a scene text; speaker and note are empty unless it is a speech."""

    kind: BlockKind
    speaker: str
    note: str
    text: str


class DocumentCastMember(BaseModel):
    """Represent a line of Dramatis Personae in the printed play."""

    name: str
    description: str


class DocumentScene(BaseModel):
    """Represent a scene of the printed play with its place and parsed text."""

    number: int
    place_name: str
    blocks: list[ScriptBlock]


class DocumentAct(BaseModel):
    """Represent an act of the printed play; its number is also written in words."""

    number: int
    number_word: str
    scenes: list[DocumentScene]


class PlayDocument(BaseModel):
    """Represent everything a renderer needs to typeset the finished play."""

    title: str
    genre: str
    premise: str
    time_and_world: str
    language_code: str
    act_count: int
    act_count_word: str
    cast: list[DocumentCastMember]
    acts: list[DocumentAct]
