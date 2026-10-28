from typing import Annotated

from fastapi import APIRouter, Body, Request
from pydantic import BaseModel, Field

from anton.api.dependencies import StoryServiceDep
from anton.api.disconnect import cancel_on_disconnect
from anton.application.agents.chat_edit_agent import ChatMessage
from anton.domain.models import ActSummary, DramaticFunction, Outline, StoryBible


router = APIRouter(prefix="/story", tags=["story"])


class OutlineReviseRequest(BaseModel):
    """Represent a chat message about the outline together with the outline from the user's form."""

    message: str = Field(min_length=1)
    outline: Outline


class OutlineRevision(BaseModel):
    """Represent the answer of the outline agent and the outline as it sees it now."""

    reply: str
    outline: Outline


class ActsReviseRequest(BaseModel):
    """Represent a chat message about the acts together with the acts from the user's form."""

    message: str = Field(min_length=1)
    acts: list[ActSummary] = Field(min_length=1)


class ActsRevision(BaseModel):
    """Represent the answer of the acts agent and the acts as it sees them now."""

    reply: str
    acts: list[ActSummary]


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
