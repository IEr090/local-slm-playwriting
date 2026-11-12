import asyncio
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
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

from anton.application.language import language_of
from anton.application.llm_schemas.chat_turn import ChatTurn
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient
from anton.infrastructure.storage.file_checkpointer import FileCheckpointer


logger = logging.getLogger(__name__)

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

    def parse_changes(self, data: D, changes: str) -> D | None:
        """Apply agreed changes written as the chat prompt asks without the model; None if they are not written so."""
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


def create_checkpointer(path: Path | None = None) -> InMemorySaver:
    """Create the store of conversations that may hold domain models in their state.

    With a path the conversations are also written to that file, so they survive a restart of the backend.
    """
    serde = JsonPlusSerializer(allowed_msgpack_modules=STATE_MODELS)
    if path is None:
        return InMemorySaver(serde=serde)
    return FileCheckpointer(path, serde=serde)


# Short answers that agree to the agent's last proposal, e.g. "yes", "ok, do it", "да, давай".
AGREEMENT = re.compile(
    r"^(yes|yeah|yep|ok|okay|sure|agreed|go ahead|do it|apply|please do|fine|ja"
    r"|да|ага|ок|окей|давай|хорошо|согласен|согласна|применяй)\b",
    re.IGNORECASE,
)
# The agent's proposals start like this (the chat prompts ask for "I suggest…"), questions do not.
PROPOSAL = re.compile(r"\b(suggest|propose|предлагаю|предложу|schlage)", re.IGNORECASE)
# A short answer is at most this many words; a longer one asks for something else as well.
AGREEMENT_MAX_WORDS = 7

NOT_UNDERSTOOD = {
    "English": "What exactly should change? Name the part and how it should be.",
    "Russian": "Что именно нужно изменить? Назовите часть и какой она должна стать.",
    "German": "Was genau soll sich ändern? Nennen Sie den Teil und wie er sein soll.",
}
APPLYING = {
    "English": "Applying the change.",
    "Russian": "Применяю изменение.",
    "German": "Ich übernehme die Änderung.",
}
NOT_APPLIED = {
    "English": "I could not apply this change. Please tell me again exactly what should change.",
    "Russian": "Не получилось применить это изменение. Скажите ещё раз, что именно нужно изменить.",
    "German": "Ich konnte die Änderung nicht übernehmen. Bitte sagen Sie noch einmal genau, was sich ändern soll.",
}


def is_proposal(text: str) -> bool:
    """Tell whether the agent's message proposes a change the playwright can agree to."""
    return bool(PROPOSAL.search(text))


def is_agreement(text: str) -> bool:
    """Tell whether a message is a short yes to the agent's last proposal."""
    return bool(AGREEMENT.match(text.strip())) and len(text.split()) <= AGREEMENT_MAX_WORDS


