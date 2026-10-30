from pydantic import BaseModel, Field


class GeneratedPlace(BaseModel):
    """Represent a new place as the language model proposes it."""

    name: str = Field(description="Short name of the place, e.g. 'The lamp room'.")
    description: str = Field(description="What it looks like and what is in it: doors, windows, furniture, objects, atmosphere.")
    significance: str = Field(description="Why this place matters for the story, in one sentence.")


class GeneratedStructureScene(BaseModel):
    """Represent one scene of an act structure as the language model writes it."""

    place: str = Field(description="Name of the place, exactly as in the list of places or in new_places.")
    characters: list[str] = Field(description="Names of the characters on stage, exactly as in the cast.")
    what_happens: str = Field(description="One or two sentences on what happens. No dialogue.")


class GeneratedStructure(BaseModel):
    """Represent the structure of an act and the places it needs, as the language model writes them."""

    new_places: list[GeneratedPlace] = Field(description="Places that are not in the list yet. Empty if none are needed.")
    scenes: list[GeneratedStructureScene]


MIN_SCENES = 2
MAX_SCENES = 8


# The limits are part of the JSON schema sent to the model, so a small model cannot stage an act as one scene.
# Only the first structure is limited; the playwright may cut scenes in the chat afterwards.
class GeneratedActScene(GeneratedStructureScene):
    """Represent a scene of the first structure of an act: at least two characters, so that they can clash."""

    characters: list[str] = Field(
        description="Names of the characters on stage, exactly as in the cast; at least two.",
        json_schema_extra={"minItems": 2},
    )


class GeneratedActStructure(GeneratedStructure):
    """Represent the first structure of an act, with a sensible number of scenes."""

    scenes: list[GeneratedActScene] = Field(min_length=MIN_SCENES, max_length=MAX_SCENES)


class GeneratedScenePlan(BaseModel):
    """Represent the detailed plan of one scene as the language model writes it."""

    place_notes: str = Field(description="The state of the place in this scene.")
    what_happens: str = Field(description="The plan of the scene.")


class EditedScene(GeneratedStructureScene):
    """Represent one scene after the agreed changes, as the language model returns it."""

    number: int = Field(description="Number of the scene, exactly as in the input.")
    place_notes: str


class EditedScenes(BaseModel):
    """Represent only the scenes the agreed changes are about and the places they need."""

    new_places: list[GeneratedPlace] = Field(description="Places that are not in the list yet. Empty if none are needed.")
    scenes: list[EditedScene]
