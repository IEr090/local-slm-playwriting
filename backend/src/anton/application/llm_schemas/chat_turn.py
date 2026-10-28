from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    """Represent one answer of an editing agent in the chat."""

    reply: str = Field(
        description="Your own answer to the playwright's message, in their language. Never repeat or quote their message.",
    )
    apply_changes: str | None = Field(
        description=(
            "Only right after the playwright agreed to your proposal: the agreed new value of every affected field, "
            "written in the language of the edited text. Otherwise null."
        ),
    )
