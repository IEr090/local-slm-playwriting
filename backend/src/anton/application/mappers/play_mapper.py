from anton.domain.models import Act, Cast, Character, Play, PlayAct, PlayCastMember, PlayScene, StoryBible


def to_play(story: StoryBible, cast: Cast) -> Play:
    """Join the Story Bible and the cast into the read model of the finished play."""
    place_names = {place.id: place.name for place in story.places}

    acts = []
    for act in story.acts:
        acts.append(PlayAct(number=act.number, scenes=_to_play_scenes(act, place_names)))

    return Play(
        title=story.outline.title,
        genre=story.outline.genre,
        premise=story.outline.premise,
        time_and_world=story.outline.time_and_world,
        act_count=len(story.acts),
        cast=_to_cast_members(cast),
        acts=acts,
    )


def _to_play_scenes(act: Act, place_names: dict[str, str]) -> list[PlayScene]:
    """Return the scenes of the act in order, each with the text written for it."""
    texts = {item.scene_number: item.text for item in act.scene_texts}

    scenes = []
    for scene in act.scenes:
        scenes.append(PlayScene(
            number=scene.number,
            place_name=place_names.get(scene.place_id, ""),
            place_notes=scene.place_notes,
            text=texts.get(scene.number, ""),
        ))
    return scenes


def _to_cast_members(cast: Cast) -> list[PlayCastMember]:
    """Return a line for every character: the full name and the tagline of the card or, without it, the occupation."""
    members = []
    for character in cast.characters:
        members.append(PlayCastMember(
            character_id=character.id,
            name=f"{character.name} {character.surname}".strip(),
            description=_describe(character, cast),
        ))
    return members


def _describe(character: Character, cast: Cast) -> str:
    """Return the tagline of the character's card, or the occupation when there is no tagline."""
    card = cast.cards.get(character.id)
    if card is not None and card.tagline.strip():
        return card.tagline.strip()
    return character.occupation_social_role
