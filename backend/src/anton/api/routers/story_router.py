from typing import Annotated

from fastapi import APIRouter, Body, Request

from anton.api.dependencies import StoryServiceDep
from anton.api.disconnect import cancel_on_disconnect
from anton.api.dto.story_dto import ActsReviseRequest, ActsRevision, OutlineReviseRequest, OutlineRevision
from anton.application.agents.chat_edit_agent import ChatMessage
from anton.domain.models import DramaticFunction, Outline, StoryBible


router = APIRouter(prefix="/story", tags=["story"])


@router.get("")
async def get_story(service: StoryServiceDep) -> StoryBible:
    """Return the saved Story Bible with its warning flags."""
    return service.get_story()


@router.post("/outline/generate")
async def generate_outline(service: StoryServiceDep, request: Request) -> StoryBible:
    """Generate the outline from the user's initial input and the cast; stop generating if the client cancels."""
    return await cancel_on_disconnect(request, service.generate_outline())


@router.put("/outline")
async def edit_outline(outline: Outline, service: StoryServiceDep) -> StoryBible:
    """Save the outline the user edited by hand."""
    return service.edit_outline(outline)


@router.post("/outline/revise")
async def revise_outline(body: OutlineReviseRequest, service: StoryServiceDep, request: Request) -> OutlineRevision:
    """Send the user's chat message to the outline agent; the revised outline is not saved."""
    result = await cancel_on_disconnect(request, service.revise_outline(body.outline, body.message))
    return OutlineRevision(reply=result.reply, outline=result.data)


@router.get("/outline/revise")
async def get_outline_revise_history(service: StoryServiceDep) -> list[ChatMessage]:
    """Return the chat history with the outline agent."""
    return await service.outline_history()


@router.post("/acts/generate")
async def generate_acts(service: StoryServiceDep, request: Request) -> StoryBible:
    """Generate the summary of every act from the outline; stop generating if the client cancels."""
    return await cancel_on_disconnect(request, service.generate_acts())


@router.put("/acts/{number}")
async def edit_act(
    number: int,
    summary: Annotated[str, Body(min_length=1)],
    dramatic_function: Annotated[DramaticFunction, Body()],
    service: StoryServiceDep,
) -> StoryBible:
    """Save the summary and dramatic function of an act the user edited by hand."""
    return service.edit_act(number, summary, dramatic_function)


@router.post("/acts/revise")
async def revise_acts(body: ActsReviseRequest, service: StoryServiceDep, request: Request) -> ActsRevision:
    """Send the user's chat message to the acts agent; the revised acts are not saved."""
    result = await cancel_on_disconnect(request, service.revise_acts(body.acts, body.message))
    return ActsRevision(reply=result.reply, acts=result.data)


@router.get("/acts/revise")
async def get_acts_revise_history(service: StoryServiceDep) -> list[ChatMessage]:
    """Return the chat history with the acts agent."""
    return await service.acts_history()


@router.post("/acts/approve")
async def approve_acts(service: StoryServiceDep) -> StoryBible:
    """Approve the acts, so the structure of the first act can be built."""
    return service.approve_acts()
