from fastapi import APIRouter, Request

from anton.api.dependencies import SceneServiceDep, TextServiceDep
from anton.api.disconnect import cancel_on_disconnect
from anton.api.dto.act_dto import ScenesReviseRequest, TextReviseRequest
from anton.application.agents.chat_edit_agent import ChatMessage
from anton.application.scene_service import SceneRevision
from anton.application.text_service import TextRevision
from anton.domain.models import Place, PlaceDraft, ScenePlan, SceneText, StoryBible


router = APIRouter(prefix="/story", tags=["acts"])


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


@router.post("/acts/{number}/text/generate")
async def generate_text(number: int, service: TextServiceDep, request: Request) -> StoryBible:
    """Write the text of the act scene by scene; stop generating if the client cancels."""
    return await cancel_on_disconnect(request, service.generate_text(number))


@router.put("/acts/{number}/text")
async def edit_text(number: int, scene_texts: list[SceneText], service: TextServiceDep) -> StoryBible:
    """Save the scene texts the user took over from the chat."""
    return service.edit_text(number, scene_texts)


@router.post("/acts/{number}/text/revise")
async def revise_text(number: int, body: TextReviseRequest, service: TextServiceDep, request: Request) -> TextRevision:
    """Send the user's chat message about the text to the act agent; nothing is saved."""
    return await cancel_on_disconnect(request, service.revise_text(number, body.scene_texts, body.message))


@router.post("/acts/{number}/text/approve")
async def approve_text(number: int, service: TextServiceDep, request: Request) -> StoryBible:
    """Approve the text and record what it changed for the characters; stop if the client cancels."""
    return await cancel_on_disconnect(request, service.approve_text(number))


@router.get("/acts/{number}/chat")
async def get_act_chat(number: int, service: SceneServiceDep) -> list[ChatMessage]:
    """Return the chat history of the act page."""
    return await service.act_chat(number)
