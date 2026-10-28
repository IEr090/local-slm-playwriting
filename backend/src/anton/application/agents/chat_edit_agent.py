import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Annotated, Any, Generic, Literal, Protocol, TypedDict, TypeVar

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command, interrupt
from pydantic import BaseModel

from anton.application.llm_schemas.chat_turn import ChatTurn
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


D = TypeVar("D")

# The domain models the graph state may hold; the checkpointer refuses to restore any other class.
STATE_MODELS = [
    ("anton.domain.models.character", "Character"),
    ("anton.domain.models.character", "CharacterHistoryEntry"),
    ("anton.domain.models.character", "Relationship"),
    ("anton.domain.models.story", "Outline"),
    ("anton.domain.models.story", "ActSummary"),
    ("anton.domain.models.story", "PlaceDraft"),
    ("anton.domain.models.story", "SceneText"),
    ("anton.application.agents.scene_targets", "SceneBoard"),
    ("anton.application.agents.scene_targets", "SceneView"),
]


class EditTarget(Protocol[D]):
    """Describe what an editing agent works on: how the model sees it and how agreed changes are applied."""

    name: str
    """Key under which the model sees the data, e.g. "outline"."""
    chat_prompt: str
    edit_prompt: str
    edit_schema: type[BaseModel]

    def view(self, data: D) -> Any:
        """Return the part of the data the model may see and change, ready for JSON."""
        ...

    def apply(self, data: D, edited: BaseModel) -> D:
        """Return the data with the model's edit applied."""
        ...


class GeneratingTarget(EditTarget[D], Protocol):
    """Describe an editing target that the agent also writes first, before the chat starts."""

    generate_prompt: str
    generate_schema: type[BaseModel]

    def generate_input(self, source: dict[str, str]) -> str:
        """Return the user prompt that the data is generated from."""
        ...

    def from_generated(self, generated: BaseModel) -> D:
        """Turn the model's answer into the data."""
        ...


class ChatMessage(BaseModel):
    """Represent one message of the chat with an agent."""

    role: Literal["user", "assistant"]
    content: str


@dataclass
class ChatEditResult(Generic[D]):
    """Represent the answer of an agent and the data as it sees it now."""

    reply: str
    data: D


class ChatEditState(TypedDict):
    """Hold the data being edited, what it is built from and the chat history about it."""

    # add_messages appends new messages to the history instead of replacing it.
    messages: Annotated[list[AnyMessage], add_messages]
    data: Any
    # What the data is generated from, e.g. the user's idea and the cast; empty when nothing is generated.
    source: dict[str, str]
    # What the model reads but never changes, e.g. the synopsis while the acts are edited.
    context: dict[str, Any]
    changes: str | None
    # The reply is held back until the agreed changes are applied.
    pending_reply: str | None


def create_checkpointer() -> InMemorySaver:
    """Create the in-memory store of conversations that may hold domain models in their state."""
    return InMemorySaver(serde=JsonPlusSerializer(allowed_msgpack_modules=STATE_MODELS))


