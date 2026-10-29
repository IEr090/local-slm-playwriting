from anton.application.agents.change_lines import line_replacements, to_line
from anton.application.llm_schemas.text_generation import EditedSceneTexts, LineEdit
from anton.application.mappers.text_mapper import apply_line_edits
from anton.domain.models import SceneText


class TextTarget:
    """Let an editing agent revise the text of the scene the user names."""

    name = "scene_texts"
    chat_prompt = "text_chat.md"
    edit_prompt = "text_edit.md"
    edit_schema = EditedSceneTexts

    def view(self, data: list[SceneText]) -> list[dict]:
        """Show the model the text of every scene with its number."""
        return [scene_text.model_dump() for scene_text in data]

    def parse_changes(self, data: list[SceneText], changes: str) -> list[SceneText] | None:
        """Apply changes written as `scene N replace "old" with "new"` without the model; None if not written so."""
        replacements = line_replacements(changes)
        if not replacements:
            return None
        edits = [LineEdit(scene_number=scene, old_line=old, new_lines=[to_line(new)] if new.strip() else []) for scene, old, new in replacements]
        return self.apply(data, EditedSceneTexts(edits))

    def apply(self, data: list[SceneText], edited: EditedSceneTexts) -> list[SceneText]:
        """Apply the model's line edits to their scenes; scene numbers the act does not have are ignored."""
        return [
            SceneText(
                scene_number=item.scene_number,
                text=apply_line_edits(item.text, [edit for edit in edited.root if edit.scene_number == item.scene_number]),
            )
            for item in data
        ]
