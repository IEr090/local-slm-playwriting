import json
import re

from anton.application.agents.scene_targets import SceneView
from anton.application.language import echoes
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
        language: str = "English",
        scenes_in_act: int = 0,
    ) -> GeneratedScenePlan:
        """Plan the scene from the act, the approved scenes before it, its place and the characters on stage."""
        user_prompt = json.dumps(
            {
                "act_summary": act_summary,
                "earlier_scenes": [item.model_dump() for item in earlier_scenes],
                "scene": scene.model_dump(exclude={"place_notes"}),
                "place": place,
                "characters": characters,
                "language": language,
                "scenes_in_act": scenes_in_act,
            },
            ensure_ascii=False,
        )
        generated = await self._plan(user_prompt)
        problem = _problem(generated, earlier_scenes)
        if problem:
            # A small model sometimes returns a phrase, its instructions or the plan of an earlier scene; one more try.
            retried = await self._plan(f"{user_prompt}\n\n{problem}")
            if not _problem(retried, earlier_scenes):
                generated = retried
        return GeneratedScenePlan(place_notes=generated.place_notes.strip(), what_happens=generated.what_happens.strip())

    async def _plan(self, user_prompt: str) -> GeneratedScenePlan:
        """Ask the model for the plan of a scene."""
        return await self.client.generate(
            system_prompt=load_prompt("scene_plan.md"),
            user_prompt=user_prompt,
            response_model=GeneratedScenePlan,
            think=True,
        )


# A plan of a few words is no plan: the text written from it fills its lines with stage directions.
MIN_PLAN_LENGTH = 150


# A plan that shares this much of its four-word phrases with an earlier one tells the same scene again.
SAME_PLAN = 0.3


def _problem(plan: GeneratedScenePlan, earlier: list[SceneView]) -> str | None:
    """Describe what is wrong with a plan, as a correction for the model; None when nothing is."""
    if _too_thin(plan):
        return "Write `what_happens` as four to six full sentences."
    if echoes(f"{plan.place_notes} {plan.what_happens}", load_prompt("scene_plan.md")):
        return "Your last answer copied the instructions or the examples. Write the plan of this scene."
    for scene in earlier:
        if _shared_phrases(plan.what_happens, scene.what_happens) >= SAME_PLAN:
            return f"Your last answer repeated scene {scene.number}. Write what happens next instead."
    return None


def _shared_phrases(text: str, earlier: str) -> float:
    """Return the share of the four-word phrases of a text that also stand in an earlier text."""
    phrases = _phrases(text)
    return len(phrases & _phrases(earlier)) / len(phrases) if phrases else 0.0


def _phrases(text: str) -> set[str]:
    """Return the four-word phrases of a text."""
    words = re.findall(r"\w+", text.casefold())
    return {" ".join(words[i:i + 4]) for i in range(len(words) - 3)}


def _too_thin(plan: GeneratedScenePlan) -> bool:
    """Tell whether a plan is too short to write a scene from, or only repeats the place notes."""
    what = plan.what_happens.strip()
    return len(what) < MIN_PLAN_LENGTH or what.casefold() == plan.place_notes.strip().casefold()
