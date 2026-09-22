from pathlib import Path


PROMPTS_DIRECTORY = Path(__file__).parent


def load_prompt(filename: str) -> str:
    """Read a Markdown prompt and return its content."""
    prompt_path = PROMPTS_DIRECTORY / filename

    if prompt_path.suffix != ".md" or prompt_path.parent != PROMPTS_DIRECTORY:
        raise ValueError("Prompt filename must reference a Markdown file in the prompts directory")

    return prompt_path.read_text(encoding="utf-8")
