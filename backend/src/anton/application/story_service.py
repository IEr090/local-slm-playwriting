import json

from anton.application.llm_schemas.act_generation import GeneratedActRevision, GeneratedActs
from anton.application.llm_schemas.outline_generation import GeneratedOutline, GeneratedOutlineRevision
from anton.application.mappers.act_mapper import changed_act_fields, to_acts
from anton.application.mappers.outline_mapper import changed_fields, to_outline
from anton.domain.models import Act, Cast, Chat, ChatMessage, ChatReply, DramaticFunction, Outline, StoryBible
from anton.errors import ActNotFoundError, CastNotFoundError, StoryNotFoundError, StoryOrderError
from anton.infrastructure.prompts import load_prompt
from anton.infrastructure.slm import SLMClient
from anton.infrastructure.storage import CastRepository, ChatRepository, StoryRepository


OUTLINE_CAST_FIELDS = {
    "name", "surname", "age", "occupation_social_role",
    "dramatic_role", "goal", "internal_conflict",
}
ACT_CAST_FIELDS = {"name", "surname", "dramatic_role", "goal"}
OUTLINE_CHAT = "outline"
ACTS_CHAT = "acts"
WHICH_ACT = 'Tell me which act to change, for example "Act Two: Margit should be crueller here".'
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
            user_prompt=_sections({"IDEA": story.user_input, "CAST": _cast_json(self._get_cast(), OUTLINE_CAST_FIELDS)}),
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

    async def generate_acts(self) -> StoryBible:
        """Generate the summary and dramatic function of every act from the outline and the cast."""
        story = self._get_story_with_outline()
        _require_acts_not_approved(story)

        generated = await self.client.generate(
            system_prompt=load_prompt("act_generation.md"),
            user_prompt=_sections({
                "OUTLINE": story.outline.model_dump_json(indent=2),
                "CAST": _cast_json(self._get_cast(), ACT_CAST_FIELDS),
            }),
            response_model=GeneratedActs,
            think=True,
        )
        acts = to_acts(generated.root)

        story = self._get_story_with_outline()
        _require_acts_not_approved(story)
        story.acts = acts
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

    async def revise_act(self, message: str) -> ChatReply:
        """Revise the act the user names in the acts chat and answer with one sentence on what changed."""
        story = self._get_story_with_acts()
        chat = self.chat_repository.load(ACTS_CHAT)

        generated = await self.client.generate(
            system_prompt=load_prompt("act_revision.md"),
            user_prompt=_sections({
                "SYNOPSIS": story.outline.synopsis,
                "ACTS": json.dumps(
                    [act.model_dump(include={"number", "dramatic_function", "summary"}) for act in story.acts],
                    ensure_ascii=False,
                    indent=2,
                ),
                "EARLIER MESSAGES": _earlier_messages(chat),
                "REQUEST": message,
            }),
            response_model=GeneratedActRevision,
            think=False,
        )

        story = self._get_story_with_acts()
        if generated.act_number not in [act.number for act in story.acts]:
            reply = ChatMessage(role="assistant", text=WHICH_ACT, decision="which_act")
            self._append_to_chat(ACTS_CHAT, ChatMessage(role="user", text=message), reply)
            return ChatReply(story=story, reply=reply)

        act = _find_act(story, generated.act_number)
        revised = act.model_copy(update={
            "summary": generated.summary.strip(),
            "dramatic_function": generated.dramatic_function,
        })
        updated = changed_act_fields(act, revised)
        story.acts[story.acts.index(act)] = revised
        self.story_repository.save(story)

        about = f"Act {act.number}"
        reply = ChatMessage(
            role="assistant",
            text=generated.change_note.strip(),
            about=about,
            decision="revised" if updated else "noted",
            updated=updated,
        )
        self._append_to_chat(ACTS_CHAT, ChatMessage(role="user", text=message, about=about), reply)
        return ChatReply(story=story, reply=reply)

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

    def _append_to_chat(self, chat_id: str, *messages: ChatMessage) -> None:
        """Add the request and the answer to the saved chat of the page."""
        chat = self.chat_repository.load(chat_id)
        chat.messages.extend(messages)
        self.chat_repository.save(chat)


def _require_no_outline(story: StoryBible) -> None:
    """Reject generating the outline a second time; it can only be edited or revised."""
    if story.outline is not None:
        raise StoryOrderError("The outline already exists. Edit it or ask the chat to revise it.")


def _require_acts_not_approved(story: StoryBible) -> None:
    """Reject generating the acts again once they are approved; then they can only be edited or revised."""
    if story.acts_approved:
        raise StoryOrderError("The acts are already approved. Edit them or ask the chat to revise one.")


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


def _earlier_messages(chat: Chat) -> str:
    """Write the last messages of the chat as short lines, so the model knows what was asked before."""
    return "\n".join(f"{message.role}: {message.text}" for message in chat.messages[-EARLIER_MESSAGES:])


def _sections(sections: dict[str, str]) -> str:
    """Join the parts of a user prompt under Markdown headings, as the prompts describe them."""
    return "\n\n".join(f"# {title}\n\n{text}" for title, text in sections.items())
