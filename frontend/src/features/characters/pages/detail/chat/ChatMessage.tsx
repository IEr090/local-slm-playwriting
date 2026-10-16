import { FIELD_LABEL } from "@/features/characters/model/labels";
import type { ChatMessage as Message } from "@/features/characters/model/types";

const fadeUp = "animate-fade-up";

/** One chat bubble: the user's request on the right, the AI's answer on the left. */
export function ChatMessage({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className={`${fadeUp} max-w-[82%] self-end rounded-[12px_12px_2px_12px] border border-gold/[0.333] bg-gold/10 px-4 py-3`}>
        <div className="font-sans text-[13px] leading-[1.5] text-ink">{message.text}</div>
      </div>
    );
  }
  const changed = [...new Set(message.changed_fields.map((f) => FIELD_LABEL[f]))];
  return (
    <div className={`${fadeUp} max-w-[88%] self-start rounded-[12px_12px_12px_2px] border border-line bg-bubble/80 px-4 py-[14px]`}>
      {changed.length > 0 && <div className="mb-2 font-sans text-xs text-muted-2">Updated: {changed.join(", ")}</div>}
      <div className="font-sans text-[13px] leading-[1.6] text-ink-3">{message.text}</div>
    </div>
  );
}

/** Three pulsing gold dots while the AI is answering. */
export function TypingIndicator() {
  return (
    <div role="status" aria-label="AI is typing" className="self-start rounded-[12px] border border-line bg-bubble/80 px-4 py-3">
      {[0, 0.2, 0.4].map((delay) => (
        <span
          key={delay}
          className="mr-1 inline-block size-[5px] animate-dots rounded-full bg-gold"
          style={{ animationDelay: `${delay}s` }}
        />
      ))}
    </div>
  );
}
