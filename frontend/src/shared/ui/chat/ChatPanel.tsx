import { motion } from "motion/react";
import { useEffect, useRef, type ReactNode } from "react";
import { ArrowRight, Spark } from "@/shared/ui/icons";
import { ChatMessage, TypingIndicator, type ChatBubble } from "./ChatMessage";

interface ChatPanelProps {
  open: boolean;
  /** Shown while the chat is empty: what the agent can do, with an example. */
  intro: ReactNode;
  placeholder?: string;
  messages: ChatBubble[];
  typing: boolean;
  draft: string;
  onDraftChange(draft: string): void;
  onSend(): void;
}

/** "ASK AI TO REVISE" panel on the right; width animates 400 ↔ 0. */
export function ChatPanel({
  open,
  intro,
  placeholder = "Describe what to change…",
  messages,
  typing,
  draft,
  onDraftChange,
  onSend,
}: ChatPanelProps) {
  const scroller = useRef<HTMLDivElement>(null);

  // keep the newest message in view
  useEffect(() => {
    const el = scroller.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages.length, typing]);

  return (
    <motion.aside
      aria-label="Ask AI to revise"
      aria-hidden={!open}
      inert={!open}
      initial={false}
      animate={{ width: open ? 400 : 0 }}
      transition={{ duration: 0.45, ease: [0.4, 0, 0.2, 1] }}
      className="h-full shrink-0 overflow-hidden"
    >
      <motion.div
        initial={false}
        animate={{ opacity: open ? 1 : 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="box-border flex h-full w-[400px] flex-col border-l border-line-subtle bg-panel px-7 py-8"
      >
        <div className="flex items-center gap-[10px]">
          <Spark className="text-gold" />
          <div className="font-sans text-xs tracking-[1.5px] text-ink-2">ASK AI TO REVISE</div>
        </div>
        <div className="my-5 border-t border-dotted border-line" />

        <div ref={scroller} className="scroll-thin flex flex-1 flex-col gap-[14px] overflow-y-auto">
          {messages.length === 0 && !typing && <div className="font-sans text-[13px] leading-[1.6] text-faint">{intro}</div>}
          {messages.map((message, i) => (
            <ChatMessage key={i} message={message} />
          ))}
          {typing && <TypingIndicator />}
        </div>

        <form
          className="mt-4 flex items-center gap-[10px] rounded-[12px] border border-line py-[6px] pr-[6px] pl-4 transition-colors focus-within:border-line-hover"
          onSubmit={(e) => {
            e.preventDefault();
            onSend();
          }}
        >
          <label htmlFor="ai-input" className="sr-only">
            Revision request
          </label>
          <input
            id="ai-input"
            value={draft}
            onChange={(e) => onDraftChange(e.target.value)}
            placeholder={placeholder}
            autoComplete="off"
            className="flex-1 border-none bg-transparent py-2 font-sans text-[13px] text-ink placeholder:text-faint focus:outline-none"
          />
          <button
            type="submit"
            aria-label="Send"
            className="flex size-9 shrink-0 items-center justify-center rounded-full border border-gold bg-transparent text-gold transition-colors hover:bg-gold/[0.133]"
          >
            <ArrowRight />
          </button>
        </form>
      </motion.div>
    </motion.aside>
  );
}
