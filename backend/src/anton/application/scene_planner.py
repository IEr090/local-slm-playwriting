import json

from anton.application.agents.scene_targets import SceneView
from anton.application.llm_schemas.scene_generation import GeneratedScenePlan
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


class ScenePlanner:
    """Write the detailed plan of one scene; a single call without a conversation, so it needs no graph."""

    def __init__(self, client: SLMClient) -> None:
        """Initialize the planner with a small language model client."""
        self.client = client

    async def plan(
        self,
        act_summary: str,
        earlier_scenes: list[SceneView],
        scene: SceneView,
        place: dict,
        characters: list[dict],
    ) -> GeneratedScenePlan:
        """Plan the scene from the act, the approved scenes before it, its place and the characters on stage."""
        user_prompt = json.dumps(
            {
                "act_summary": act_summary,
                "earlier_scenes": [item.model_dump() for item in earlier_scenes],
                "scene": scene.model_dump(exclude={"place_notes"}),
                "place": place,
                "characters": characters,
            },
            ensure_ascii=False,
        )
        generated = await self.client.generate(
            system_prompt=load_prompt("scene_plan.md"),
            user_prompt=user_prompt,
            response_model=GeneratedScenePlan,
            think=True,
        )
        return GeneratedScenePlan(place_notes=generated.place_notes.strip(), what_happens=generated.what_happens.strip())
