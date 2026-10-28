import json

from anton.application.agents.chat_edit_agent import ChatEditAgent, ChatEditResult, ChatMessage
from anton.domain.models import Act, ActSummary, Cast, DramaticFunction, Outline, StoryBible
from anton.errors import ActNotFoundError, CastNotFoundError, StoryNotFoundError, StoryOrderError
from anton.infrastructure.storage import CastRepository, StoryRepository


OUTLINE_CAST_FIELDS = {
    "name", "surname", "age", "occupation_social_role",
    "dramatic_role", "goal", "internal_conflict",
}
ACT_CAST_FIELDS = {"name", "surname", "dramatic_role", "goal"}
# There is one play at a time, so every page has one conversation.
OUTLINE_THREAD = "outline"
ACTS_THREAD = "acts"


class StoryService:
    """Build the Story Bible of the play step by step: outline, acts, scenes and the text of every act."""

    def __init__(
        self,
        story_repository: StoryRepository,
        cast_repository: CastRepository,
        outline_agent: ChatEditAgent[Outline],
        acts_agent: ChatEditAgent[list[ActSummary]],
    ) -> None:
        """Initialize the service with the repositories it reads and extends and the agents of its pages."""
        self.story_repository = story_repository
        self.cast_repository = cast_repository
        self.outline_agent = outline_agent
        self.acts_agent = acts_agent

    async def start_play(self, user_input: str) -> None:
        """Start a new Story Bible from the user's initial input and forget the chats about the previous play."""
        self.story_repository.save(StoryBible(user_input=user_input))
        await self.outline_agent.forget(OUTLINE_THREAD)
        await self.acts_agent.forget(ACTS_THREAD)

    def get_story(self) -> StoryBible:
        """Return the saved Story Bible."""
        story = self.story_repository.load()
        if story is None:
            raise StoryNotFoundError("No play has been started yet.")
        return story

    async def generate_outline(self) -> StoryBible:
        """Generate the outline of the whole play from the user's initial input and the cast."""
        story = self.get_story()
        _require_no_outline(story)

        outline = await self.outline_agent.generate(
            OUTLINE_THREAD, {"idea": story.user_input, "cast": _cast_json(self._get_cast(), OUTLINE_CAST_FIELDS)},
        )

        # Another request may have saved the Story Bible while the outline was generated.
        story = self.get_story()
        _require_no_outline(story)
        story.outline = outline
        self.story_repository.save(story)
        return story

    def edit_outline(self, outline: Outline) -> StoryBible:
        """Replace the outline with the one the user edited by hand."""
        story = self._get_story_with_outline()
        story.outline = outline
        self.story_repository.save(story)
        return story

    async def revise_outline(self, outline: Outline, message: str) -> ChatEditResult[Outline]:
        """Send the user's message with the outline from their form to the outline agent; nothing is saved."""
        self._get_story_with_outline()
        return await self.outline_agent.send(OUTLINE_THREAD, outline, message)

    async def outline_history(self) -> list[ChatMessage]:
        """Return the chat history with the outline agent."""
        return await self.outline_agent.history(OUTLINE_THREAD)

    async def generate_acts(self) -> StoryBible:
        """Generate the summary and dramatic function of every act from the outline and the cast."""
        story = self._get_story_with_outline()
        _require_acts_not_approved(story)

        summaries = await self.acts_agent.generate(
            ACTS_THREAD,
            {"outline": story.outline.model_dump_json(indent=2), "cast": _cast_json(self._get_cast(), ACT_CAST_FIELDS)},
        )

        story = self._get_story_with_outline()
        _require_acts_not_approved(story)
        story.acts = [Act(**summary.model_dump()) for summary in summaries]
        story.acts_built_from_outline = story.outline.model_copy()
        self.story_repository.save(story)
        return story

    def edit_act(self, number: int, summary: str, dramatic_function: DramaticFunction) -> StoryBible:
        """Replace the summary and dramatic function of an act with the ones the user edited by hand."""
        story = self.get_story()
        act = _find_act(story, number)
        act.summary = summary
        act.dramatic_function = dramatic_function
        self.story_repository.save(story)
        return story

    async def revise_acts(self, acts: list[ActSummary], message: str) -> ChatEditResult[list[ActSummary]]:
        """Send the user's message with the acts from their form to the acts agent; nothing is saved."""
        story = self._get_story_with_acts()
        return await self.acts_agent.send(ACTS_THREAD, acts, message, context={"synopsis": story.outline.synopsis})

    async def acts_history(self) -> list[ChatMessage]:
        """Return the chat history with the acts agent."""
        return await self.acts_agent.history(ACTS_THREAD)

    def approve_acts(self) -> StoryBible:
        """Approve the acts, so the structure of the first act can be built."""
        story = self._get_story_with_acts()
        story.acts_approved = True
        self.story_repository.save(story)
        return story

    def _get_story_with_outline(self) -> StoryBible:
        """Return the saved Story Bible and make sure its outline exists."""
        story = self.get_story()
        if story.outline is None:
            raise StoryOrderError("The outline has not been generated yet.")
        return story

    def _get_story_with_acts(self) -> StoryBible:
        """Return the saved Story Bible and make sure its acts exist."""
        story = self._get_story_with_outline()
        if not story.acts:
            raise StoryOrderError("The acts have not been generated yet.")
        return story

    def _get_cast(self) -> Cast:
        """Return the saved cast, which every step of the Story Bible builds on."""
        cast = self.cast_repository.load()
        if cast is None or not cast.characters:
            raise CastNotFoundError("No cast has been generated yet.")
        return cast


def _require_no_outline(story: StoryBible) -> None:
    """Reject generating the outline a second time; it can only be edited or revised."""
    if story.outline is not None:
        raise StoryOrderError("The outline already exists. Edit it or ask the agent to revise it.")


def _require_acts_not_approved(story: StoryBible) -> None:
    """Reject generating the acts again once they are approved; then they can only be edited."""
    if story.acts_approved:
        raise StoryOrderError("The acts are already approved. Edit them instead.")


def _find_act(story: StoryBible, number: int) -> Act:
    """Return the act with the given number."""
    for act in story.acts:
        if act.number == number:
            return act
    raise ActNotFoundError(f"Act {number} is not in the Story Bible.")


def _cast_json(cast: Cast, fields: set[str]) -> str:
    """Write the given fields of every character as a JSON array."""
    return json.dumps(
        [character.model_dump(include=fields) for character in cast.characters],
        ensure_ascii=False,
        indent=2,
    )

