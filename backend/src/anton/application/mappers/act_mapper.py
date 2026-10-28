from anton.application.llm_schemas.act_generation import EditedAct, GeneratedAct
from anton.domain.models import ActSummary
from anton.errors import SLMResponseError


def to_act_summaries(generated: list[GeneratedAct]) -> list[ActSummary]:
    """Number the generated acts from one in the order the model wrote them."""
    if not generated:
        raise SLMResponseError("The model returned no acts")
    return [
        ActSummary(number=number, summary=item.summary.strip(), dramatic_function=item.dramatic_function)
        for number, item in enumerate(generated, start=1)
    ]


def apply_edited_acts(acts: list[ActSummary], edited: list[EditedAct]) -> list[ActSummary]:
    """Replace the acts the model edited and keep the others; numbers the play does not have are ignored."""
    by_number = {item.number: item for item in edited}
    return [
        ActSummary(number=act.number, summary=by_number[act.number].summary.strip(), dramatic_function=by_number[act.number].dramatic_function)
        if act.number in by_number else act
        for act in acts
    ]
