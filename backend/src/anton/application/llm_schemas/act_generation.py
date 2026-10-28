from pydantic import BaseModel, Field, RootModel

from anton.domain.models import DramaticFunction


class GeneratedAct(BaseModel):
    """Represent the summary of an act as the language model generates it."""

    summary: str = Field(description="Three or four sentences on what happens in the act. No dialogue.")
    dramatic_function: DramaticFunction


class GeneratedActs(RootModel[list[GeneratedAct]]):
    """Represent all acts of the play, in order, as the language model generates them."""


class GeneratedActRevision(BaseModel):
    """Represent the revised act and what was changed, as the language model generates them."""

    act_number: int | None = Field(description="Number of the act the request is about, or null if the request names no act.")
    summary: str = Field(description="The revised summary of that act.")
    dramatic_function: DramaticFunction
    change_note: str = Field(description="One short sentence on what was changed and why.")
