import type { ReactNode } from "react";
import { cn } from "@/shared/lib/utils";
import { Spark } from "@/shared/ui/icons";
import { RoundIconButton } from "@/shared/ui/RoundIconButton";

interface StoryHeaderProps {
  eyebrow: string;
  /** Status tag next to the eyebrow; none if left out. */
  tag?: string;
  title: string;
  sub: string;
  /** The sub line describes something in progress: italic and lighter. */
  status?: boolean;
  /** Pills left of the chat toggle. */
  children?: ReactNode;
  /** The AI chat toggle; left out on a page without a chat. */
  chat?: { open: boolean; onToggle(): void };
}

/** Header of the play and act pages: eyebrow + status tag, serif title, sub line, pills and the chat toggle. */
export function StoryHeader({ eyebrow, tag, title, sub, status = false, children, chat }: StoryHeaderProps) {
  const chatLabel = chat?.open ? "Hide AI chat" : "Show AI chat";
  return (
    <header className="relative flex flex-wrap items-end justify-between gap-6 border-b border-dotted border-line-strong px-12 pt-[34px] pb-[18px]">
      <div className="min-w-0">
        <div className="flex min-h-[23px] items-center gap-[14px]">
          <span className="font-sans text-[11px] tracking-[2px] text-muted-2 uppercase">{eyebrow}</span>
          {tag && (
            <span className="rounded-full border border-gold/40 px-[10px] py-[3px] font-sans text-[10px] tracking-[2.5px] text-gold">{tag}</span>
          )}
        </div>
        <h1 className="mt-2 mb-0 font-serif text-[46px] leading-none font-medium">{title}</h1>
        <div className={cn("mt-2 min-h-[1.4em] font-sans text-[13px]", status ? "text-ink-2 italic" : "text-muted")}>{sub}</div>
      </div>
      <div className="mb-1 flex shrink-0 items-center gap-[10px]">
        {children}
        {chat && (
          <RoundIconButton active={chat.open} onClick={chat.onToggle} aria-label={chatLabel} title={chatLabel}>
            <Spark />
          </RoundIconButton>
        )}
      </div>
    </header>
  );
}
