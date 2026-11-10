import logging

from anton.application.agents.act_chat import ActChat
from anton.application.agents.chat_edit_agent import ChatEditAgent, ChatEditResult, ChatMessage
from anton.application.language import play_language
from anton.application.mappers.cast_mapper import ACT_CAST_FIELDS, OUTLINE_CAST_FIELDS, cast_json
from anton.application.story_lookup import find_act, load_cast, load_story
from anton.application.validators.story_order import require_acts_not_approved, require_outline_open
from anton.domain.models import Act, ActSummary, DramaticFunction, Outline, StoryBible
from anton.errors import StoryOrderError
from anton.infrastructure.storage import CastRepository, StoryRepository


logger = logging.getLogger(__name__)

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
        act_chat: ActChat,
    ) -> None:
        """Initialize the service with its repositories, the agents of its pages and the act chat."""
        self.story_repository = story_repository
        self.cast_repository = cast_repository
        self.outline_agent = outline_agent
        self.acts_agent = acts_agent
        self.act_chat = act_chat

    async def start_play(self, user_input: str) -> None:
        """Start a new Story Bible from the user's initial input and forget the chats about the previous play."""
        logger.debug("Starting play user_input_length=%s", len(user_input))
        old_story = self.story_repository.load()
        if old_story is not None:
            for act in old_story.acts:
                await self.act_chat.forget(act.number)

        self.story_repository.save(StoryBible(user_input=user_input))
        await self.outline_agent.forget(OUTLINE_THREAD)
        await self.acts_agent.forget(ACTS_THREAD)
        logger.info("Started play user_input_length=%s", len(user_input))

    def get_story(self) -> StoryBible:
        """Return the saved Story Bible."""
        return load_story(self.story_repository)

    async def generate_outline(self) -> StoryBible:
        """Generate the outline of the whole play from the user's input and the cast; again until the acts exist."""
        logger.debug("Generating outline")
        story = self.get_story()
        require_outline_open(story)

        outline = await self.outline_agent.generate(
            OUTLINE_THREAD,
            {
                "idea": story.user_input,
                "cast": cast_json(load_cast(self.cast_repository), OUTLINE_CAST_FIELDS),
                "language": play_language(story.user_input),
            },
        )

        # Another request may have saved the Story Bible while the outline was generated.
        story = self.get_story()
        require_outline_open(story)
        story.outline = outline
        self.story_repository.save(story)
        logger.info("Saved generated outline")
        return story

    def edit_outline(self, outline: Outline) -> StoryBible:
        """Replace the outline with the one the user edited by hand."""
        logger.debug("Editing outline")
        story = self._get_story_with_outline()
        story.outline = outline
        self.story_repository.save(story)
        logger.info("Saved edited outline")
        return story

    async def revise_outline(self, outline: Outline, message: str) -> ChatEditResult[Outline]:
        """Send the user's message with the outline from their form to the outline agent; nothing is saved."""
        logger.debug("Revising outline message_length=%s", len(message))
        self._get_story_with_outline()
        return await self.outline_agent.send(OUTLINE_THREAD, outline, message)

    async def outline_history(self) -> list[ChatMessage]:
        """Return the chat history with the outline agent."""
        logger.debug("Reading outline history")
        return await self.outline_agent.history(OUTLINE_THREAD)

    async def generate_acts(self) -> StoryBible:
        """Generate the summary and dramatic function of every act from the outline and the cast."""
        logger.debug("Generating acts")
        story = self._get_story_with_outline()
        require_acts_not_approved(story)

        summaries = await self.acts_agent.generate(
            ACTS_THREAD,
            {
                "outline": story.outline.model_dump_json(indent=2),
                "cast": cast_json(load_cast(self.cast_repository), ACT_CAST_FIELDS),
                "language": play_language(story.user_input),
            },
        )

        story = self._get_story_with_outline()
        require_acts_not_approved(story)
        story.acts = [Act(**summary.model_dump()) for summary in summaries]
        story.acts_built_from_outline = story.outline.model_copy()
        self.story_repository.save(story)
        logger.info("Saved generated acts act_count=%s", len(story.acts))
        return story

    def edit_act(self, number: int, summary: str, dramatic_function: DramaticFunction) -> StoryBible:
        """Replace the summary and dramatic function of an act with the ones the user edited by hand."""
        logger.debug("Editing act act_number=%s", number)
        story = self.get_story()
        act = find_act(story, number)
        act.summary = summary
        act.dramatic_function = dramatic_function
        self.story_repository.save(story)
        logger.info("Saved edited act act_number=%s", number)
        return story

    async def revise_acts(self, acts: list[ActSummary], message: str) -> ChatEditResult[list[ActSummary]]:
        """Send the user's message with the acts from their form to the acts agent; nothing is saved."""
        logger.debug("Revising acts message_length=%s", len(message))
        story = self._get_story_with_acts()
        return await self.acts_agent.send(ACTS_THREAD, acts, message, context={"synopsis": story.outline.synopsis})

    async def acts_history(self) -> list[ChatMessage]:
        """Return the chat history with the acts agent."""
        logger.debug("Reading acts history")
        return await self.acts_agent.history(ACTS_THREAD)

    def approve_acts(self) -> StoryBible:
        """Approve the acts, so the structure of the first act can be built."""
        logger.debug("Approving acts")
        story = self._get_story_with_acts()
        story.acts_approved = True
        self.story_repository.save(story)
        logger.info("Approved acts")
        return story

    def _get_story_with_outline(self) -> StoryBible:
        """Return the saved Story Bible and make sure its outline exists."""
        story = self.get_story()
        if story.outline is None:
            logger.warning("Outline is not generated yet")
            raise StoryOrderError("The outline has not been generated yet.")
        return story

    def _get_story_with_acts(self) -> StoryBible:
        """Return the saved Story Bible and make sure its acts exist."""
        story = self._get_story_with_outline()
        if not story.acts:
            logger.warning("Acts are not generated yet")
            raise StoryOrderError("The acts have not been generated yet.")
        return story
