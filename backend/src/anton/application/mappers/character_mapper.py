from uuid import uuid4

from anton.application.llm_schemas.character_generation import GeneratedCharacter, GeneratedRelationship
from anton.domain.models import Character, Relationship


def to_characters(generated: list[GeneratedCharacter]) -> list[Character]:
    """Give every generated character an id and link relationships to those ids."""
    ids = [str(uuid4()) for _ in generated]

    return [
        Character(
            id=character_id,
            **item.model_dump(exclude={"relationships"}),
            relationships=[
                Relationship(
                    character_id=_find_id(relationship, generated, ids),
                    description=relationship.description,
                )
                for relationship in item.relationships
            ],
        )
        for character_id, item in zip(ids, generated)
    ]


def _find_id(relationship: GeneratedRelationship, generated: list[GeneratedCharacter], ids: list[str]) -> str:
    """Return the id of the referenced character, or an empty string if it is not clear."""
    name = _normalize(relationship.name)
    surname = _normalize(relationship.surname)

    by_full_name = [
        character_id
        for character_id, item in zip(ids, generated)
        if _normalize(item.name) == name and _normalize(item.surname) == surname
    ]
    if len(by_full_name) == 1:
        return by_full_name[0]

    by_name = [character_id for character_id, item in zip(ids, generated) if _normalize(item.name) == name]
    if len(by_name) == 1:
        return by_name[0]

    return ""


def _normalize(value: str) -> str:
    """Make names comparable regardless of case and surrounding spaces."""
    return value.strip().casefold()
