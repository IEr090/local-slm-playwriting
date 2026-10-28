from pydantic import BaseModel, Field, RootModel


class GeneratedLine(BaseModel):
    """Represent one line of a scene: a speech or a stage direction."""

    character: str = Field(description="Name of the speaking character, exactly as in the input. Empty string for a stage direction.")
    parenthetical: str = Field(description="A short acting note for the speech, e.g. 'looking at the table'. Empty string if none.")
    text: str = Field(description="What the character says, or the stage direction itself.")


class GeneratedSceneText(BaseModel):
    """Represent the dialogue and stage directions of one scene as the language model writes them."""

    lines: list[GeneratedLine] = Field(description="The scene from beginning to end. Start with a stage direction that sets the scene.")


class EditedSceneText(GeneratedSceneText):
    """Represent one scene text after the agreed changes, as the language model returns it."""

    scene_number: int = Field(description="Number of the scene, exactly as in the input.")


class EditedSceneTexts(RootModel[list[EditedSceneText]]):
    """Represent only the scene texts the agreed changes are about."""


class GeneratedHistoryEntry(BaseModel):
    """Represent what changed for one character in one scene."""

    character: str = Field(description="Name of the character, exactly as in the input.")
    change: str = Field(description="One sentence on what changed for the character: what they learned, decided, lost or how a relationship changed.")


class GeneratedHistory(BaseModel):
    """Represent the changes of the characters in one scene, as the language model extracts them."""

    entries: list[GeneratedHistoryEntry] = Field(description="One entry per character who changed. Empty if nobody changed.")
