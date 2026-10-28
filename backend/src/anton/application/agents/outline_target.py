from anton.application.llm_schemas.outline_generation import GeneratedOutline
from anton.application.mappers.outline_mapper import to_outline
from anton.domain.models import Outline


class OutlineTarget:
    """Let an editing agent write the outline of the play from the user's idea and the cast, then revise it."""

    name = "outline"
    chat_prompt = "outline_chat.md"
    edit_prompt = "outline_edit.md"
    edit_schema = GeneratedOutline
    generate_prompt = "outline_generation.md"
    generate_schema = GeneratedOutline

    def view(self, data: Outline) -> dict:
        """Show the model the whole outline."""
        return data.model_dump()

    def apply(self, data: Outline, edited: GeneratedOutline) -> Outline:
        """Take the whole outline from the model."""
        return to_outline(edited)

    def generate_input(self, source: dict[str, str]) -> str:
        """Give the model the user's idea and the cast under the headings the prompt describes."""
        return f"# IDEA\n\n{source['idea']}\n\n# CAST\n\n{source['cast']}"

    def from_generated(self, generated: GeneratedOutline) -> Outline:
        """Turn the generated outline into the outline of the Story Bible."""
        return to_outline(generated)
