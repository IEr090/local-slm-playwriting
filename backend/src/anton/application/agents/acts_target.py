from pydantic import ValidationError

from anton.application.agents.change_lines import field_values, quoted_acts
from anton.application.llm_schemas.act_generation import EditedActs, GeneratedActs
from anton.application.mappers.act_mapper import apply_edited_acts, to_act_summaries
from anton.domain.models import ActSummary


class ActsTarget:
    """Let an editing agent divide the outline into acts, then revise the act the user names."""

    name = "acts"
    chat_prompt = "acts_chat.md"
    edit_prompt = "acts_edit.md"
    edit_schema = EditedActs
    generate_prompt = "act_generation.md"
    generate_schema = GeneratedActs

    def view(self, data: list[ActSummary]) -> list[dict]:
        """Show the model every act with its number, summary and dramatic function."""
        return [act.model_dump() for act in data]

    def apply(self, data: list[ActSummary], edited: EditedActs) -> list[ActSummary]:
        """Replace only the acts the model edited."""
        return apply_edited_acts(data, edited.root)

    def parse_changes(self, data: list[ActSummary], changes: str) -> list[ActSummary] | None:
        """Apply changes written as `act N field_key: new value` without the model; None if they are not written so."""
        values = field_values(changes, {"summary", "dramatic_function"}, prefix="act") or {
            str(number): {"summary": summary} for number, summary in quoted_acts(changes).items()
        }
        if not values:
            return None
        acts = []
        for act in data:
            patch = {key: value.strip().lower() if key == "dramatic_function" else value.strip() for key, value in values.get(str(act.number), {}).items()}
            try:
                acts.append(ActSummary(**(act.model_dump() | patch)))
            except ValidationError:
                return None
        return acts

    def generate_input(self, source: dict[str, str]) -> str:
        """Give the model the outline and the cast under the headings the prompt describes."""
        return f"# OUTLINE\n\n{source['outline']}\n\n# CAST\n\n{source['cast']}\n\n# LANGUAGE\n\n{source.get('language', 'English')}"

    def from_generated(self, generated: GeneratedActs) -> list[ActSummary]:
        """Number the generated acts from one."""
        return to_act_summaries(generated.root)
