import json

from anton.application.llm_schemas.character_edit import EditedCharacter
from anton.domain.models import Character
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


async def edit_character(client: SLMClient, character: Character, changes: str) -> Character:
    """Apply the agreed changes to a character with the model, keeping its id and relationships."""
    # Relationships hold ids of other characters, which the model could break.
    user_prompt = json.dumps(
        {"character": character.model_dump(exclude={"id", "relationships"}), "changes": changes},
        ensure_ascii=False,
    )
    edited = await client.generate(
        system_prompt=load_prompt("character_edit.md"),
        user_prompt=user_prompt,
        response_model=EditedCharacter,
        think=True,
    )
    return Character(id=character.id, relationships=character.relationships, **edited.model_dump())
