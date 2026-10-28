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


class OutlineChatTurn(BaseModel):
    """Represent one answer of the outline agent in the chat."""

    reply: str = Field(
        description="Your own answer to the playwright's message, in their language. Never repeat or quote their message.",
    )
    apply_changes: str | None = Field(
        description=(
            "Only right after the playwright agreed to your proposal: the agreed new value of every affected field, "
            "written in the language of the outline. Otherwise null."
        ),
    )
