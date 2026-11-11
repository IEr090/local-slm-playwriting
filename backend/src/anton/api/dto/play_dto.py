from typing import Annotated

from pydantic import BaseModel, StringConstraints


class SceneTextEdit(BaseModel):
    """Represent the new text of one scene of the finished play."""

    # The text is trimmed first, so a text of spaces only is as empty as "" and is rejected.
    text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
