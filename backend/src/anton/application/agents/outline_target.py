from pydantic import ValidationError

from anton.application.agents.change_lines import field_values, quoted_values
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

    def parse_changes(self, data: Outline, changes: str) -> Outline | None:
        """Apply changes written as `field_key: new value` without the model; None if they are not written so."""
        # as the prompt asks (`tone: ...`), or as in a proposal the playwright agreed to (`the tone: «...»`)
        values = field_values(changes, set(Outline.model_fields)).get("", {}) or quoted_values(changes, set(Outline.model_fields))
        if not values:
            return None
        if "genre" in values:
            values["genre"] = values["genre"].strip().strip(".").lower()
        try:
            return Outline(**(data.model_dump() | {key: value.strip() for key, value in values.items()}))
        except ValidationError:
            return None

    def generate_input(self, source: dict[str, str]) -> str:
        """Give the model the user's idea and the cast under the headings the prompt describes."""
        return f"# IDEA\n\n{source['idea']}\n\n# CAST\n\n{source['cast']}"

    def from_generated(self, generated: GeneratedOutline) -> Outline:
        """Turn the generated outline into the outline of the Story Bible."""
        return to_outline(generated)
