from typing import Literal

from langchain_core.messages import AnyMessage, HumanMessage
from pydantic import BaseModel


class ChatMessage(BaseModel):
    """Represent one message of the chat with an agent."""

    role: Literal["user", "assistant"]
    content: str


def to_chat_messages(messages: list[AnyMessage]) -> list[ChatMessage]:
    """Turn the graph messages into chat messages of the user and the assistant."""
    return [
        ChatMessage(role="user" if isinstance(message, HumanMessage) else "assistant", content=message.content)
        for message in messages
    ]
