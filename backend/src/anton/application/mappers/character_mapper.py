from uuid import uuid4

from anton.application.llm_schemas.character_generation import GeneratedCharacter, GeneratedRelationship
from anton.domain.models import Character, Relationship


def to_characters(generated: list[GeneratedCharacter]) -> list[Character]:
    """Give every generated character an id and link relationships to those ids."""
    ids = [str(uuid4()) for _ in generated]
    names = [_split_name(item.name, item.surname) for item in generated]

    return [
        Character(
            id=character_id,
            name=name,
            surname=surname,
            **item.model_dump(exclude={"name", "surname", "relationships"}),
            relationships=[
                Relationship(
                    character_id=_find_id(relationship, names, ids),
                    description=relationship.description,
                )
                for relationship in item.relationships
            ],
        )
        for character_id, (name, surname), item in zip(ids, names, generated)
    ]


def _split_name(name: str, surname: str) -> tuple[str, str]:
    """Keep only the first name in the name, even if the model also wrote the surname there."""
    name = name.strip()
    surname = surname.strip()

    if surname and name.casefold().endswith(" " + surname.casefold()):
        return name[: -len(surname)].strip(), surname
    if not surname and " " in name:
        first, rest = name.split(" ", 1)
        return first, rest.strip()
    return name, surname


def _find_id(relationship: GeneratedRelationship, names: list[tuple[str, str]], ids: list[str]) -> str:
    """Return the id of the referenced character, or an empty string if it is not clear."""
    name, surname = (_normalize(part) for part in _split_name(relationship.name, relationship.surname))

    by_full_name = [
        character_id
        for character_id, (item_name, item_surname) in zip(ids, names)
        if _normalize(item_name) == name and _normalize(item_surname) == surname
    ]
    if len(by_full_name) == 1:
        return by_full_name[0]

    by_name = [character_id for character_id, (item_name, _) in zip(ids, names) if _normalize(item_name) == name]
    if len(by_name) == 1:
        return by_name[0]

    return ""


def _normalize(value: str) -> str:
    """Make names comparable regardless of case and surrounding spaces."""
    return value.strip().casefold()
