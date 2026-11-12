import json

from anton.domain.models import Cast, Scene


OUTLINE_CAST_FIELDS = {
    "name", "surname", "age", "occupation_social_role",
    "dramatic_role", "goal", "internal_conflict",
}
ACT_CAST_FIELDS = {"name", "surname", "dramatic_role", "goal"}
PLAN_CHARACTER_FIELDS = {
    "name", "surname", "age", "personality",
    "goal", "motivation", "fear_weakness", "internal_conflict",
}


def cast_json(cast: Cast, fields: set[str]) -> str:
    """Write the given fields of every character as a JSON array."""
    characters = []
    for character in cast.characters:
        characters.append(character.model_dump(include=fields))
    return json.dumps(characters, ensure_ascii=False, indent=2)


def on_stage_profiles(cast: Cast, scene: Scene, act_number: int) -> list[dict]:
    """Return the profiles of the characters on stage with what changed for them before this scene."""
    profiles = []
    for character in cast.characters:
        if character.id not in scene.character_ids:
            continue

        history = []
        for entry in character.history:
            if (entry.act_number, entry.scene_number) < (act_number, scene.number):
                history.append(entry.change)

        profile = character.model_dump(include=PLAN_CHARACTER_FIELDS)
        profile["history"] = history
        profiles.append(profile)
    return profiles
