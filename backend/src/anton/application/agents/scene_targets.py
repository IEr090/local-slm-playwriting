from pydantic import BaseModel

from anton.application.agents.change_lines import field_values

from anton.application.llm_schemas.scene_generation import (
    EditedScenes,
    GeneratedActStructure,
    GeneratedPlace,
    GeneratedStructure,
    GeneratedStructureScene,
)
from anton.domain.models import PlaceDraft


class SceneView(BaseModel):
    """Represent a scene as the model sees it: with the names of the place and the characters instead of ids."""

    number: int
    place: str
    place_notes: str
    characters: list[str]
    what_happens: str


class SceneBoard(BaseModel):
    """Represent the scenes of an act page and the new places the model proposed for them."""

    scenes: list[SceneView]
    new_places: list[PlaceDraft] = []


class StructureTarget:
    """Let an editing agent propose the scenes of an act, then reorder, cut, add or change them with the user."""

    name = "scenes"
    chat_prompt = "structure_chat.md"
    edit_prompt = "structure_edit.md"
    edit_schema = GeneratedStructure
    generate_prompt = "act_structure.md"
    generate_schema = GeneratedActStructure

    def view(self, data: SceneBoard) -> list[dict]:
        """Show the model every scene of the structure in order."""
        return [scene.model_dump(exclude={"place_notes"}) for scene in data.scenes]

    def apply(self, data: SceneBoard, edited: GeneratedStructure) -> SceneBoard:
        """Take the whole new list of scenes from the model; the order of the list is the order of the act."""
        return _board(edited.scenes, edited.new_places)

    def parse_changes(self, data: SceneBoard, changes: str) -> SceneBoard | None:
        """Never parse the changes without the model: the structure is rewritten as a whole list."""
        return None

    def generate_input(self, source: dict[str, str]) -> str:
        """Give the model the outline, the act, the acts before it, the places and the cast."""
        sections = [
            ("outline", "OUTLINE"), ("act", "ACT"), ("earlier_acts", "EARLIER ACTS"),
            ("places", "PLACES"), ("cast", "CAST"),
        ]
        blocks = []
        for key, title in sections:
            blocks.append(f"# {title}\n\n{source[key]}")
        blocks.append(f"# LANGUAGE\n\n{source.get('language', 'English')}")
        return "\n\n".join(blocks)

    def from_generated(self, generated: GeneratedStructure) -> SceneBoard:
        """Number the generated scenes from one."""
        return _board(generated.scenes, generated.new_places)


class ScenesTarget:
    """Let an editing agent revise the plan of the scene the user names."""

    name = "scenes"
    chat_prompt = "scenes_chat.md"
    edit_prompt = "scenes_edit.md"
    edit_schema = EditedScenes

    def view(self, data: SceneBoard) -> list[dict]:
        """Show the model every scene with its plan."""
        return [scene.model_dump() for scene in data.scenes]

    def parse_changes(self, data: SceneBoard, changes: str) -> SceneBoard | None:
        """Apply changes written as `scene N field_key: new value` without the model; None if not written so."""
        values = field_values(changes, {"place", "place_notes", "characters", "what_happens"}, prefix="scene")
        if not values:
            return None
        scenes = []
        for scene in data.scenes:
            patch: dict = {key: value.strip() for key, value in values.get(str(scene.number), {}).items()}
            if "characters" in patch:
                patch["characters"] = [name.strip() for name in patch["characters"].split(",") if name.strip()]
            scenes.append(scene.model_copy(update=patch))
        return SceneBoard(scenes=scenes, new_places=[])

    def apply(self, data: SceneBoard, edited: EditedScenes) -> SceneBoard:
        """Replace only the scenes the model edited; numbers the act does not have are ignored."""
        by_number = {scene.number: scene for scene in edited.scenes}
        scenes = []
        for scene in data.scenes:
            edited_scene = by_number.get(scene.number)
            if edited_scene is None:
                scenes.append(scene)
                continue
            values = edited_scene.model_dump()
            values["what_happens"] = edited_scene.what_happens.strip()
            scenes.append(SceneView(**values))
        return SceneBoard(scenes=scenes, new_places=_places(edited.new_places))


def _board(scenes: list[GeneratedStructureScene], places: list[GeneratedPlace]) -> SceneBoard:
    """Number the scenes in their order and keep the proposed places."""
    views = []
    for number, scene in enumerate(scenes, start=1):
        views.append(SceneView(
            number=number,
            place=scene.place.strip(),
            place_notes="",
            characters=scene.characters,
            what_happens=scene.what_happens.strip(),
        ))
    return SceneBoard(scenes=views, new_places=_places(places))


def _places(places: list[GeneratedPlace]) -> list[PlaceDraft]:
    """Turn the proposed places into place drafts with trimmed text."""
    drafts = []
    for place in places:
        trimmed = {}
        for key, value in place.model_dump().items():
            trimmed[key] = value.strip()
        drafts.append(PlaceDraft(**trimmed))
    return drafts
