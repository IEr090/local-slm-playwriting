from anton.application.llm_schemas.act_generation import EditedAct, GeneratedAct
from anton.domain.models import ActSummary


# The order of the dramatic functions in a play; acts with the same function keep the order the model wrote.
FUNCTION_ORDER = {"setup": 0, "development": 1, "climax": 2, "resolution": 3}


def to_act_summaries(generated: list[GeneratedAct]) -> list[ActSummary]:
    """Number the generated acts from one, in the order of their dramatic functions.

    A small model sometimes writes the resolution before the development; the summaries follow their function,
    so putting the functions in order also puts the story in order.
    """
    ordered = sorted(generated, key=lambda item: FUNCTION_ORDER[item.dramatic_function])
    return [
        ActSummary(number=number, summary=item.summary.strip(), dramatic_function=item.dramatic_function)
        for number, item in enumerate(ordered, start=1)
    ]


def apply_edited_acts(acts: list[ActSummary], edited: list[EditedAct]) -> list[ActSummary]:
    """Replace the acts the model edited and keep the others; numbers the play does not have are ignored."""
    by_number = {item.number: item for item in edited}

    result = []
    for act in acts:
        item = by_number.get(act.number)
        if item is None:
            result.append(act)
            continue
        result.append(ActSummary(
            number=act.number,
            summary=item.summary.strip(),
            dramatic_function=item.dramatic_function,
        ))
    return result
