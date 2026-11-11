from pydantic import BaseModel, Field


class SceneTextEdit(BaseModel):
    """Represent the new text of one scene of the finished play."""

    text: str = Field(min_length=1)
