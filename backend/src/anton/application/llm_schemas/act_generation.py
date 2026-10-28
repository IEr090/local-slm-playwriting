from pydantic import BaseModel, Field, RootModel

from anton.domain.models import DramaticFunction


class GeneratedAct(BaseModel):
    """Represent the summary of an act as the language model generates it."""

    summary: str = Field(description="Three or four sentences on what happens in the act. No dialogue.")
    dramatic_function: DramaticFunction


class GeneratedActs(RootModel[list[GeneratedAct]]):
    """Represent all acts of the play, in order, as the language model generates them."""


class EditedAct(GeneratedAct):
    """Represent one act after the agreed changes, as the language model returns it."""

    number: int = Field(description="Number of the act, exactly as in the input.")


class EditedActs(RootModel[list[EditedAct]]):
    """Represent only the acts the agreed changes are about, as the language model returns them."""


class ActsChatTurn(BaseModel):
    """Represent one answer of the acts agent in the chat."""

    reply: str = Field(
        description="Your own answer to the playwright's message, in their language. Never repeat or quote their message.",
    )
    apply_changes: str | None = Field(
        description=(
            "Only right after the playwright agreed to your proposal: the act number and the agreed new value of every "
            "affected field, written in the language of the acts. Otherwise null."
        ),
    )