def _strings(value: Any) -> list[str]:
    """Collect every string of a JSON-like value, so the language of a text is judged without its keys."""
    if isinstance(value, str):
        return [value]

    items = []
    if isinstance(value, dict):
        items = list(value.values())
    elif isinstance(value, list):
        items = value

    texts = []
    for item in items:
        texts.extend(_strings(item))
    return texts


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
            initial_state = _initial_state([], None, source, {})
            result = await self.graph.ainvoke(initial_state, _config(thread_id))
            return result["data"]

    async def send(
        self, thread_id: str, data: D, message: str, context: dict[str, Any] | None = None,
    ) -> ChatEditResult[D]:
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
                initial_state = _initial_state([HumanMessage(message)], data, {}, context)
                result = await self.graph.ainvoke(initial_state, config)
            return ChatEditResult(reply=result["__interrupt__"][0].value, data=result["data"])

    async def history(self, thread_id: str) -> list[ChatMessage]:
        """Return the chat history of the thread, or an empty list if there is none."""
        state = await self.graph.aget_state(_config(thread_id))
        history = []
        for message in state.values.get("messages", []):
            role = "user" if isinstance(message, HumanMessage) else "assistant"
            history.append(ChatMessage(role=role, content=message.content))
        return history

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
        reply_language = _reply_language(state["messages"])

        user_prompt = self._chat_prompt(state, history, last, reply_language)
        turn = await self._turn_without_echo(user_prompt, last.content, reply_language)
        turn = await self._turn_in_language(user_prompt, turn, reply_language)

        changes = (turn.apply_changes or "").strip()
        if changes:
            return {"changes": changes, "pending_reply": turn.reply}

        agreed_proposal = _agreed_proposal(history, last)
        if agreed_proposal:
            # The playwright said yes but a small model asked again: apply the proposal they agreed to.
            reply = turn.reply
            if reply.rstrip().endswith("?"):
                reply = APPLYING[reply_language]
            return {"changes": agreed_proposal, "pending_reply": reply}
        return {"messages": [AIMessage(turn.reply)], "changes": None, "pending_reply": None}

    def _chat_prompt(
        self, state: ChatEditState, history: list[AnyMessage], last: AnyMessage, reply_language: str,
    ) -> str:
        """Write the input of the chat turn: the data, the context, the earlier messages and the last message."""
        view = self.target.view(state["data"])

        earlier_messages = []
        for message in history:
            earlier_messages.append({"speaker": _speaker_of(message), "text": message.content})

        text_language = language_of(" ".join(_strings(view))) or "English"
        return json.dumps(
            {
                **state["context"],
                self.target.name: view,
                "history": earlier_messages,
                "playwright_message": last.content,
                # Named in the input, because a small model follows the language of its examples otherwise.
                "reply_language": reply_language,
                "text_language": text_language,
            },
            ensure_ascii=False,
        )

    async def _turn_without_echo(self, user_prompt: str, last_text: str, reply_language: str) -> ChatTurn:
        """Ask for a chat answer; if the model only repeats the user's message, try once more and then give up."""
        turn = await self._turn(user_prompt)
        if not _same_text(turn.reply, last_text):
            return turn

        # A small model sometimes repeats the message instead of answering it: one more try with a hint.
        logger.info("Retrying chat turn reason=echo")
        hint = "Your last reply only repeated the playwright's message. Answer it instead."
        turn = await self._turn(f"{user_prompt}\n\n{hint}")
        if not _same_text(turn.reply, last_text):
            return turn

        logger.info("Chat turn still echoes, asking the user to say again")
        return ChatTurn(reply=NOT_UNDERSTOOD[reply_language], apply_changes=None)

    async def _turn_in_language(self, user_prompt: str, turn: ChatTurn, reply_language: str) -> ChatTurn:
        """Return the turn if its reply is in the user's language, else try once more with the language named."""
        if _in_language(turn.reply, reply_language):
            return turn

        # A small model often answers in the language of the outline; one more try with the language named.
        logger.info("Retrying chat turn reason=wrong_language reply_language=%s", reply_language)
        hint = f"Write `reply` in {reply_language}; only quoted new values stay in the text language."
        retried = await self._turn(f"{user_prompt}\n\n{hint}")
        if _in_language(retried.reply, reply_language):
            return retried
        return turn

    async def _turn(self, user_prompt: str) -> ChatTurn:
        """Ask the model for one chat answer."""
        return await self.client.generate(
            system_prompt=load_prompt(self.target.chat_prompt),
            user_prompt=user_prompt,
            response_model=ChatTurn,
            think=False,
        )

    def _after_chat(self, state: ChatEditState) -> str:
        """Go on to the edit if changes were agreed, otherwise wait for the user."""
        return "edit" if state["changes"] else "wait_user"

    async def _edit(self, state: ChatEditState) -> dict:
        """Apply the agreed changes: directly when they are written as the prompt asks, else by the model."""
        proposal = _last_proposal(state["messages"])
        direct_data = self._parse_directly(state, proposal)
        if direct_data is not None:
            return {
                "data": direct_data, "changes": None, "pending_reply": None,
                "messages": [AIMessage(state["pending_reply"])],
            }

        edited = await self.client.generate(
            system_prompt=load_prompt(self.target.edit_prompt),
            user_prompt=json.dumps(
                {self.target.name: self.target.view(state["data"]), "changes": state["changes"]},
                ensure_ascii=False,
            ),
            response_model=self.target.edit_schema,
            think=False,
        )
        data = self.target.apply(state["data"], edited)

        # The reply says the change is applied, which is not true when the edit changed nothing.
        if data != state["data"]:
            reply = state["pending_reply"]
        else:
            logger.info("Edit changed nothing target=%s", self.target.name)
            reply = NOT_APPLIED[_reply_language(state["messages"])]
        return {"data": data, "changes": None, "pending_reply": None, "messages": [AIMessage(reply)]}

    def _parse_directly(self, state: ChatEditState, proposal: str) -> D | None:
        """Return the data changed without the model, or None if neither the changes nor the proposal say how."""
        # The proposal the playwright agreed to states the new values too.
        for text in (state["changes"], proposal):
            parsed = self.target.parse_changes(state["data"], text)
            if parsed is not None and parsed != state["data"]:
                return parsed
        return None

    def _wait_user(self, state: ChatEditState) -> dict:
        """Pause until the user answers, then take their message and the data and context from their form."""
        # Right after the data is written there is no answer to show yet.
        answer = interrupt(state["messages"][-1].content if state["messages"] else "")
        return {"messages": [HumanMessage(answer["message"])], "data": answer["data"], "context": answer["context"]}


def _initial_state(messages: list[AnyMessage], data: Any, source: dict[str, str], context: dict[str, Any]) -> dict:
    """Return the state a run of the graph starts from."""
    return {
        "messages": messages, "data": data, "source": source, "context": context,
        "changes": None, "pending_reply": None,
    }


def _speaker_of(message: AnyMessage) -> str:
    """Name the speaker of a message as the chat prompts call them."""
    if isinstance(message, HumanMessage):
        return "playwright"
    return "dramaturg"


def _agreed_proposal(history: list[AnyMessage], last: AnyMessage) -> str:
    """Return the agent's last message if it proposed a change and the user's last message agrees to it, else ''."""
    if not history or not isinstance(history[-1], AIMessage):
        return ""
    proposal = history[-1].content
    if is_proposal(proposal) and is_agreement(last.content):
        return proposal
    return ""


def _last_proposal(messages: list[AnyMessage]) -> str:
    """Return the text of the agent's latest message, or '' if the agent has not written yet."""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message.content
    return ""


def _in_language(reply: str, language: str) -> bool:
    """Tell whether a reply is in the language, apart from quoted new values; too little text counts as yes."""
    own = re.sub(r"«[^»]*»|\"[^\"]*\"|“[^”]*”", " ", reply)
    found = language_of(own)
    return found is None or found == language


def _same_text(a: str, b: str) -> bool:
    """Tell whether two messages are the same apart from case, spaces and punctuation."""
    return _bare_text(a) == _bare_text(b)


def _bare_text(text: str) -> str:
    """Remove case, repeated spaces and punctuation from a message."""
    return re.sub(r"[\W_]+", " ", text).strip().casefold()


def _reply_language(messages: list[AnyMessage]) -> str:
    """Return the language of the playwright's latest message that is long enough to tell, English by default."""
    for message in reversed(messages):
        if not isinstance(message, HumanMessage):
            continue
        language = language_of(message.content)
        if language is not None:
            return language
    return "English"


def _config(thread_id: str) -> dict:
    """Return the graph config that selects the conversation of the thread."""
    return {"configurable": {"thread_id": thread_id}}