class ChatEditAgent(Generic[D]):
    """Chat with the user about one piece of the play, apply agreed changes and optionally write it first.

    The same graph serves every page; the target says what is edited. One conversation per thread id.
    """

    def __init__(self, client: SLMClient, target: EditTarget[D], checkpointer: BaseCheckpointSaver) -> None:
        """Initialize the agent with a small language model client, what it edits and a store of conversations."""
        self.client = client
        self.target = target
        self.checkpointer = checkpointer
        self.graph = self._build_graph(checkpointer)
        # Overlapping runs would resume from the same interrupt and lose a turn of the history.
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    async def generate(self, thread_id: str, source: dict[str, str]) -> D:
        """Start a new conversation by writing the data from its source."""
        async with self._locks[thread_id]:
            await self.checkpointer.adelete_thread(thread_id)
            result = await self.graph.ainvoke(
                {"messages": [], "data": None, "source": source, "context": {}, "changes": None, "pending_reply": None},
                _config(thread_id),
            )
            return result["data"]

    async def send(self, thread_id: str, data: D, message: str, context: dict[str, Any] | None = None) -> ChatEditResult[D]:
        """Send the user's message with the data from their form and return the agent's answer."""
        context = context or {}
        config = _config(thread_id)
        async with self._locks[thread_id]:
            state = await self.graph.aget_state(config)
            if state.interrupts:
                answer = {"message": message, "data": data, "context": context}
                result = await self.graph.ainvoke(Command(resume=answer), config)
            else:
                # No conversation yet (e.g. after a restart), or the previous run failed before pausing.
                result = await self.graph.ainvoke(
                    {
                        "messages": [HumanMessage(message)], "data": data, "source": {}, "context": context,
                        "changes": None, "pending_reply": None,
                    },
                    config,
                )
            return ChatEditResult(reply=result["__interrupt__"][0].value, data=result["data"])

    async def history(self, thread_id: str) -> list[ChatMessage]:
        """Return the chat history of the thread, or an empty list if there is none."""
        state = await self.graph.aget_state(_config(thread_id))
        return [
            ChatMessage(role="user" if isinstance(message, HumanMessage) else "assistant", content=message.content)
            for message in state.values.get("messages", [])
        ]

    async def forget(self, thread_id: str) -> None:
        """Forget the conversation of the thread, e.g. when a new play is started."""
        async with self._locks[thread_id]:
            await self.checkpointer.adelete_thread(thread_id)

    def _build_graph(self, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
        """Build the graph that writes the data, chats about it, applies agreed changes and waits for the user."""
        graph = StateGraph(ChatEditState)
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

    def _at_start(self, state: ChatEditState) -> str:
        """Write the data first if there is none yet, otherwise answer the user's message."""
        return "generate" if state["data"] is None else "chat"

    async def _generate(self, state: ChatEditState) -> dict:
        """Write the data from its source; only targets that can be generated get here."""
        target: GeneratingTarget[D] = self.target
        generated = await self.client.generate(
            system_prompt=load_prompt(target.generate_prompt),
            user_prompt=target.generate_input(state["source"]),
            response_model=target.generate_schema,
            think=True,
        )
        return {"data": target.from_generated(generated)}

    async def _chat(self, state: ChatEditState) -> dict:
        """Let the model answer the user and say whether changes were agreed."""
        # The last message is kept apart from the history, so a small model answers it instead of continuing the list.
        *history, last = state["messages"]
        user_prompt = json.dumps(
            {
                **state["context"],
                self.target.name: self.target.view(state["data"]),
                "history": [
                    {"speaker": "playwright" if isinstance(message, HumanMessage) else "dramaturg", "text": message.content}
                    for message in history
                ],
                "playwright_message": last.content,
            },
            ensure_ascii=False,
        )
        turn = await self.client.generate(
            system_prompt=load_prompt(self.target.chat_prompt),
            user_prompt=user_prompt,
            response_model=ChatTurn,
            think=False,
        )
        changes = (turn.apply_changes or "").strip() or None
        if changes:
            return {"changes": changes, "pending_reply": turn.reply}
        return {"messages": [AIMessage(turn.reply)], "changes": None, "pending_reply": None}

    def _after_chat(self, state: ChatEditState) -> str:
        """Go on to the edit if changes were agreed, otherwise wait for the user."""
        return "edit" if state["changes"] else "wait_user"

    async def _edit(self, state: ChatEditState) -> dict:
        """Apply the agreed changes to the data."""
        edited = await self.client.generate(
            system_prompt=load_prompt(self.target.edit_prompt),
            user_prompt=json.dumps(
                {self.target.name: self.target.view(state["data"]), "changes": state["changes"]},
                ensure_ascii=False,
            ),
            response_model=self.target.edit_schema,
            think=False,
        )
        return {
            "data": self.target.apply(state["data"], edited),
            "changes": None,
            "pending_reply": None,
            "messages": [AIMessage(state["pending_reply"])],
        }

    def _wait_user(self, state: ChatEditState) -> dict:
        """Pause until the user answers, then take their message and the data and context from their form."""
        # Right after the data is written there is no answer to show yet.
        answer = interrupt(state["messages"][-1].content if state["messages"] else "")
        return {"messages": [HumanMessage(answer["message"])], "data": answer["data"], "context": answer["context"]}


def _config(thread_id: str) -> dict:
    """Return the graph config that selects the conversation of the thread."""
    return {"configurable": {"thread_id": thread_id}}
