import json

from anton.application.llm_schemas.outline_generation import GeneratedOutline, GeneratedOutlineRevision
from anton.application.mappers.outline_mapper import changed_fields, to_outline
from anton.domain.models import Cast, Chat, ChatMessage, ChatReply, Outline, StoryBible
from anton.errors import CastNotFoundError, StoryNotFoundError, StoryOrderError
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient
from anton.infrastructure.storage import CastRepository, ChatRepository, StoryRepository


OUTLINE_CAST_FIELDS = {
    "name", "surname", "age", "occupation_social_role",
    "dramatic_role", "goal", "internal_conflict",
}
OUTLINE_CHAT = "outline"
EARLIER_MESSAGES = 2


class StoryService:
    """Build the Story Bible of the play step by step: outline, acts, scenes and the text of every act."""

    def __init__(
        self,
        client: SLMClient,
        story_repository: StoryRepository,
        cast_repository: CastRepository,
        chat_repository: ChatRepository,
    ) -> None:
        """Initialize the service with a small language model client and the repositories it reads and extends."""
        self.client = client
        self.story_repository = story_repository
        self.cast_repository = cast_repository
        self.chat_repository = chat_repository

    def start_play(self, user_input: str) -> None:
        """Start a new Story Bible from the user's initial input and forget the chats of the previous play."""
        self.story_repository.save(StoryBible(user_input=user_input))
        self.chat_repository.clear()

    def get_story(self) -> StoryBible:
        """Return the saved Story Bible."""
        story = self.story_repository.load()
        if story is None:
            raise StoryNotFoundError("No play has been started yet.")
        return story

    def get_chat(self, chat_id: str) -> Chat:
        """Return the saved chat of a page, empty if nobody wrote in it yet."""
        return self.chat_repository.load(chat_id)

    async def generate_outline(self) -> StoryBible:
        """Generate the outline of the whole play from the user's initial input and the cast."""
        story = self.get_story()
        _require_no_outline(story)

        generated = await self.client.generate(
            system_prompt=load_prompt("outline_generation.md"),
            user_prompt=_sections({"IDEA": story.user_input, "CAST": _cast_json(self._get_cast())}),
            response_model=GeneratedOutline,
            think=True,
        )

        # Another request may have saved the Story Bible while the outline was generated.
        story = self.get_story()
        _require_no_outline(story)
        story.outline = to_outline(generated)
        self.story_repository.save(story)
        return story

    def edit_outline(self, outline: Outline) -> StoryBible:
        """Replace the outline with the one the user edited by hand."""
        story = self._get_story_with_outline()
        story.outline = outline
        self.story_repository.save(story)
        return story

    async def revise_outline(self, message: str) -> ChatReply:
        """Revise the outline as the user asks in the chat and answer with one sentence on what changed."""
        story = self._get_story_with_outline()
        chat = self.chat_repository.load(OUTLINE_CHAT)

        generated = await self.client.generate(
            system_prompt=load_prompt("outline_revision.md"),
            user_prompt=_sections({
                "OUTLINE": story.outline.model_dump_json(indent=2),
                "EARLIER MESSAGES": _earlier_messages(chat),
                "REQUEST": message,
            }),
            response_model=GeneratedOutlineRevision,
            think=False,
        )
        revised = to_outline(generated.outline)

        story = self._get_story_with_outline()
        updated = changed_fields(story.outline, revised)
        story.outline = revised
        self.story_repository.save(story)

        reply = ChatMessage(
            role="assistant",
            text=generated.change_note.strip(),
            decision="revised" if updated else "noted",
            updated=updated,
        )
        self._append_to_chat(OUTLINE_CHAT, ChatMessage(role="user", text=message), reply)
        return ChatReply(story=story, reply=reply)

    def _get_story_with_outline(self) -> StoryBible:
        """Return the saved Story Bible and make sure its outline exists."""
        story = self.get_story()
        if story.outline is None:
            raise StoryOrderError("The outline has not been generated yet.")
        return story

    def _get_cast(self) -> Cast:
        """Return the saved cast, which every step of the Story Bible builds on."""
        cast = self.cast_repository.load()
        if cast is None or not cast.characters:
            raise CastNotFoundError("No cast has been generated yet.")
        return cast

    def _append_to_chat(self, chat_id: str, *messages: ChatMessage) -> None:
        """Add the request and the answer to the saved chat of the page."""
        chat = self.chat_repository.load(chat_id)
        chat.messages.extend(messages)
        self.chat_repository.save(chat)


def _require_no_outline(story: StoryBible) -> None:
    """Reject generating the outline a second time; it can only be edited or revised."""
    if story.outline is not None:
        raise StoryOrderError("The outline already exists. Edit it or ask the chat to revise it.")


def _cast_json(cast: Cast) -> str:
    """Write the fields of every character that the outline needs as a JSON array."""
    return json.dumps(
        [character.model_dump(include=OUTLINE_CAST_FIELDS) for character in cast.characters],
        ensure_ascii=False,
        indent=2,
    )


def _earlier_messages(chat: Chat) -> str:
    """Write the last messages of the chat as short lines, so the model knows what was asked before."""
    return "\n".join(f"{message.role}: {message.text}" for message in chat.messages[-EARLIER_MESSAGES:])


def _sections(sections: dict[str, str]) -> str:
    """Join the parts of a user prompt under Markdown headings, as the prompts describe them."""
    return "\n\n".join(f"# {title}\n\n{text}" for title, text in sections.items())
