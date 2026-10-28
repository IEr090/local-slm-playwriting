import asyncio
import json
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from anton.application.agent_chat import ChatMessage, to_chat_messages
from anton.application.llm_schemas.outline_generation import GeneratedOutline, OutlineChatTurn
from anton.application.mappers.outline_mapper import to_outline
from anton.domain.models import Outline
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


# There is one play at a time, so there is one conversation about its outline.
THREAD = {"configurable": {"thread_id": "outline"}}


class OutlineAgentState(TypedDict):
    """Hold the outline, what it is generated from and the chat history of the outline agent."""

    # add_messages appends new messages to the history instead of replacing it.
    messages: Annotated[list[AnyMessage], add_messages]
    idea: str
    cast: str
    outline: Outline | None
    changes: str | None
    # The reply is held back until the agreed changes are applied.
    pending_reply: str | None


class OutlineAgentReply(BaseModel):
    """Represent the answer of the outline agent and the outline as it sees it now."""

    reply: str
    outline: Outline


def create_outline_checkpointer() -> InMemorySaver:
    """Create the in-memory store of the conversation that holds the outline in its state."""
    serde = JsonPlusSerializer(allowed_msgpack_modules=[("anton.domain.models.story", "Outline")])
    return InMemorySaver(serde=serde)


class OutlineAgent:
    """Write the outline of the play and then chat with the user about it."""

    def __init__(self, client: SLMClient, checkpointer: BaseCheckpointSaver) -> None:
        """Initialize the agent with a small language model client and a store of the conversation."""
        self.client = client
        self.checkpointer = checkpointer
        self.graph = self._build_graph(checkpointer)
        # Overlapping runs would resume from the same interrupt and lose a turn of the history.
        self._lock = asyncio.Lock()

    async def generate(self, idea: str, cast: str) -> Outline:
        """Start a new conversation by writing the outline from the user's idea and the cast."""
        async with self._lock:
            await self.checkpointer.adelete_thread("outline")
            result = await self.graph.ainvoke(
                {"messages": [], "idea": idea, "cast": cast, "outline": None, "changes": None, "pending_reply": None},
                THREAD,
            )
            return result["outline"]

    async def send(self, outline: Outline, message: str) -> OutlineAgentReply:
        """Send the user's message with the outline from their form and return the agent's answer."""
        async with self._lock:
            state = await self.graph.aget_state(THREAD)
            if state.interrupts:
                result = await self.graph.ainvoke(Command(resume={"message": message, "outline": outline}), THREAD)
            else:
                # No conversation yet (e.g. after a restart), or the previous run failed before pausing.
                result = await self.graph.ainvoke(
                    {
                        "messages": [HumanMessage(message)], "idea": "", "cast": "",
                        "outline": outline, "changes": None, "pending_reply": None,
                    },
                    THREAD,
                )
            return OutlineAgentReply(reply=result["__interrupt__"][0].value, outline=result["outline"])

    async def history(self) -> list[ChatMessage]:
        """Return the chat history about the outline, or an empty list if there is none."""
        state = await self.graph.aget_state(THREAD)
        return to_chat_messages(state.values.get("messages", []))

    async def forget(self) -> None:
        """Forget the conversation, e.g. when a new play is started."""
        async with self._lock:
            await self.checkpointer.adelete_thread("outline")

    def _build_graph(self, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
        """Build the graph that writes the outline, chats about it, applies agreed changes and waits for the user."""
        graph = StateGraph(OutlineAgentState)
        graph.add_node("generate", self._generate)
        graph.add_node("chat", self._chat)
        graph.add_node("edit", self._edit)
        graph.add_node("wait_user", self._wait_user)
        graph.add_conditional_edges(START, self._at_start, ["generate", "chat"])
        graph.add_edge("generate", "wait_user")
        graph.add_conditional_edges("chat", self._after_chat, ["edit", "wait_user"])
        graph.add_edge("edit", "wait_user")
        graph.add_edge("wait_user", "chat")
        return graph.compile(checkpointer=checkpointer)

    def _at_start(self, state: OutlineAgentState) -> str:
        """Write the outline first if there is none yet, otherwise answer the user's message."""
        return "generate" if state["outline"] is None else "chat"

    async def _generate(self, state: OutlineAgentState) -> dict:
        """Write the outline of the whole play from the user's idea and the cast."""
        generated = await self.client.generate(
            system_prompt=load_prompt("outline_generation.md"),
            user_prompt=f"# IDEA\n\n{state['idea']}\n\n# CAST\n\n{state['cast']}",
            response_model=GeneratedOutline,
            think=True,
        )
        return {"outline": to_outline(generated)}

    async def _chat(self, state: OutlineAgentState) -> dict:
        """Let the model answer the user and say whether changes were agreed."""
        # The last message is kept apart from the history, so a small model answers it instead of continuing the list.
        *history, last = state["messages"]
        user_prompt = json.dumps(
            {
                "outline": state["outline"].model_dump(),
                "history": [
                    {"speaker": "playwright" if isinstance(message, HumanMessage) else "dramaturg", "text": message.content}
                    for message in history
                ],
                "playwright_message": last.content,
            },
            ensure_ascii=False,
        )
        turn = await self.client.generate(
            system_prompt=load_prompt("outline_chat.md"),
            user_prompt=user_prompt,
            response_model=OutlineChatTurn,
            think=False,
        )
        changes = (turn.apply_changes or "").strip() or None
        if changes:
            return {"changes": changes, "pending_reply": turn.reply}
        return {"messages": [AIMessage(turn.reply)], "changes": None, "pending_reply": None}

    def _after_chat(self, state: OutlineAgentState) -> str:
        """Go on to the edit if changes were agreed, otherwise wait for the user."""
        return "edit" if state["changes"] else "wait_user"

    async def _edit(self, state: OutlineAgentState) -> dict:
        """Apply the agreed changes to the outline."""
        edited = await self.client.generate(
            system_prompt=load_prompt("outline_edit.md"),
            user_prompt=json.dumps({"outline": state["outline"].model_dump(), "changes": state["changes"]}, ensure_ascii=False),
            response_model=GeneratedOutline,
            think=False,
        )
        return {
            "outline": to_outline(edited),
            "changes": None,
            "pending_reply": None,
            "messages": [AIMessage(state["pending_reply"])],
        }

    def _wait_user(self, state: OutlineAgentState) -> dict:
        """Pause until the user answers, then take their message and the outline from their form."""
        # Right after the outline is written there is no answer to show yet.
        answer = interrupt(state["messages"][-1].content if state["messages"] else "")
        return {"messages": [HumanMessage(answer["message"])], "outline": answer["outline"]}
