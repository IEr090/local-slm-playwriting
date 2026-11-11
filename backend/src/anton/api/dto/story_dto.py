from pydantic import BaseModel, Field

from anton.domain.models import ActSummary, Outline


class OutlineReviseRequest(BaseModel):
    """Represent a chat message about the outline together with the outline from the user's form."""

    message: str = Field(min_length=1)
    outline: Outline


class OutlineRevision(BaseModel):
    """Represent the answer of the outline agent and the outline as it sees it now."""

    reply: str
    outline: Outline


class ActsReviseRequest(BaseModel):
    """Represent a chat message about the acts together with the acts from the user's form."""

    message: str = Field(min_length=1)
    acts: list[ActSummary] = Field(min_length=1)


class ActsRevision(BaseModel):
    """Represent the answer of the acts agent and the acts as it sees them now."""

    reply: str
    acts: list[ActSummary]
