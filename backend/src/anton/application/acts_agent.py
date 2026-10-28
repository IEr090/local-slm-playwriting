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
from anton.application.llm_schemas.act_generation import ActsChatTurn, EditedActs, GeneratedActs
from anton.application.mappers.act_mapper import apply_edited_acts, to_act_summaries
from anton.domain.models import ActSummary
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient


# There is one play at a time, so there is one conversation about its acts.
THREAD = {"configurable": {"thread_id": "acts"}}


class ActsAgentState(TypedDict):
    """Hold the acts, what they are generated from and the chat history of the acts agent."""

    # add_messages appends new messages to the history instead of replacing it.
    messages: Annotated[list[AnyMessage], add_messages]
    outline: str
    cast: str
    synopsis: str
    acts: list[ActSummary] | None
    changes: str | None
    # The reply is held back until the agreed changes are applied.
    pending_reply: str | None


class ActsAgentReply(BaseModel):
    """Represent the answer of the acts agent and the acts as it sees them now."""

    reply: str
    acts: list[ActSummary]


def create_acts_checkpointer() -> InMemorySaver:
    """Create the in-memory store of the conversation that holds the acts in its state."""
    serde = JsonPlusSerializer(allowed_msgpack_modules=[("anton.domain.models.story", "ActSummary")])
    return InMemorySaver(serde=serde)


class ActsAgent:
    """Divide the outline into acts and then chat with the user about them."""

    def __init__(self, client: SLMClient, checkpointer: BaseCheckpointSaver) -> None:
        """Initialize the agent with a small language model client and a store of the conversation."""
        self.client = client
        self.checkpointer = checkpointer
        self.graph = self._build_graph(checkpointer)
        # Overlapping runs would resume from the same interrupt and lose a turn of the history.
        self._lock = asyncio.Lock()

    async def generate(self, outline: str, cast: str) -> list[ActSummary]:
        """Start a new conversation by writing the summary of every act from the outline and the cast."""
        async with self._lock:
            await self.checkpointer.adelete_thread("acts")
            result = await self.graph.ainvoke(
                {
                    "messages": [], "outline": outline, "cast": cast, "synopsis": "",
                    "acts": None, "changes": None, "pending_reply": None,
                },
                THREAD,
            )
            return result["acts"]

    async def send(self, synopsis: str, acts: list[ActSummary], message: str) -> ActsAgentReply:
        """Send the user's message with the acts from their form and return the agent's answer."""
        async with self._lock:
            state = await self.graph.aget_state(THREAD)
            answer = {"message": message, "synopsis": synopsis, "acts": acts}
            if state.interrupts:
                result = await self.graph.ainvoke(Command(resume=answer), THREAD)
            else:
                # No conversation yet (e.g. after a restart), or the previous run failed before pausing.
                result = await self.graph.ainvoke(
                    {
                        "messages": [HumanMessage(message)], "outline": "", "cast": "", "synopsis": synopsis,
                        "acts": acts, "changes": None, "pending_reply": None,
                    },
                    THREAD,
                )
            return ActsAgentReply(reply=result["__interrupt__"][0].value, acts=result["acts"])

    async def history(self) -> list[ChatMessage]:
        """Return the chat history about the acts, or an empty list if there is none."""
        state = await self.graph.aget_state(THREAD)
        return to_chat_messages(state.values.get("messages", []))

    async def forget(self) -> None:
        """Forget the conversation, e.g. when a new play is started."""
        async with self._lock:
            await self.checkpointer.adelete_thread("acts")

    def _build_graph(self, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
        """Build the graph that writes the acts, chats about them, applies agreed changes and waits for the user."""
        graph = StateGraph(ActsAgentState)
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

    def _at_start(self, state: ActsAgentState) -> str:
        """Write the acts first if there are none yet, otherwise answer the user's message."""
        return "generate" if state["acts"] is None else "chat"

    async def _generate(self, state: ActsAgentState) -> dict:
        """Write the summary and dramatic function of every act from the outline and the cast."""
        generated = await self.client.generate(
            system_prompt=load_prompt("act_generation.md"),
            user_prompt=f"# OUTLINE\n\n{state['outline']}\n\n# CAST\n\n{state['cast']}",
            response_model=GeneratedActs,
            think=True,
        )
        return {"acts": to_act_summaries(generated.root)}

    async def _chat(self, state: ActsAgentState) -> dict:
        """Let the model answer the user and say whether changes were agreed."""
        # The last message is kept apart from the history, so a small model answers it instead of continuing the list.
        *history, last = state["messages"]
        user_prompt = json.dumps(
            {
                "synopsis": state["synopsis"],
                "acts": [act.model_dump() for act in state["acts"]],
                "history": [
                    {"speaker": "playwright" if isinstance(message, HumanMessage) else "dramaturg", "text": message.content}
                    for message in history
                ],
                "playwright_message": last.content,
            },
            ensure_ascii=False,
        )
        turn = await self.client.generate(
            system_prompt=load_prompt("acts_chat.md"),
            user_prompt=user_prompt,
            response_model=ActsChatTurn,
            think=False,
        )
        changes = (turn.apply_changes or "").strip() or None
        if changes:
            return {"changes": changes, "pending_reply": turn.reply}
        return {"messages": [AIMessage(turn.reply)], "changes": None, "pending_reply": None}

    def _after_chat(self, state: ActsAgentState) -> str:
        """Go on to the edit if changes were agreed, otherwise wait for the user."""
        return "edit" if state["changes"] else "wait_user"

    async def _edit(self, state: ActsAgentState) -> dict:
        """Apply the agreed changes to the acts they are about."""
        edited = await self.client.generate(
            system_prompt=load_prompt("acts_edit.md"),
            user_prompt=json.dumps(
                {"acts": [act.model_dump() for act in state["acts"]], "changes": state["changes"]},
                ensure_ascii=False,
            ),
            response_model=EditedActs,
            think=False,
        )
        return {
            "acts": apply_edited_acts(state["acts"], edited.root),
            "changes": None,
            "pending_reply": None,
            "messages": [AIMessage(state["pending_reply"])],
        }

    def _wait_user(self, state: ActsAgentState) -> dict:
        """Pause until the user answers, then take their message, the synopsis and the acts from their form."""
        # Right after the acts are written there is no answer to show yet.
        answer = interrupt(state["messages"][-1].content if state["messages"] else "")
        return {"messages": [HumanMessage(answer["message"])], "synopsis": answer["synopsis"], "acts": answer["acts"]}
