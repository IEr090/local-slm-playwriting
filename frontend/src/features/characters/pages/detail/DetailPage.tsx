import { motion } from "motion/react";
import { useEffect, useState } from "react";
import { Navigate, useParams } from "react-router";
import { isEmptyProfile, missingFields, missingLabels, sameProfile } from "@/features/characters/model/validation";
import { paths } from "@/features/characters/paths";
import { ApiError } from "@/shared/api/errors";
import { useErrors } from "@/shared/errors/errors-context";
import { useCastActions, useCastState } from "@/features/characters/store/cast-context";
import { ChatPanel } from "./chat/ChatPanel";
import { DetailHeader } from "./DetailHeader";
import { FieldGrid } from "./FieldGrid";
import { LeaveDialog } from "./LeaveDialog";

/** Page "/cast/:id": character detail with live header and scrollable field cards. */
export function DetailPage() {
  const { id = "" } = useParams();
  const { loaded, cast, cards, saved, chatOpen, chats, draft, aiTypingFor, highlight } = useCastState();
  const { characterOpened, updateCharacter, leaveToGrid, saveCharacter, toggleChat, setDraft, sendRevision } =
    useCastActions();
  const { showError } = useErrors();
  // CREATE / SAVE was pressed with empty required fields: they turn red and the button stays off until filled
  const [attemptedFor, setAttemptedFor] = useState<string | null>(null);
  const [leaving, setLeaving] = useState(false);
  const index = cast.findIndex((c) => c.id === id);
  const character = cast[index];

  // a (new) character is shown: empty chat draft, chat panel closed, chat history read
  useEffect(() => {
    if (loaded) characterOpened(id);
  }, [id, loaded, characterOpened]);

  if (!loaded) return null; // the saved cast is still being read after a reload
  if (!character) return <Navigate to={paths.cast} replace />;

  const savedVersion = saved[character.id];
  const isNew = !savedVersion;
  const changed = isNew ? !isEmptyProfile(character) : !sameProfile(character, savedVersion);
  const missing = missingFields(character);
  const attempted = attemptedFor === character.id;

  const save = () => {
    if (!missing.length) return void saveCharacter(character.id);
    setAttemptedFor(character.id);
    showError(
      new ApiError(
        `Fill in all required fields to ${isNew ? "create" : "save"} the character.`,
        `Missing: ${missingLabels(missing)}`,
      ),
    );
  };
  const leave = () => (changed ? setLeaving(true) : leaveToGrid());

  return (
    <div className="absolute inset-0 flex">
      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_900px_600px_at_0%_0%,#17130d_0%,transparent_60%)]" />

        <DetailHeader
          character={character}
          index={index}
          total={cast.length}
          chatOpen={chatOpen}
          saveLabel={isNew ? "CREATE" : "SAVE"}
          saveDisabled={!changed || (attempted && missing.length > 0)}
          onAll={leave}
          onSave={save}
          onToggleChat={toggleChat}
        />

        <motion.div layoutScroll className="scroll-thin relative box-border flex-1 overflow-y-auto px-12 pt-5 pb-10">
          <FieldGrid
            key={character.id}
            character={character}
            // a character that is not created yet cannot be linked
            cast={cast.filter((c) => c.id in saved)}
            cards={cards}
            onChange={(patch) => updateCharacter(character.id, patch)}
            highlighted={highlight?.id === character.id ? highlight.fields : undefined}
            invalid={attempted ? missing : undefined}
          />
        </motion.div>
      </div>
      <ChatPanel
        open={chatOpen}
        characterName={character.name || "this character"}
        messages={chats[character.id] ?? []}
        typing={aiTypingFor === character.id}
        draft={draft}
        onDraftChange={setDraft}
        onSend={() => void sendRevision(character.id)}
      />
      <LeaveDialog
        open={leaving}
        isNew={isNew}
        onStay={() => setLeaving(false)}
        onLeave={() => {
          setLeaving(false);
          leaveToGrid();
        }}
      />
    </div>
  );
}
