from uuid import uuid4

from anton.application.agents.scene_targets import SceneBoard, SceneView
from anton.domain.models import Character, Place, Scene, ScenePlan


def to_scene_views(scenes: list[ScenePlan], places: list[Place], characters: list[Character]) -> list[SceneView]:
    """Replace the ids of places and characters with their names, so a small model can read and copy them."""
    place_names = {place.id: place.name for place in places}
    character_names = {character.id: full_name(character) for character in characters}
    return [
        SceneView(
            number=number,
            place=place_names.get(scene.place_id, ""),
            place_notes=scene.place_notes,
            characters=[character_names[character_id] for character_id in scene.character_ids if character_id in character_names],
            what_happens=scene.what_happens,
        )
        for number, scene in enumerate(scenes, start=1)
    ]


def add_new_places(board: SceneBoard, places: list[Place]) -> list[Place]:
    """Return the places with every place the model proposed or named that is not in the list yet."""
    places = list(places)
    known = {_normalize(place.name) for place in places}
    drafts = {_normalize(draft.name): draft for draft in board.new_places}

    for name in [draft.name for draft in board.new_places] + [scene.place for scene in board.scenes]:
        key = _normalize(name)
        if not key or key in known:
            continue
        draft = drafts.get(key)
        places.append(Place(
            id=str(uuid4()),
            name=name.strip(),
            description=draft.description if draft else "",
            significance=draft.significance if draft else "",
        ))
        known.add(key)
    return places


def to_scene_plans(views: list[SceneView], places: list[Place], characters: list[Character]) -> list[ScenePlan]:
    """Replace the names the model wrote with ids; unknown characters are dropped, unknown places stay empty."""
    place_ids = {_normalize(place.name): place.id for place in places}
    return [
        ScenePlan(
            place_id=place_ids.get(_normalize(view.place), ""),
            place_notes=view.place_notes,
            character_ids=_unique([
                character_id
                for name in view.characters
                if (character_id := _find_character(name, characters))
            ]),
            what_happens=view.what_happens,
        )
        for view in views
    ]


def to_scenes(plans: list[ScenePlan]) -> list[Scene]:
    """Number new draft scenes without plans in the order of the list."""
    return [Scene(number=number, **plan.model_dump()) for number, plan in enumerate(plans, start=1)]


def full_name(character: Character) -> str:
    """Return the name and surname of a character as the model sees them."""
    return f"{character.name} {character.surname}".strip()


def _find_character(name: str, characters: list[Character]) -> str:
    """Return the id of the character with this full or first name, or an empty string if it is not clear."""
    key = _normalize(name)
    by_full_name = [character.id for character in characters if _normalize(full_name(character)) == key]
    if len(by_full_name) == 1:
        return by_full_name[0]
    by_name = [character.id for character in characters if _normalize(character.name) == key]
    return by_name[0] if len(by_name) == 1 else ""


def _unique(ids: list[str]) -> list[str]:
    """Remove repeated ids and keep the order."""
    return list(dict.fromkeys(ids))


def _normalize(value: str) -> str:
    """Make names comparable regardless of case and surrounding spaces."""
    return value.strip().casefold()
