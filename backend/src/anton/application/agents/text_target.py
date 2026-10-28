from anton.application.llm_schemas.text_generation import EditedSceneTexts
from anton.application.mappers.text_mapper import format_lines
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

    def apply(self, data: list[SceneText], edited: EditedSceneTexts) -> list[SceneText]:
        """Replace only the scene texts the model rewrote; numbers the act does not have are ignored."""
        by_number = {item.scene_number: format_lines(item.lines) for item in edited.root}
        return [
            SceneText(scene_number=item.scene_number, text=by_number[item.scene_number])
            if by_number.get(item.scene_number) else item
            for item in data
        ]
