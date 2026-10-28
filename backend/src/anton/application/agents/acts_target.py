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

    def generate_input(self, source: dict[str, str]) -> str:
        """Give the model the outline and the cast under the headings the prompt describes."""
        return f"# OUTLINE\n\n{source['outline']}\n\n# CAST\n\n{source['cast']}"

    def from_generated(self, generated: GeneratedActs) -> list[ActSummary]:
        """Number the generated acts from one."""
        return to_act_summaries(generated.root)
