from pydantic import BaseModel, Field, RootModel


class GeneratedLine(BaseModel):
    """Represent one line of a scene: a speech or a stage direction."""

    character: str = Field(description="Name of the speaking character, exactly as in the input. Empty string for a stage direction.")
    parenthetical: str = Field(description="A short acting note for the speech, e.g. 'looking at the table'. Empty string if none.")
    text: str = Field(description="What the character says, or the stage direction itself.")


class GeneratedSceneText(BaseModel):
    """Represent the dialogue and stage directions of one scene as the language model writes them."""

    lines: list[GeneratedLine] = Field(description="The scene from beginning to end. Start with a stage direction that sets the scene.")


class LineEdit(BaseModel):
    """Represent one agreed change of a scene text: a line and the lines that take its place."""

    scene_number: int = Field(description="Number of the scene, exactly as in the input.")
    old_line: str = Field(
        description="The line to change, copied exactly from the scene text, e.g. 'MARGIT: Of course you didn't.'. "
        "Empty string to add the new lines at the end of the scene.",
    )
    new_lines: list[GeneratedLine] = Field(description="The lines that take the place of the old line, in order. Empty to cut the line.")


# A small model that has to rewrite a whole scene often returns only the lines it changed and the rest of the
# scene is lost, so it returns only the edits and every other line stays as it is.
class EditedSceneTexts(RootModel[list[LineEdit]]):
    """Represent the agreed changes of the scene texts, one edit per changed line."""


class GeneratedHistoryEntry(BaseModel):
    """Represent what changed for one character in one scene."""

    character: str = Field(description="Name of the character, exactly as in the input.")
    change: str = Field(description="One sentence on what changed for the character: what they learned, decided, lost or how a relationship changed.")


class GeneratedHistory(BaseModel):
    """Represent the changes of the characters in one scene, as the language model extracts them."""

    entries: list[GeneratedHistoryEntry] = Field(description="One entry per character who changed. Empty if nobody changed.")
