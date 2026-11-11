from pydantic import BaseModel, Field

from anton.domain.models import ScenePlan, SceneText


class ScenesReviseRequest(BaseModel):
    """Represent a chat message on the act page together with the scenes from the user's form."""

    message: str = Field(min_length=1)
    scenes: list[ScenePlan] = Field(min_length=1)


class TextReviseRequest(BaseModel):
    """Represent a chat message about the text of the act together with the scene texts from the user's form."""

    message: str = Field(min_length=1)
    scene_texts: list[SceneText] = Field(min_length=1)
