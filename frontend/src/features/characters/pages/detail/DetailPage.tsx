import { motion } from "motion/react";
import { useEffect } from "react";
import { Navigate, useParams } from "react-router";
import { paths } from "@/features/characters/paths";
import { useCastActions, useCastState } from "@/features/characters/store/cast-context";
import { ChatPanel } from "./chat/ChatPanel";
import { DetailHeader } from "./DetailHeader";
import { FieldGrid } from "./FieldGrid";

/** Page "/cast/:id": character detail with live header and scrollable field cards. */
export function DetailPage() {
  const { id = "" } = useParams();
  const { loaded, cast, cards, chatOpen, chats, draft, aiTypingFor, highlight } = useCastState();
  const { characterOpened, updateCharacter, leaveToGrid, toggleChat, setDraft, sendRevision } = useCastActions();
  const index = cast.findIndex((c) => c.id === id);
  const character = cast[index];

  // a (new) character is shown: empty chat draft, chat panel closed
  useEffect(() => {
    characterOpened();
  }, [id, characterOpened]);

  if (!loaded) return null; // the saved cast is still being read after a reload
  if (!character) return <Navigate to={paths.cast} replace />;

  return (
    <div className="absolute inset-0 flex">
      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_900px_600px_at_0%_0%,#17130d_0%,transparent_60%)]" />

        <DetailHeader
          character={character}
          index={index}
          total={cast.length}
          chatOpen={chatOpen}
          onAll={leaveToGrid}
          onToggleChat={toggleChat}
        />

        <motion.div layoutScroll className="scroll-thin relative box-border flex-1 overflow-y-auto px-12 pt-5 pb-10">
          <FieldGrid
            key={character.id}
            character={character}
            cast={cast}
            cards={cards}
            onChange={(patch) => updateCharacter(character.id, patch)}
            highlighted={highlight?.id === character.id ? highlight.fields : undefined}
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
    </div>
  );
}
