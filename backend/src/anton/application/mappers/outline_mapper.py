from anton.application.llm_schemas.outline_generation import GeneratedOutline
from anton.domain.models import Outline


def to_outline(generated: GeneratedOutline) -> Outline:
    """Turn the generated outline into the outline of the Story Bible, trimming stray spaces."""
    values = {}
    for field, value in generated.model_dump().items():
        if isinstance(value, str):
            value = value.strip()
        values[field] = value
    return Outline(**values)

