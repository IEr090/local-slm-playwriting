from pydantic import BaseModel, Field, RootModel

from anton.domain.models import DramaticFunction


class GeneratedAct(BaseModel):
    """Represent the summary of an act as the language model generates it."""

    summary: str = Field(description="Three or four sentences on what happens in the act. No dialogue.")
    dramatic_function: DramaticFunction


class GeneratedActs(RootModel[list[GeneratedAct]]):
    """Represent all acts of the play, in order, as the language model generates them."""

