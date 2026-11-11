from fastapi import APIRouter
from pydantic import BaseModel, Field

from anton.api.dependencies import PlayServiceDep
from anton.domain.models import Play


router = APIRouter(prefix="/story/play", tags=["play"])


class SceneTextEdit(BaseModel):
    """Represent the new text of one scene of the finished play."""

    text: str = Field(min_length=1)


@router.get("")
async def get_play(service: PlayServiceDep) -> Play:
    """Return the whole play: title page, Dramatis Personae and every act with its scenes."""
    return service.get_play()


@router.put("/acts/{number}/scenes/{scene_number}/text")
async def edit_scene_text(number: int, scene_number: int, body: SceneTextEdit, service: PlayServiceDep) -> Play:
    """Save a final correction of one scene's text and return the updated play."""
    return service.edit_scene_text(number, scene_number, body.text)
