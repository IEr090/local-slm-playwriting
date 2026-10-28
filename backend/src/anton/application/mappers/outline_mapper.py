from anton.application.llm_schemas.outline_generation import GeneratedOutline
from anton.domain.models import Outline


def to_outline(generated: GeneratedOutline) -> Outline:
    """Turn the generated outline into the outline of the Story Bible, trimming stray spaces."""
    return Outline(**{
        field: value.strip() if isinstance(value, str) else value
        for field, value in generated.model_dump().items()
    })


def changed_fields(old: Outline, new: Outline) -> list[str]:
    """Return the keys of the outline fields that differ, in the order of the outline."""
    return [field for field in Outline.model_fields if getattr(old, field) != getattr(new, field)]
