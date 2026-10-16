import asyncio
import json
from collections import defaultdict
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from anton.application.llm_schemas.character_edit import EditChatTurn, EditedCharacter
from anton.domain.models import Character
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


class EditAgentState(TypedDict):
    """Hold the character being edited and the chat history of the edit agent."""

    # add_messages appends new messages to the history instead of replacing it.
    messages: Annotated[list[AnyMessage], add_messages]
    character: Character
    changes: str | None
    # The reply is held back until the agreed changes are applied.
    pending_reply: str | None


class ChatMessage(BaseModel):
    """Represent one message of the chat with the edit agent."""

    role: Literal["user", "assistant"]
    content: str


class EditAgentReply(BaseModel):
    """Represent the answer of the edit agent and the character as it sees it now."""

    reply: str
    character: Character


async def edit_character(client: SLMClient, character: Character, changes: str) -> Character:
    """Apply the agreed changes to a character with the model, keeping its id and relationships."""
    # Relationships hold ids of other characters, which the model could break.
    user_prompt = json.dumps(
        {"character": character.model_dump(exclude={"id", "relationships"}), "changes": changes},
        ensure_ascii=False,
    )
    edited = await client.generate(
        system_prompt=load_prompt("character_edit.md"),
        user_prompt=user_prompt,
        response_model=EditedCharacter,
        think=True,
    )
    return Character(id=character.id, relationships=character.relationships, **edited.model_dump())


def create_checkpointer() -> InMemorySaver:
    """Create the in-memory store of conversations that may hold characters in their state."""
    serde = JsonPlusSerializer(allowed_msgpack_modules=[("anton.domain.models.character", "Character")])
    return InMemorySaver(serde=serde)


class EditAgent:
    """Chat with the user about one character at a time; one conversation per character."""

    def __init__(self, client: SLMClient, checkpointer: BaseCheckpointSaver) -> None:
        """Initialize the agent with a small language model client and a store of conversations."""
        self.client = client
        self.graph = self._build_graph(checkpointer)
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def send(self, character: Character, message: str) -> EditAgentReply:
        """Send the user's message with the character from their form and return the agent's answer."""
        config = {"configurable": {"thread_id": character.id}}
        # Overlapping sends would resume from the same interrupt and lose a turn of the history.
        async with self._locks[character.id]:
            state = await self.graph.aget_state(config)
            if state.interrupts:
                result = await self.graph.ainvoke(Command(resume={"message": message, "character": character}), config)
            else:
                # No conversation yet, or the previous run failed before pausing; add_messages keeps the history.
                result = await self.graph.ainvoke(
                    {"messages": [HumanMessage(message)], "character": character, "changes": None, "pending_reply": None},
                    config,
                )
            return EditAgentReply(reply=result["__interrupt__"][0].value, character=result["character"])

    async def history(self, character_id: str) -> list[ChatMessage]:
        """Return the chat history about the character, or an empty list if there is none."""
        state = await self.graph.aget_state({"configurable": {"thread_id": character_id}})
        return _to_chat_messages(state.values.get("messages", []))

    def _build_graph(self, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
        """Build the graph that chats about a character, applies agreed changes and waits for the user."""
        graph = StateGraph(EditAgentState)
        graph.add_node("chat", self._chat)
        graph.add_node("edit", self._edit)
        graph.add_node("wait_user", self._wait_user)
        graph.add_edge(START, "chat")
        graph.add_conditional_edges("chat", self._after_chat, ["edit", "wait_user"])
        graph.add_edge("edit", "wait_user")
        graph.add_edge("wait_user", "chat")
        return graph.compile(checkpointer=checkpointer)

    async def _chat(self, state: EditAgentState) -> dict:
        """Let the model answer the user and say whether changes were agreed."""
        user_prompt = json.dumps(
            {
                "character": state["character"].model_dump(exclude={"id", "relationships"}),
                "messages": [message.model_dump() for message in _to_chat_messages(state["messages"])],
            },
            ensure_ascii=False,
        )
        turn = await self.client.generate(
            system_prompt=load_prompt("character_edit_chat.md"),
            user_prompt=user_prompt,
            response_model=EditChatTurn,
            think=True,
        )
        changes = (turn.apply_changes or "").strip() or None
        if changes:
            return {"changes": changes, "pending_reply": turn.reply}
        return {"messages": [AIMessage(turn.reply)], "changes": None, "pending_reply": None}

    def _after_chat(self, state: EditAgentState) -> str:
        """Go on to the edit if changes were agreed, otherwise wait for the user."""
        return "edit" if state["changes"] else "wait_user"

    async def _edit(self, state: EditAgentState) -> dict:
        """Apply the agreed changes to the character."""
        character = await edit_character(self.client, state["character"], state["changes"])
        return {
            "character": character,
            "changes": None,
            "pending_reply": None,
            "messages": [AIMessage(state["pending_reply"])],
        }

    def _wait_user(self, state: EditAgentState) -> dict:
        """Pause until the user answers, then take their message and the character from their form."""
        answer = interrupt(state["messages"][-1].content)
        return {"messages": [HumanMessage(answer["message"])], "character": answer["character"]}


def _to_chat_messages(messages: list[AnyMessage]) -> list[ChatMessage]:
    """Turn the graph messages into chat messages of the user and the assistant."""
    return [
        ChatMessage(role="user" if isinstance(message, HumanMessage) else "assistant", content=message.content)
        for message in messages
    ]
