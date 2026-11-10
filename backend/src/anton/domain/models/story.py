from typing import Literal

from pydantic import BaseModel, computed_field


Genre = Literal["comedy", "drama", "tragedy", "tragicomedy", "farce"]
DramaticFunction = Literal["setup", "development", "climax", "resolution"]
ActStatus = Literal["draft", "structure_approved", "scenes_approved", "text_approved"]
SceneStatus = Literal["draft", "approved"]


class Outline(BaseModel):
    """Represent the short outline of the whole play."""

    title: str
    premise: str
    genre: Genre
    tone: str
    time_and_world: str
    central_conflict: str
    synopsis: str


class PlaceDraft(BaseModel):
    """Represent a place of the play that has no id yet."""

    name: str
    description: str
    significance: str


class Place(PlaceDraft):
    """Represent a place that does not change during the play and is reused in every act."""

    id: str


class ScenePlan(BaseModel):
    """Represent what a scene is built from: where it happens, who is on stage and what happens."""

    place_id: str
    place_notes: str
    character_ids: list[str]
    what_happens: str


class Scene(ScenePlan):
    """Represent a scene inside an act; it has a plan but no text of its own."""

    number: int
    planned: bool = False
    status: SceneStatus = "draft"
    plan_built_from: list[ScenePlan] | None = None

    def to_plan(self) -> ScenePlan:
        """Keep only the plan fields of the scene."""
        return ScenePlan(**self.model_dump(include=set(ScenePlan.model_fields)))


class SceneText(BaseModel):
    """Represent the dialogue and stage directions written for one scene of an act."""

    scene_number: int
    text: str


class ActSummary(BaseModel):
    """Represent what the user edits of an act: its summary and dramatic function."""

    number: int
    summary: str
    dramatic_function: DramaticFunction


class Act(ActSummary):
    """Represent an act of the play, named by its number."""

    status: ActStatus = "draft"
    scenes: list[Scene] = []
    scene_texts: list[SceneText] = []
    scenes_built_from_summary: str | None = None
    text_built_from_scenes: list[ScenePlan] | None = None

    @computed_field
    @property
    def text(self) -> str:
        """Join the texts of all scenes into the one text of the act."""
        return "\n\n".join(f"SCENE {item.scene_number}\n\n{item.text}" for item in self.scene_texts)

    @computed_field
    @property
    def summary_changed(self) -> bool:
        """Tell whether the summary differs from the one the scenes were built from."""
        return self.scenes_built_from_summary is not None and self.scenes_built_from_summary != self.summary

    @computed_field
    @property
    def scenes_changed(self) -> bool:
        """Tell whether the scenes differ from the ones the text was written from."""
        return self.text_built_from_scenes is not None and self.text_built_from_scenes != _plans(self.scenes)

    @computed_field
    @property
    def outdated_plans(self) -> list[int]:
        """Return the numbers of scenes whose plan was written before an earlier scene changed."""
        numbers = []
        for index, scene in enumerate(self.scenes):
            if scene.plan_built_from is None:
                continue
            if scene.plan_built_from != _plans(self.scenes[:index]):
                numbers.append(scene.number)
        return numbers


class StoryBible(BaseModel):
    """Represent the shared structured state of the play that the agents read and extend."""

    user_input: str = ""
    outline: Outline | None = None
    acts: list[Act] = []
    acts_approved: bool = False
    places: list[Place] = []
    acts_built_from_outline: Outline | None = None

    @computed_field
    @property
    def outline_changed(self) -> bool:
        """Tell whether the outline differs from the one the acts were built from."""
        return self.acts_built_from_outline is not None and self.acts_built_from_outline != self.outline


def _plans(scenes: list[Scene]) -> list[ScenePlan]:
    """Keep only the plan fields of the scenes, so approving or numbering them does not count as a change."""
    return [scene.to_plan() for scene in scenes]
