from pydantic import BaseModel


class PlayCastMember(BaseModel):
    """Represent a line of Dramatis Personae: a character with a short description."""

    character_id: str
    name: str
    description: str


class PlayScene(BaseModel):
    """Represent a scene of the finished play with its place and text."""

    number: int
    place_name: str
    place_notes: str
    text: str


class PlayAct(BaseModel):
    """Represent an act of the finished play with its scenes in story order."""

    number: int
    scenes: list[PlayScene]


class Play(BaseModel):
    """Represent everything the page of the whole play shows, so the frontend does not join it itself."""

    title: str
    genre: str
    premise: str
    time_and_world: str
    act_count: int
    cast: list[PlayCastMember]
    acts: list[PlayAct]
