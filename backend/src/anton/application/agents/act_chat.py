from langgraph.checkpoint.base import BaseCheckpointSaver

from anton.application.agents.chat_edit_agent import ChatEditAgent, ChatMessage
from anton.application.agents.scene_targets import SceneBoard, ScenesTarget, StructureTarget
from anton.application.agents.text_target import TextTarget
from anton.domain.models import SceneText
from anton.infrastructure.slm import SLMClient


class ActChat:
    """Hold the one chat of an act page, in which a different agent answers at every stage of the act.

    The structure, scene plans and text agents write into the same conversation ("act-N"), so the user sees one
    history whatever the stage. Each message sends the data of the current stage along, so the data the
    conversation holds is replaced by the agent that answers.
    """

    def __init__(self, client: SLMClient, checkpointer: BaseCheckpointSaver) -> None:
        """Create the three agents of the act page on one store of conversations."""
        self.structure: ChatEditAgent[SceneBoard] = ChatEditAgent(client, StructureTarget(), checkpointer)
        self.scenes: ChatEditAgent[SceneBoard] = ChatEditAgent(client, ScenesTarget(), checkpointer)
        self.text: ChatEditAgent[list[SceneText]] = ChatEditAgent(client, TextTarget(), checkpointer)

    async def history(self, number: int) -> list[ChatMessage]:
        """Return the chat history of the act page; any of the agents reads the same conversation."""
        return await self.structure.history(act_thread(number))

    async def forget(self, number: int) -> None:
        """Forget the chat of the act page, e.g. when the act is written anew or a new play is started."""
        await self.structure.forget(act_thread(number))


def act_thread(number: int) -> str:
    """Return the id of the conversation of an act page."""
    return f"act-{number}"
