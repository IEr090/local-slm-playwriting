import json

from anton.application.agents.scene_targets import SceneView
from anton.application.llm_schemas.text_generation import GeneratedHistory, GeneratedSceneText
from anton.application.mappers.text_mapper import format_lines
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


class SceneWriter:
    """Write the text of one scene and extract what it changed for the characters; single calls without a graph."""

    def __init__(self, client: SLMClient) -> None:
        """Initialize the writer with a small language model client."""
        self.client = client

    async def write(
        self,
        play: dict,
        act_summary: str,
        scene: SceneView,
        place: dict,
        characters: list[dict],
        previous_ending: str,
    ) -> str:
        """Write the dialogue and stage directions of a scene from its approved plan, in play format."""
        user_prompt = json.dumps(
            {
                "play": play,
                "act_summary": act_summary,
                "scene": scene.model_dump(),
                "place": place,
                "characters": characters,
                "previous_scene_ending": previous_ending,
            },
            ensure_ascii=False,
        )
        generated = await self.client.generate(
            system_prompt=load_prompt("scene_text.md"),
            user_prompt=user_prompt,
            response_model=GeneratedSceneText,
            think=True,
        )
        return format_lines(generated.lines)

    async def extract_history(self, scene_text: str, characters: list[str]) -> GeneratedHistory:
        """Find out what the scene changed for each character on stage."""
        return await self.client.generate(
            system_prompt=load_prompt("character_history.md"),
            user_prompt=json.dumps({"scene_text": scene_text, "characters": characters}, ensure_ascii=False),
            response_model=GeneratedHistory,
            think=False,
        )
