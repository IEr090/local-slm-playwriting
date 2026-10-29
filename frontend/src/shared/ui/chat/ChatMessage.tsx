/** What a chat bubble shows; every feature maps its own messages to this. */
export type ChatBubble =
  | {
      role: "user";
      text: string;
      /** Small gold label above the text, e.g. "ACT TWO" or "SCENE 3". */
      about?: string;
    }
  | {
      role: "ai";
      text: string;
      /** Labels of what the AI changed with this answer; empty when it only answered. */
      updated: string[];
    };

const fadeUp = "animate-fade-up";

/** One chat bubble: the user's request on the right, the AI's answer on the left. */
export function ChatMessage({ message }: { message: ChatBubble }) {
  if (message.role === "user") {
    return (
      <div className={`${fadeUp} max-w-[82%] self-end rounded-[12px_12px_2px_12px] border border-gold/[0.333] bg-gold/10 px-4 py-3`}>
        {message.about && <span className="mb-1 block font-sans text-[10px] tracking-[1.5px] text-gold">{message.about}</span>}
        <div className="font-sans text-[13px] leading-[1.5] text-ink">{message.text}</div>
      </div>
    );
  }
  return (
    <div className={`${fadeUp} max-w-[88%] self-start rounded-[12px_12px_12px_2px] border border-line bg-bubble/80 px-4 py-[14px]`}>
      {message.updated.length > 0 && <div className="mb-2 font-sans text-xs text-muted-2">Updated: {message.updated.join(", ")}</div>}
      <div className="font-sans text-[13px] leading-[1.6] whitespace-pre-line text-ink-3">{message.text}</div>
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
