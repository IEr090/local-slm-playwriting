from typing import Literal

from pydantic import BaseModel

from anton.domain.models.story import StoryBible


ChatRole = Literal["user", "assistant"]
ChatDecision = Literal["revised", "added", "which_act", "which_scene", "noted"]


class ChatMessage(BaseModel):
    """Represent one message in the chat of a page."""

    role: ChatRole
    text: str
    about: str = ""
    decision: ChatDecision | None = None
    updated: list[str] = []


class Chat(BaseModel):
    """Represent the chat of one page, e.g. "outline", "acts" or "act-1"."""

    id: str
    messages: list[ChatMessage] = []


class ChatReply(BaseModel):
    """Represent the answer of a chat together with the Story Bible it changed."""

    story: StoryBible
    reply: ChatMessage
