from anton.application.llm_schemas.act_generation import GeneratedAct
from anton.domain.models import Act
from anton.errors import SLMResponseError


def to_acts(generated: list[GeneratedAct]) -> list[Act]:
    """Number the generated acts from one in the order the model wrote them."""
    if not generated:
        raise SLMResponseError("The model returned no acts")
    return [
        Act(number=number, summary=item.summary.strip(), dramatic_function=item.dramatic_function)
        for number, item in enumerate(generated, start=1)
    ]


def changed_act_fields(old: Act, new: Act) -> list[str]:
    """Return the keys of the act fields the user can edit that differ."""
    return [field for field in ("summary", "dramatic_function") if getattr(old, field) != getattr(new, field)]
