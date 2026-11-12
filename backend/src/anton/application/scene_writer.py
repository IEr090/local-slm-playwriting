import json
import logging

from anton.application.agents.scene_targets import SceneView
from anton.application.llm_schemas.text_generation import GeneratedHistory, GeneratedSceneText
from anton.application.mappers.text_mapper import format_lines
from anton.application.validators.scene_text_checks import (
    looping_phrases,
    narrated_lines,
    repeated_lines,
    unknown_speakers,
    without_repeats,
)
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


logger = logging.getLogger(__name__)


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
        language: str = "English",
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
                "language": language,
            },
            ensure_ascii=False,
        )
        generated = await self._write(user_prompt)
        problems = _problems(generated, characters)
        if problems:
            # A small model sometimes lets strangers speak, repeats itself or retells the plan; one more try.
            logger.info("Retrying scene text reason=problems problem_count=%s", len(problems))
            names = ", ".join(f"{c.get('name', '')} {c.get('surname', '')}".strip() for c in characters)
            correction = (
                f"{user_prompt}\n\nYour last answer had these problems: {' '.join(problems)} "
                f"Only these characters may speak: {names}."
            )
            retried = await self._write(correction)
            retried_problems = _problems(retried, characters)
            if len(retried_problems) < len(problems):
                generated = retried
            else:
                logger.info("Kept first scene text, retry was not better problem_count=%s", len(retried_problems))
        return format_lines(without_repeats(generated.lines))

    async def _write(self, user_prompt: str) -> GeneratedSceneText:
        """Ask the model for the lines of a scene."""
        return await self.client.generate(
            system_prompt=load_prompt("scene_text.md"),
            user_prompt=user_prompt,
            response_model=GeneratedSceneText,
            think=True,
        )

    async def extract_history(
        self, scene_text: str, characters: list[str], language: str = "English",
    ) -> GeneratedHistory:
        """Find out what the scene changed for each character on stage."""
        user_prompt = json.dumps(
            {"scene_text": scene_text, "characters": characters, "language": language},
            ensure_ascii=False,
        )
        return await self.client.generate(
            system_prompt=load_prompt("character_history.md"),
            user_prompt=user_prompt,
            response_model=GeneratedHistory,
            think=False,
        )


def _problems(generated: GeneratedSceneText, characters: list[dict]) -> list[str]:
    """Describe what is wrong with a written scene, as a correction for the model; empty when nothing is."""
    problems = []
    strangers = unknown_speakers(generated.lines, characters)
    if strangers:
        problems.append(f"Do not let {', '.join(strangers)} speak.")
    if repeated_lines(generated.lines):
        problems.append("Some lines repeat earlier lines; every line must be new.")
    loops = looping_phrases(generated.lines)
    if loops:
        problems.append(f'The phrase "{loops[0]}" comes back again and again; let the scene move on instead.')
    if narrated_lines(generated.lines, characters):
        problems.append(
            "Some speeches tell about the speaker by name like a plan; a speech is what the character says aloud."
        )
    return problems
