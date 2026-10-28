from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from anton.api.dependencies import SceneServiceDep
from anton.api.disconnect import cancel_on_disconnect
from anton.application.agents.chat_edit_agent import ChatMessage
from anton.application.scene_service import SceneRevision
from anton.domain.models import Place, PlaceDraft, ScenePlan, StoryBible


router = APIRouter(prefix="/story", tags=["acts"])


class ScenesReviseRequest(BaseModel):
    """Represent a chat message on the act page together with the scenes from the user's form."""

    message: str = Field(min_length=1)
    scenes: list[ScenePlan] = Field(min_length=1)


@router.get("/places")
async def get_places(service: SceneServiceDep) -> list[Place]:
    """Return all places of the play."""
    return service.get_places()


@router.post("/places")
async def create_place(draft: PlaceDraft, service: SceneServiceDep) -> Place:
    """Create a place by hand."""
    return service.create_place(draft)


@router.post("/acts/{number}/structure/generate")
async def generate_structure(number: int, service: SceneServiceDep, request: Request) -> StoryBible:
    """Propose the scenes of the act; stop generating if the client cancels."""
    return await cancel_on_disconnect(request, service.generate_structure(number))


@router.put("/acts/{number}/scenes")
async def edit_structure(number: int, scenes: list[ScenePlan], service: SceneServiceDep) -> StoryBible:
    """Save the scenes the user reordered, cut or added by hand, in their new order."""
    return service.edit_structure(number, scenes)


@router.post("/acts/{number}/structure/revise")
async def revise_structure(number: int, body: ScenesReviseRequest, service: SceneServiceDep, request: Request) -> SceneRevision:
    """Send the user's chat message about the structure to the act agent; only new places are saved."""
    return await cancel_on_disconnect(request, service.revise_structure(number, body.scenes, body.message))


@router.post("/acts/{number}/structure/approve")
async def approve_structure(number: int, service: SceneServiceDep) -> StoryBible:
    """Approve the structure, so the plans of the scenes can be written."""
    return service.approve_structure(number)


@router.post("/acts/{number}/scenes/{scene_number}/plan")
async def plan_scene(number: int, scene_number: int, service: SceneServiceDep, request: Request) -> StoryBible:
    """Write the detailed plan of the scene; stop generating if the client cancels."""
    return await cancel_on_disconnect(request, service.plan_scene(number, scene_number))


@router.put("/acts/{number}/scenes/{scene_number}")
async def edit_scene(number: int, scene_number: int, plan: ScenePlan, service: SceneServiceDep) -> StoryBible:
    """Save the plan of a scene the user edited by hand; the scene becomes a draft again."""
    return service.edit_scene(number, scene_number, plan)


@router.post("/acts/{number}/scenes/revise")
async def revise_scenes(number: int, body: ScenesReviseRequest, service: SceneServiceDep, request: Request) -> SceneRevision:
    """Send the user's chat message about the scene plans to the act agent; only new places are saved."""
    return await cancel_on_disconnect(request, service.revise_scenes(number, body.scenes, body.message))


@router.post("/acts/{number}/scenes/{scene_number}/approve")
async def approve_scene(number: int, scene_number: int, service: SceneServiceDep) -> StoryBible:
    """Approve the plan of a scene."""
    return service.approve_scene(number, scene_number)


@router.post("/acts/{number}/scenes/{scene_number}/reopen")
async def reopen_scene(number: int, scene_number: int, service: SceneServiceDep) -> StoryBible:
    """Take back the approval of a scene."""
    return service.reopen_scene(number, scene_number)


@router.get("/acts/{number}/chat")
async def get_act_chat(number: int, service: SceneServiceDep) -> list[ChatMessage]:
    """Return the chat history of the act page."""
    return await service.act_chat(number)
