from pydantic import BaseModel, Field

from anton.domain.models import Genre


class GeneratedOutline(BaseModel):
    """Represent the play outline as the language model generates it."""

    title: str = Field(description="Title of the play.")
    premise: str = Field(description="One sentence on where the play is headed, e.g. 'Greed leads to loss.'")
    genre: Genre
    tone: str = Field(description="Tone and atmosphere in one or two sentences.")
    time_and_world: str = Field(description="Era and milieu of the play; no list of concrete places.")
    central_conflict: str = Field(description="Who wants what and what stands in the way.")
    synopsis: str = Field(description="A few sentences from the beginning to the end of the play, including the ending.")


class GeneratedOutlineRevision(BaseModel):
    """Represent the revised outline and what was changed, as the language model generates them."""

    outline: GeneratedOutline
    change_note: str = Field(description="One short sentence on what was changed and why.")
