from typing import Annotated

from fastapi import APIRouter, Body, Request

from anton.api.dependencies import StoryServiceDep
from anton.api.disconnect import cancel_on_disconnect
from anton.domain.models import Chat, ChatReply, DramaticFunction, Outline, StoryBible


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


@router.post("/outline/chat")
async def revise_outline(
    message: Annotated[str, Body(embed=True, min_length=1)],
    service: StoryServiceDep,
    request: Request,
) -> ChatReply:
    """Revise the outline as the user asks in the outline chat; stop generating if the client cancels."""
    return await cancel_on_disconnect(request, service.revise_outline(message))


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


@router.post("/acts/chat")
async def revise_act(
    message: Annotated[str, Body(embed=True, min_length=1)],
    service: StoryServiceDep,
    request: Request,
) -> ChatReply:
    """Revise the act the user names in the acts chat; stop generating if the client cancels."""
    return await cancel_on_disconnect(request, service.revise_act(message))


@router.post("/acts/approve")
async def approve_acts(service: StoryServiceDep) -> StoryBible:
    """Approve the acts, so the structure of the first act can be built."""
    return service.approve_acts()


@router.get("/chats/{chat_id}")
async def get_chat(chat_id: str, service: StoryServiceDep) -> Chat:
    """Return all messages of the chat of a page, e.g. "outline"."""
    return service.get_chat(chat_id)
